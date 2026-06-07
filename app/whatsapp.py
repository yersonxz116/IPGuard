import io
import logging
import time

import requests

logger = logging.getLogger(__name__)

_last_notification_time = {}
_session = requests.Session()   # mantiene cookies automáticamente
_last_login_time = 0
LOGIN_TTL = 3600  # re-login cada hora

COOLDOWN_SECONDS = 60


def get_waha_config():
    try:
        from flask import current_app
        return {
            'api_url': current_app.config.get('WAHA_API_URL', '').rstrip('/'),
            'session': current_app.config.get('WAHA_SESSION', 'default'),
            'api_key': current_app.config.get('WAHA_API_KEY', ''),
        }
    except RuntimeError:
        return {'api_url': '', 'session': 'default', 'api_key': ''}


def _should_notify(camera_name):
    now = time.time()
    last_time = _last_notification_time.get(camera_name, 0)
    if now - last_time < COOLDOWN_SECONDS:
        return False
    _last_notification_time[camera_name] = now
    return True


def _ensure_logged_in(api_url, api_key):
    """Hace login con cookie-session si no hay sesión activa o expiró."""
    global _last_login_time
    if time.time() - _last_login_time < LOGIN_TTL:
        return True

    try:
        resp = _session.post(
            f'{api_url}/login',
            data={'username': 'admin', 'password': api_key},
            timeout=10,
            allow_redirects=True,
        )
        # 200 tras redirect de login = éxito
        _last_login_time = time.time()
        logger.debug('Login WAHA exitoso (status=%s)', resp.status_code)
        return True
    except Exception as exc:
        logger.warning('Error en login WAHA: %s', exc)
        return False


def send_person_detected(camera_name, chat_id, waha_config, frame_bgr=None):
    """
    Envía alerta de persona detectada vía WAHA.
    Si se proporciona frame_bgr (numpy array BGR de OpenCV),
    se adjunta como imagen junto con el mensaje.
    """
    api_url = waha_config.get('api_url', '')
    session = waha_config.get('session', 'default')
    api_key = waha_config.get('api_key', '')

    if not api_url or not chat_id:
        return False

    if not _should_notify(camera_name):
        return False

    to_number = chat_id.replace('@c.us', '').strip()

    caption = (
        f'⚠️ *IPGuard — Alerta de seguridad*\n'
        f'📷 Cámara: *{camera_name}*\n'
        f'🕐 {time.strftime("%H:%M:%S")} — {time.strftime("%d/%m/%Y")}\n'
        f'🚨 Persona detectada en tiempo real'
    )

    if not _ensure_logged_in(api_url, api_key):
        logger.warning('No se pudo autenticar en WAHA, alerta no enviada')
        return False

    # ── Intentar enviar imagen si hay frame disponible ──────────────────────
    if frame_bgr is not None:
        try:
            import cv2
            # Codificar frame como JPEG en memoria
            ok, buf = cv2.imencode('.jpg', frame_bgr,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if ok:
                img_bytes = io.BytesIO(buf.tobytes())
                url = f'{api_url}/sessions/{session}/send-file'
                resp = _session.post(
                    url,
                    data={'to': to_number, 'caption': caption},
                    files={'file': ('alerta.jpg', img_bytes, 'image/jpeg')},
                    timeout=15,
                )
                body = resp.json()
                if body.get('ok'):
                    logger.info('Alerta con imagen enviada: camara=%s → %s',
                                camera_name, to_number)
                    return True
                logger.warning('send-file respondió ok=false: %s', body)
        except Exception as exc:
            logger.warning('Error enviando imagen, fallback a texto: %s', exc)

    # ── Fallback: solo texto ─────────────────────────────────────────────────
    resp = None
    try:
        url = f'{api_url}/sessions/{session}/send'
        resp = _session.post(
            url,
            json={'to': to_number, 'message': caption},
            timeout=10,
        )
        body = resp.json()
        if body.get('ok'):
            logger.info('Alerta (texto) enviada: camara=%s → %s',
                        camera_name, to_number)
            return True
        logger.warning('send respondió ok=false: %s', body)
        return False
    except Exception as exc:
        if resp is not None and resp.status_code in (401, 403):
            global _last_login_time
            _last_login_time = 0
        logger.warning('Error enviando alerta: %s', exc)
        return False
