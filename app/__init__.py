import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

from .extensions import db, migrate
from .models import Camera, User
from .vision import generate_processed_stream, is_person_detector_available


def limit_to_two_sentences(text):
    """Reduce model output to at most two readable sentences."""
    normalized = re.sub(r'\s+', ' ', text).strip()
    if not normalized:
        return ''

    sentences = re.findall(r'[^.!?]+[.!?]+|[^.!?]+$', normalized)
    short_answer = ' '.join(sentence.strip() for sentence in sentences[:2]).strip()

    if len(sentences) <= 1 and len(short_answer.split()) > 45:
        short_answer = ' '.join(short_answer.split()[:45]).rstrip(',.')
        short_answer = f'{short_answer}.'

    return short_answer


def normalize_camera_url(raw_url):
    """Normaliza una URL de camara agregando esquema HTTP si falta."""
    candidate = (raw_url or '').strip()
    if not candidate:
        return ''

    if '://' not in candidate:
        candidate = f'http://{candidate}'

    return candidate


def is_valid_camera_url(url):
    """Valida que la URL de camara sea HTTP o HTTPS y tenga host."""
    parsed = urlparse(url)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def infer_snapshot_url(stream_url):
    """Intenta inferir la captura estatica para streams ESP32-CAM comunes."""
    if stream_url.endswith('/foto') or stream_url.endswith('/capture'):
        return stream_url
    return ''


def is_live_stream_url(url):
    """Detecta endpoints comunes de video en vivo como ESP32-CAM o DroidCam."""
    normalized_url = normalize_camera_url(url).lower()
    if not normalized_url:
        return False

    stream_markers = (
        '/stream',
        '/video',
        '.mjpg',
        '.mjpeg',
        'action=stream',
    )
    return any(marker in normalized_url for marker in stream_markers)


def resolve_camera_urls(input_url, input_snapshot_url=''):
    """Resuelve URLs reales para camaras ESP32-CAM y endpoints comunes."""
    normalized_input = normalize_camera_url(input_url)
    parsed = urlparse(normalized_input)
    path = parsed.path or ''
    base_url = f'{parsed.scheme}://{parsed.netloc}'

    if not path or path == '/':
        stream_url = f'{base_url}/stream'
    elif path == '/foto':
        # Compatibilidad con registros antiguos que guardaban /foto como stream.
        stream_url = f'{base_url}/stream'
    else:
        stream_url = normalized_input

    snapshot_url = normalize_camera_url(input_snapshot_url)
    if not snapshot_url:
        snapshot_url = infer_snapshot_url(stream_url)

    preview_url = snapshot_url or stream_url
    preview_mode = 'snapshot'
    if is_live_stream_url(stream_url) and preview_url == stream_url:
        preview_mode = 'stream'

    return stream_url, snapshot_url, preview_url, preview_mode


