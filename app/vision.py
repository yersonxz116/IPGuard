import time
import threading
from pathlib import Path


MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'pose_landmarker_full.task'

_detection_active = {}


def set_detection_active(camera_id, active):
    _detection_active[camera_id] = active


def get_detection_active(camera_id):
    return _detection_active.get(camera_id, True)


def _load_vision_dependencies():
    """Carga OpenCV y MediaPipe Tasks de forma perezosa."""
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import PoseLandmarker
        from mediapipe.tasks.python.vision import PoseLandmarkerOptions
        from mediapipe.tasks.python.vision import PoseLandmarksConnections
        from mediapipe.tasks.python.vision import RunningMode
    except ImportError as exc:
        return None, str(exc)

    return {
        'cv2': cv2,
        'mp': mp,
        'BaseOptions': BaseOptions,
        'PoseLandmarker': PoseLandmarker,
        'PoseLandmarkerOptions': PoseLandmarkerOptions,
        'PoseLandmarksConnections': PoseLandmarksConnections,
        'RunningMode': RunningMode,
    }, ''


def is_person_detector_available():
    """Indica si el entorno tiene lo necesario para deteccion."""
    dependencies, dependency_error = _load_vision_dependencies()
    return bool(dependencies) and not dependency_error and MODEL_PATH.exists()


def _build_pose_landmarker(dependencies):
    options = dependencies['PoseLandmarkerOptions'](
        base_options=dependencies['BaseOptions'](model_asset_path=str(MODEL_PATH)),
        running_mode=dependencies['RunningMode'].VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.70,   # era 0.25 — evita falsos positivos
        min_pose_presence_confidence=0.70,    # era 0.25
        min_tracking_confidence=0.60,         # era 0.25
        output_segmentation_masks=False
    )
    return dependencies['PoseLandmarker'].create_from_options(options)


def _bounding_box_from_landmarks(frame, landmarks):
    visible_points = [landmark for landmark in landmarks if landmark.visibility >= 0.25]
    if len(visible_points) < 4:
        return None

    frame_height, frame_width = frame.shape[:2]
    xs = [int(point.x * frame_width) for point in visible_points]
    ys = [int(point.y * frame_height) for point in visible_points]

    pad = 16
    x1 = max(min(xs) - pad, 0)
    y1 = max(min(ys) - pad, 0)
    x2 = min(max(xs) + pad, frame_width - 1)
    y2 = min(max(ys) + pad, frame_height - 1)

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


def _is_valid_person(landmarks):
    """
    Valida que los landmarks correspondan a una persona real.
    Requiere que hombros, caderas y al menos una rodilla/tobillo sean visibles
    con alta confianza — descarta siluetas parciales y objetos con forma humana.
    """
    # Índices MediaPipe Pose: 11=hombro_izq, 12=hombro_der, 23=cadera_izq,
    # 24=cadera_der, 25=rodilla_izq, 26=rodilla_der, 27=tobillo_izq, 28=tobillo_der
    SHOULDERS  = [11, 12]
    HIPS       = [23, 24]
    LEGS       = [25, 26, 27, 28]
    THRESHOLD  = 0.60

    def visible(indices, min_count=1):
        count = sum(1 for i in indices
                    if i < len(landmarks) and landmarks[i].visibility >= THRESHOLD)
        return count >= min_count

    # Exigir: ambos hombros + al menos 1 cadera + al menos 1 punto de pierna
    if not visible(SHOULDERS, min_count=2):
        return False
    if not visible(HIPS, min_count=1):
        return False
    if not visible(LEGS, min_count=1):
        return False
    return True


def annotate_people_frame(frame, dependencies, landmarker, timestamp_ms):
    cv2 = dependencies['cv2']
    mp  = dependencies['mp']

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    result    = landmarker.detect_for_video(mp_image, timestamp_ms)

    if not result.pose_landmarks:
        return frame, False

    landmarks = result.pose_landmarks[0]

    # Validación estricta: rechaza detecciones parciales o dudosas
    if not _is_valid_person(landmarks):
        return frame, False

    bounding_box = _bounding_box_from_landmarks(frame, landmarks)
    if bounding_box:
        x1, y1, x2, y2 = bounding_box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 214, 143), 2)

    return frame, True


def _encode_status_frame(message):
    dependencies, dependency_error = _load_vision_dependencies()
    if dependency_error or not dependencies:
        return None

    cv2 = dependencies['cv2']
    frame = cv2.UMat(360, 640, cv2.CV_8UC3).get()
    frame[:] = (7, 13, 11)
    cv2.putText(
        frame,
        message[:52],
        (18, 170),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (255, 225, 222),
        2,
        cv2.LINE_AA
    )
    ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return None
    return buffer.tobytes()


