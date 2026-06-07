"""
socket_handlers.py — Procesamiento de frames vía WebSocket.

El navegador captura cada N ms el <canvas> con el stream de la cámara
y envía el JPEG codificado en base64. Este módulo recibe el frame,
corre MediaPipe en el servidor y devuelve el resultado (bbox, persona_detectada).
Si detecta persona con confirmación, dispara la alerta WhatsApp.
"""

import base64
import logging
import time

from flask import request
from flask_socketio import emit

from .extensions import socketio
from .vision import _is_valid_person, _load_vision_dependencies, MODEL_PATH, _build_pose_landmarker
from .whatsapp import get_waha_config, send_person_detected

logger = logging.getLogger(__name__)

# ── Estado por sesión WebSocket ───────────────────────────────────────────────
# { sid: { landmarker, dependencies, timestamp_ms, confirm_streak, last_result } }
_sessions: dict = {}

CONFIRM_NEEDED = 4   # detecciones consecutivas antes de confirmar
DETECT_WIDTH   = 640


def _get_or_create_session(sid):
    if sid in _sessions:
        return _sessions[sid]

    deps, err = _load_vision_dependencies()
    if err or not deps:
        return None

    try:
        lm = _build_pose_landmarker(deps)
    except Exception as exc:
        logger.warning('No se pudo crear landmarker para sid=%s: %s', sid, exc)
        return None

    state = {
        'landmarker':     lm,
        'dependencies':   deps,
        'timestamp_ms':   0,
        'confirm_streak': 0,
        'last_result':    False,
        'camera_name':    '',
        'chat_id':        '',
        'detection_on':   True,
    }
    _sessions[sid] = state
    return state


def _cleanup_session(sid):
    state = _sessions.pop(sid, None)
    if state and state.get('landmarker'):
        try:
            state['landmarker'].close()
        except Exception:
            pass


# ── Eventos SocketIO ──────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    logger.info('WS connect sid=%s', request.sid)


@socketio.on('disconnect')
def on_disconnect():
    _cleanup_session(request.sid)
    logger.info('WS disconnect sid=%s', request.sid)


@socketio.on('init_camera')
def on_init_camera(data):
    """
    El cliente envía metadatos de la cámara al abrir el stream.
    data = { camera_name, chat_id, detection_on }
    """
    sid = request.sid
    state = _get_or_create_session(sid)
    if not state:
        emit('detection_unavailable', {'reason': 'MediaPipe no disponible en el servidor'})
        return

    state['camera_name']  = data.get('camera_name', '')
    state['chat_id']      = data.get('chat_id', '')
    state['detection_on'] = bool(data.get('detection_on', True))
    emit('ready', {'detector': True})


@socketio.on('toggle_detection')
def on_toggle_detection(data):
    sid = request.sid
    state = _sessions.get(sid)
    if state:
        state['detection_on']   = bool(data.get('active', True))
        state['confirm_streak'] = 0
        state['last_result']    = False


@socketio.on('frame')
def on_frame(data):
    """
    Recibe un frame JPEG en base64 desde el navegador.
    data = { image: 'data:image/jpeg;base64,...', camera_name, chat_id }
    Devuelve: { person: bool, bbox: [x1,y1,x2,y2] | null }
    """
    sid   = request.sid
    state = _sessions.get(sid)

    if not state:
        state = _get_or_create_session(sid)
        if not state:
            emit('result', {'person': False, 'bbox': None})
            return

    # Actualizar metadatos si vienen en el frame
    if 'camera_name' in data:
        state['camera_name'] = data['camera_name']
    if 'chat_id' in data:
        state['chat_id'] = data['chat_id']

    if not state.get('detection_on', True):
        state['confirm_streak'] = 0
        state['last_result']    = False
        emit('result', {'person': False, 'bbox': None})
        return

    # Decodificar JPEG
    try:
        import cv2, numpy as np
        raw = data.get('image', '')
        if raw.startswith('data:'):
            raw = raw.split(',', 1)[1]
        img_bytes = base64.b64decode(raw)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('frame vacío')
    except Exception as exc:
        logger.debug('Error decodificando frame: %s', exc)
        emit('result', {'person': False, 'bbox': None})
        return

    # Escalar para inferencia
    h, w = frame.shape[:2]
    if w > DETECT_WIDTH:
        scale = DETECT_WIDTH / w
        small = cv2.resize(frame, (DETECT_WIDTH, int(h * scale)))
    else:
        small  = frame
        scale  = 1.0

    deps = state['dependencies']
    lm   = state['landmarker']
    mp   = deps['mp']
    cv2_ = deps['cv2']

    state['timestamp_ms'] += 100  # ~10fps desde cliente

    try:
        rgb    = cv2_.cvtColor(small, cv2_.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = lm.detect_for_video(mp_img, state['timestamp_ms'])
    except Exception as exc:
        logger.debug('Error en inferencia: %s', exc)
        emit('result', {'person': False, 'bbox': None})
        return

    person_now = False
    bbox_out   = None

    if result.pose_landmarks:
        landmarks = result.pose_landmarks[0]
        if _is_valid_person(landmarks):
            person_now = True

            # Calcular bbox en coordenadas del frame ORIGINAL (no del small)
            xs = [lm_pt.x * w for lm_pt in landmarks]
            ys = [lm_pt.y * h for lm_pt in landmarks]
            margin = 20
            x1 = max(0,     int(min(xs)) - margin)
            y1 = max(0,     int(min(ys)) - margin)
            x2 = min(w - 1, int(max(xs)) + margin)
            y2 = min(h - 1, int(max(ys)) + margin)
            bbox_out = [x1, y1, x2, y2]

    # Confirmación por streak
    if person_now:
        state['confirm_streak'] += 1
    else:
        state['confirm_streak'] = 0

    confirmed = state['confirm_streak'] >= CONFIRM_NEEDED
    state['last_result'] = confirmed

    # Alerta WhatsApp con el frame si está confirmado
    if confirmed:
        try:
            from flask import current_app
            with current_app.app_context():
                cfg = get_waha_config()
            send_person_detected(
                state['camera_name'],
                state['chat_id'],
                cfg,
                frame_bgr=frame,
            )
        except Exception as exc:
            logger.debug('Error enviando alerta WS: %s', exc)

    emit('result_' + data.get('camera_id', ''), {
        'person': confirmed,
        'bbox':   bbox_out if confirmed else None,
    }, broadcast=False)


# ── Store de frames del agente (cámara → último JPEG bytes) ──────────────────
# { camera_id: bytes }
_agent_frames: dict = {}


@socketio.on('agent_frame')
def on_agent_frame(data):
    """
    El teléfono-cámara (camera_agent.html) envía frames aquí.
    data = { camera_id, image: 'data:image/jpeg;base64,...' }
    Guardamos el JPEG para que el dashboard lo consulte por HTTP.
    """
    camera_id = str(data.get('camera_id', ''))
    raw = data.get('image', '')
    if not camera_id or not raw:
        return
    try:
        if raw.startswith('data:'):
            raw = raw.split(',', 1)[1]
        _agent_frames[camera_id] = base64.b64decode(raw)
    except Exception:
        pass


def get_agent_frame(camera_id: str):
    """Devuelve los bytes JPEG más recientes del agente, o None."""
    return _agent_frames.get(str(camera_id))

