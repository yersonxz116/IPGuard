import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

from .extensions import db, migrate
from .models import User


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


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

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

    @app.route('/dashboard')
    def dashboard():
        """Pagina del dashboard protegida por sesion."""
        if 'user_id' not in session:
            return redirect(url_for('login'))

        return render_template('index.html')

    @app.after_request
    def add_cache_headers(response):
        if 'static' in request.path:
            response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    return app