class _FrameReader:
    """
    Hilo de lectura dedicado que drena el buffer de OpenCV continuamente.
    Solo conserva el frame más reciente — elimina el delay acumulado.
    """

    def __init__(self, capture, cv2):
        self._capture = capture
        self._cv2 = cv2
        self._frame = None
        self._ok = True
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop_event.is_set():
            ok, frame = self._capture.read()
            with self._lock:
                self._ok = ok
                if ok and frame is not None:
                    self._frame = frame
            if not ok:
                time.sleep(0.01)

    def read(self):
        with self._lock:
            return self._ok, self._frame

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=2)


def generate_camera_stream(stream_url, camera_id, camera_name='', chat_id='', waha_config=None):
    """Genera un stream MJPEG de baja latencia. Aplica deteccion solo si el flag esta activo."""
    from .whatsapp import send_person_detected

    dependencies, dependency_error = _load_vision_dependencies()
    if dependency_error or not dependencies:
        error_frame = _encode_status_frame('Instala mediapipe y opencv para usar la deteccion.')
        if error_frame:
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n'
        return

    cv2 = dependencies['cv2']
    landmarker = None

    if MODEL_PATH.exists():
        try:
            landmarker = _build_pose_landmarker(dependencies)
        except Exception:
            landmarker = None

    capture = cv2.VideoCapture(stream_url)

    # Minimizar buffer interno de OpenCV → baja latencia
    try:
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
        capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
    except Exception:
        pass

    if not capture.isOpened():
        if landmarker:
            landmarker.close()
        error_frame = _encode_status_frame('No se pudo abrir el stream de la camara.')
        if error_frame:
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n'
        return

    reader = _FrameReader(capture, cv2)

    try:
        last_success          = time.time()
        timestamp_ms          = 0
        frame_count           = 0
        last_detection_result = False
        confirm_streak        = 0
        CONFIRM_NEEDED        = 4
        DETECT_WIDTH          = 640

        # Cap de FPS: limita el yield a máx 25 fps sin importar si hay detección o no.
        # Sin esto, al desactivar detección el loop corre a >200 fps e inunda el socket.
        TARGET_FPS   = 25
        FRAME_PERIOD = 1.0 / TARGET_FPS   # 0.04 s entre frames
        last_yield   = 0.0

        while True:
            ok, frame = reader.read()

            if not ok or frame is None:
                if time.time() - last_success > 3.0:
                    error_frame = _encode_status_frame('Se perdio la lectura del stream.')
                    if error_frame:
                        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n'
                    break
                time.sleep(0.005)
                continue

            last_success = time.time()
            frame_count += 1
            timestamp_ms += 33
            output_frame = frame
            person_detected = last_detection_result

            if landmarker and get_detection_active(camera_id):
                if frame_count % 3 == 0:
                    try:
                        h, w = frame.shape[:2]
                        if w > DETECT_WIDTH:
                            scale = DETECT_WIDTH / w
                            small = cv2.resize(frame, (DETECT_WIDTH, int(h * scale)))
                        else:
                            small = frame

                        _, person_detected_now = annotate_people_frame(
                            small, dependencies, landmarker, timestamp_ms
                        )

                        if person_detected_now:
                            confirm_streak += 1
                        else:
                            confirm_streak = 0

                        person_confirmed      = confirm_streak >= CONFIRM_NEEDED
                        last_detection_result = person_confirmed
                        person_detected       = person_confirmed

                        if person_confirmed:
                            output_frame, _ = annotate_people_frame(
                                frame.copy(), dependencies, landmarker, timestamp_ms
                            )
                    except Exception:
                        output_frame   = frame
                        confirm_streak = 0

                if person_detected and camera_name and chat_id and waha_config:
                    send_person_detected(camera_name, chat_id, waha_config,
                                         frame_bgr=output_frame)
            else:
                # Detección desactivada: resetear streak para no heredar estado
                confirm_streak        = 0
                last_detection_result = False

            # ── Cap de FPS ──────────────────────────────────────────────────
            now = time.time()
            elapsed = now - last_yield
            if elapsed < FRAME_PERIOD:
                time.sleep(FRAME_PERIOD - elapsed)
            last_yield = time.time()

            ok, buffer = cv2.imencode(
                '.jpg',
                output_frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 75]
            )
            if not ok:
                continue

            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

    finally:
        reader.stop()
        capture.release()
        if landmarker:
            landmarker.close()
