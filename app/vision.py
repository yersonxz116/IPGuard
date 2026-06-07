import time
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
        min_pose_detection_confidence=0.25,
        min_pose_presence_confidence=0.25,
        min_tracking_confidence=0.25,
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


def annotate_people_frame(frame, dependencies, landmarker, timestamp_ms):
    cv2 = dependencies['cv2']
    mp = dependencies['mp']

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    result = landmarker.detect_for_video(mp_image, timestamp_ms)

    if not result.pose_landmarks:
        return frame, False

    landmarks = result.pose_landmarks[0]
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


def generate_camera_stream(stream_url, camera_id, camera_name='', chat_id='', waha_config=None):
    """Genera un stream MJPEG. Aplica deteccion solo si el flag esta activo."""
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
    if not capture.isOpened():
        if landmarker:
            landmarker.close()
        error_frame = _encode_status_frame('No se pudo abrir el stream de la camara.')
        if error_frame:
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n'
        return

    try:
        last_success = time.time()
        timestamp_ms = 0
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                if time.time() - last_success > 2.0:
                    error_frame = _encode_status_frame('Se perdio la lectura del stream.')
                    if error_frame:
                        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n'
                    break
                continue

            last_success = time.time()
            timestamp_ms += 33
            output_frame = frame
            person_detected = False

            if landmarker and get_detection_active(camera_id):
                try:
                    output_frame, person_detected = annotate_people_frame(
                        frame, dependencies, landmarker, timestamp_ms
                    )
                except Exception:
                    output_frame = frame

                if person_detected and camera_name and chat_id and waha_config:
                    send_person_detected(camera_name, chat_id, waha_config)

            ok, buffer = cv2.imencode(
                '.jpg',
                output_frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 82]
            )
            if not ok:
                continue

            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
    finally:
        capture.release()
        if landmarker:
            landmarker.close()