def serialize_camera(camera):
    """Convierte una camara a un formato JSON util para el dashboard."""
    _, _, preview_url, preview_mode = resolve_camera_urls(
        camera.stream_url,
        camera.snapshot_url or ''
    )
    detection_enabled = preview_mode == 'stream' and is_person_detector_available()
    detection_stream_url = ''
    if camera.id and detection_enabled:
        detection_stream_url = url_for('api_camera_processed_stream', camera_id=camera.id)

    return {
        'id': camera.id,
        'name': camera.name,
        'stream_url': camera.stream_url,
        'snapshot_url': camera.snapshot_url or '',
        'preview_url': preview_url,
        'preview_mode': preview_mode,
        'detection_stream_url': detection_stream_url,
        'detection_enabled': detection_enabled,
        'location': camera.location or '',
        'is_active': bool(camera.is_active),
        'created_at': camera.created_at.isoformat()
    }


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000

    db.init_app(app)
    migrate.init_app(app, db)

    @app.context_processor
    def inject_asset_url():
        """Agrega versionado por mtime a archivos estaticos locales."""
        def asset_url(filename):
            static_path = Path(app.static_folder) / filename
            version = int(static_path.stat().st_mtime) if static_path.exists() else 1
            return url_for('static', filename=filename, v=version)

        return {'asset_url': asset_url}

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login():
        """Muestra la pagina de login."""
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/ia')
    def ia_chat():
        """Muestra el chat publico con Ollama."""
        return render_template('ia.html', model_name=app.config['OLLAMA_MODEL'])

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Registra un usuario nuevo en la base de datos."""
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        form_data = {
            'full_name': '',
            'username': '',
            'email': ''
        }

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            form_data.update({
                'full_name': full_name,
                'username': username,
                'email': email
            })

            if not full_name or not username or not email or not password or not confirm_password:
                return render_template(
                    'register.html',
                    error_message='Todos los campos son obligatorios.',
                    form_data=form_data
                ), 400

            if password != confirm_password:
                return render_template(
                    'register.html',
                    error_message='Las contrasenas no coinciden.',
                    form_data=form_data
                ), 400

            if len(password) < 8:
                return render_template(
                    'register.html',
                    error_message='La contrasena debe tener al menos 8 caracteres.',
                    form_data=form_data
                ), 400

            existing_user = User.query.filter(
                or_(User.username == username, User.email == email)
            ).first()

            if existing_user:
                message = 'El usuario ya existe.' if existing_user.username == username else 'El correo ya esta registrado.'
                return render_template(
                    'register.html',
                    error_message=message,
                    form_data=form_data
                ), 409

            user = User(
                full_name=full_name,
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()

            return render_template(
                'register.html',
                success_message='Cuenta creada correctamente. Ahora puedes iniciar sesion.',
                form_data={}
            ), 201

        return render_template('register.html', form_data=form_data)

    @app.route('/logout')
    def logout():
        """Cierra la sesion del usuario."""
        session.clear()
        return redirect(url_for('index'))

    @app.route('/api/login', methods=['POST'])
    def api_login():
        """Autentica un usuario por nombre de usuario o email."""
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos no proporcionados'
            }), 400

        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')

        if not username_or_email:
            return jsonify({
                'success': False,
                'message': 'El usuario o email es requerido'
            }), 400

        if not password:
            return jsonify({
                'success': False,
                'message': 'La contrasena es requerida'
            }), 400

        user = User.query.filter(
            or_(User.username == username_or_email, User.email == username_or_email.lower())
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({
                'success': False,
                'message': 'Usuario, correo o contrasena incorrectos'
            }), 401

        session['user_id'] = user.id
        session['username'] = user.username
        session['logged_in'] = True

        return jsonify({
            'success': True,
            'message': 'Login exitoso',
            'redirect': '/dashboard',
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email
            }
        }), 200

    @app.route('/api/ia/chat', methods=['POST'])
    def api_ia_chat():
        """Consulta el modelo de Ollama sin requerir sesion."""
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos no proporcionados'
            }), 400

        prompt = data.get('message', '').strip()
        history = data.get('history', [])

        if not prompt:
            return jsonify({
                'success': False,
                'message': 'El mensaje no puede estar vacio'
            }), 400

        if history and not isinstance(history, list):
            return jsonify({
                'success': False,
                'message': 'El historial enviado no es valido'
            }), 400

        messages = [
            {
                'role': 'system',
                'content': (
                    'Eres un asistente claro y util en espanol. '
                    'Responde de forma directa, natural y relevante a la pregunta del usuario. '
                    'Limita siempre tu respuesta a maximo dos frases cortas.'
                )
            }
        ]

        for item in history[-10:]:
            if not isinstance(item, dict):
                continue
            role = item.get('role')
            content = str(item.get('content', '')).strip()
            if role in {'user', 'assistant'} and content:
                messages.append({'role': role, 'content': content})

        messages.append({'role': 'user', 'content': prompt})

        payload = json.dumps({
            'model': app.config['OLLAMA_MODEL'],
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.45,
                'num_predict': 80
            }
        }).encode('utf-8')

        ollama_request = Request(
            app.config['OLLAMA_URL'],
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urlopen(ollama_request, timeout=120) as response:
                ollama_data = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='ignore')
            return jsonify({
                'success': False,
                'message': 'Ollama respondio con un error',
                'detail': detail
            }), 502
        except URLError:
            return jsonify({
                'success': False,
                'message': 'No fue posible conectar con Ollama en http://127.0.0.1:11434'
            }), 503
        except Exception as exc:
            return jsonify({
                'success': False,
                'message': 'Error inesperado consultando el modelo',
                'detail': str(exc)
            }), 500

        message = ollama_data.get('message') or {}
        answer = limit_to_two_sentences(str(message.get('content', '')).strip())
        if not answer:
            return jsonify({
                'success': False,
                'message': 'El modelo no devolvio contenido'
            }), 502

        return jsonify({
            'success': True,
            'model': app.config['OLLAMA_MODEL'],
            'response': answer
        }), 200

    @app.route('/api/cameras', methods=['POST'])
    def api_create_camera():
        """Registra una camara IP para el usuario autenticado."""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Debes iniciar sesion para agregar camaras'
            }), 401

        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos no proporcionados'
            }), 400

        name = data.get('name', '').strip()
        location = data.get('location', '').strip()
        raw_stream_url = data.get('stream_url', '')
        raw_snapshot_url = data.get('snapshot_url', '')
        normalized_stream_input = normalize_camera_url(raw_stream_url)
        normalized_snapshot_input = normalize_camera_url(raw_snapshot_url)

        if not name:
            return jsonify({
                'success': False,
                'message': 'El nombre de la camara es obligatorio'
            }), 400

        if not normalized_stream_input:
            return jsonify({
                'success': False,
                'message': 'La URL base o del stream es obligatoria'
            }), 400

        if not is_valid_camera_url(normalized_stream_input):
            return jsonify({
                'success': False,
                'message': 'La URL base o del stream no es valida'
            }), 400

        if normalized_snapshot_input and not is_valid_camera_url(normalized_snapshot_input):
            return jsonify({
                'success': False,
                'message': 'La URL de captura no es valida'
            }), 400

        stream_url, snapshot_url, _, _ = resolve_camera_urls(
            normalized_stream_input,
            normalized_snapshot_input
        )

        camera = Camera(
            user_id=user_id,
            name=name,
            location=location or None,
            stream_url=stream_url,
            snapshot_url=snapshot_url or None,
            is_active=True
        )
        db.session.add(camera)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Camara agregada correctamente',
            'camera': serialize_camera(camera)
        }), 201

    @app.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
    def api_delete_camera(camera_id):
        """Elimina una camara registrada por el usuario autenticado."""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Debes iniciar sesion para gestionar camaras'
            }), 401

        camera = Camera.query.filter_by(id=camera_id, user_id=user_id).first()
        if not camera:
            return jsonify({
                'success': False,
                'message': 'La camara no existe o no te pertenece'
            }), 404

        db.session.delete(camera)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Camara eliminada correctamente'
        }), 200

    @app.route('/api/cameras/<int:camera_id>/processed_stream')
    def api_camera_processed_stream(camera_id):
        """Entrega un stream MJPEG procesado con deteccion de personas."""
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Debes iniciar sesion para ver el stream procesado'
            }), 401

        camera = Camera.query.filter_by(id=camera_id, user_id=user_id).first()
        if not camera:
            return jsonify({
                'success': False,
                'message': 'La camara no existe o no te pertenece'
            }), 404

        if not is_person_detector_available():
            return jsonify({
                'success': False,
                'message': 'OpenCV o MediaPipe no estan instalados en el entorno'
            }), 503

        return Response(
            generate_processed_stream(camera.stream_url),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    @app.route('/dashboard')
    def dashboard():
        """Pagina del dashboard protegida por sesion."""
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        user = User.query.get(user_id)
        if not user:
            session.clear()
            return redirect(url_for('login'))

        cameras = Camera.query.filter_by(user_id=user.id).order_by(Camera.created_at.desc()).all()
        camera_cards = [serialize_camera(camera) for camera in cameras]
        active_cameras = sum(1 for camera in cameras if camera.is_active)

        return render_template(
            'dashboard.html',
            user=user,
            cameras=camera_cards,
            total_cameras=len(cameras),
            active_cameras=active_cameras,
            camera_payload=camera_cards,
            detector_available=is_person_detector_available()
        )

    @app.after_request
    def add_cache_headers(response):
        if 'static' in request.path:
            response.headers['Cache-Control'] = (
                'public, max-age=31536000, immutable, stale-while-revalidate=86400'
            )
        return response

    return app
