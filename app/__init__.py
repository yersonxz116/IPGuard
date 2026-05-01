from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import secrets


def create_app():
    app = Flask(__name__)

    # Configuracion de la aplicacion
    app.secret_key = secrets.token_hex(32)

    # Configuracion de sesion
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login():
        """Muestra la pagina de login"""
        # Si ya esta logueado, redirigir al dashboard
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/register')
    def register():
        """Muestra la pagina de registro"""
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('register.html')

    @app.route('/logout')
    def logout():
        """Cierra la sesion del usuario"""
        session.clear()
        return redirect(url_for('index'))

    @app.route('/api/login', methods=['POST'])
    def api_login():
        """
        Endpoint POST para autenticar usuarios.
        Por ahora es mock: acepta cualquier usuario con contrasena 'admin123'
        """
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos no proporcionados'
            }), 400

        username = data.get('username', '').strip()
        password = data.get('password', '')

        # Validacion basica de campos vacios
        if not username:
            return jsonify({
                'success': False,
                'message': 'El usuario es requerido'
            }), 400

        if not password:
            return jsonify({
                'success': False,
                'message': 'La contrasena es requerida'
            }), 400

        # Mock de autenticacion - acepta 'admin' con contrasena 'admin123'
        # En produccion, esto se conectaria a la base de datos
        if username == 'admin' and password == 'admin123':
            # Credenciales correctas - crear sesion
            session['user_id'] = 1
            session['username'] = username
            session['logged_in'] = True

            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'redirect': '/dashboard',
                'user': {
                    'id': 1,
                    'username': username
                }
            }), 200
        else:
            # Credenciales incorrectas
            return jsonify({
                'success': False,
                'message': 'Usuario o contrasena incorrectos'
            }), 401

    @app.route('/dashboard')
    def dashboard():
        """Pagina del dashboard (protegida)"""
        if 'user_id' not in session:
            return redirect(url_for('login'))

        return render_template('index.html')

    # Headers de cache para archivos estaticos (videos, imagenes, CSS, JS)
    @app.after_request
    def add_cache_headers(response):
        if 'static' in request.path:
            # Cache de 1 hora para archivos estaticos
            response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    return app
