# IPGuard

Aplicacion web en Flask para monitoreo de camaras IP con deteccion de personas en tiempo real usando MediaPipe Pose, alertas por WhatsApp y autenticacion segura con MFA.

## Que incluye

- Landing page del proyecto con identidad visual de IPGuard.
- Registro de usuarios con persistencia en MySQL.
- Login por `username` o `email`.
- Passwords hasheadas con Werkzeug.
- Cifrado de datos sensibles recuperables con Fernet.
- Autenticacion multifactor con Google Authenticator, codigos de respaldo y archivo privado PEM.
- Migraciones con Flask-Migrate y Alembic.
- Dashboard autenticado para registrar y visualizar camaras IP.
- Stream MJPEG en vivo desde camaras IP en la misma red local.
- Deteccion de personas con MediaPipe Pose (modelo `pose_landmarker_full`).
- Stream procesado con recuadro verde sobre la persona detectada.
- Alertas automaticas por WhatsApp via WAHA cuando se detecta una persona (cooldown 60s por camara).
- Imagen del frame adjunta en la alerta de WhatsApp.
- Compatible con DroidCam, ESP32-CAM y cualquier camara que publique MJPEG.
- Vista `/ia` conectada a Ollama.
- Chat IA responsive con scroll interno solo en el historial de mensajes.

## Stack

- Python 3.10+
- Flask + Flask-SQLAlchemy + Flask-Migrate
- MySQL + PyMySQL
- OpenCV
- MediaPipe
- cryptography (Fernet)
- pyotp + qrcode
- requests
- WAHA (WhatsApp HTTP API — Docker)
- Ollama

## Estructura principal

```text
IPGuard/
├── app/
│   ├── __init__.py          # Rutas, endpoints, factory de Flask
│   ├── extensions.py        # db, migrate
│   ├── models.py            # User, Camera, BackupCode
│   ├── security.py          # Cifrado, TOTP, PEM, codigos de respaldo
│   ├── vision.py            # Deteccion MediaPipe, _FrameReader, stream procesado
│   ├── whatsapp.py          # Cliente WAHA, envio de alertas con imagen
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│       ├── dashboard.html
│       └── ...
├── migrations/
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Requisitos previos

- Python 3.10 o superior
- MySQL Server en `127.0.0.1:3306`
- Modelo MediaPipe en `app/models/pose_landmarker_full.task` (para deteccion de personas)
- Ollama instalado si vas a usar la vista `/ia`
- Docker con WAHA si vas a usar alertas por WhatsApp

---

## Configuracion paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/yersonxz116/IPGuard.git
cd IPGuard
```

### 2. Crear y activar entorno virtual

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear archivo de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
SECRET_KEY=cambia-esto-por-una-clave-larga-y-aleatoria
DATA_ENCRYPTION_KEY=clave-fernet-generada-una-sola-vez
DATABASE_URL=mysql+pymysql://root:tu_password@127.0.0.1:3306/camera_detection_db
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=gemma3:1b
MFA_ISSUER_NAME=IPGuard
WAHA_API_URL=http://127.0.0.1:3001
WAHA_SESSION=default
```

**Generar `DATA_ENCRYPTION_KEY` una sola vez:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> ⚠️ No cambies `DATA_ENCRYPTION_KEY` despues de haber guardado datos. Los registros cifrados con otra clave no se podran descifrar.

---

### 5. Configurar MySQL

Entra a MySQL y crea la base de datos:

```sql
CREATE DATABASE camera_detection_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Opcional — crear usuario dedicado:
```sql
CREATE USER 'ipguard'@'localhost' IDENTIFIED BY 'tu_password';
GRANT ALL PRIVILEGES ON camera_detection_db.* TO 'ipguard'@'localhost';
FLUSH PRIVILEGES;
```

### 6. Aplicar migraciones

```bash
flask db upgrade
```

> No ejecutes `flask db init` si la carpeta `migrations/` ya existe en el repo.

### 7. Descargar el modelo de MediaPipe

Descarga `pose_landmarker_full.task` desde la web de MediaPipe y colócalo en:

```text
app/models/pose_landmarker_full.task
```

Sin este archivo la app arranca igual, pero la deteccion de personas no estara disponible.

### 8. Ejecutar la aplicacion

```bash
python run.py
```

La app queda disponible en:
```
http://127.0.0.1:5002
```

---

## Configurar WAHA (alertas WhatsApp)

WAHA es una API HTTP para WhatsApp que corre en Docker.

### Instalar y levantar WAHA

```bash
docker run -d \
  --name waserver \
  -p 3001:3000 \
  devlikeapro/waha
```

### Crear sesion

```bash
curl -X POST http://127.0.0.1:3001/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "default"}'
```

### Escanear QR

```bash
curl http://127.0.0.1:3001/api/screenshot?session=default
```

Abre la imagen que devuelve y escanea el QR con WhatsApp en tu telefono.

### Verificar que esta conectado

```bash
curl http://127.0.0.1:3001/api/sessions/default
```

Debe mostrar `"status": "WORKING"`.

### Configurar en `.env`

```env
WAHA_API_URL=http://127.0.0.1:3001
WAHA_SESSION=default
```

> ⚠️ No uses el dominio de Cloudflare para WAHA desde el servidor — usa siempre `127.0.0.1:3001` directo. Cloudflare bloquea con error 1010.

### Configurar numero de WhatsApp en el dashboard

En la seccion de configuracion del dashboard, ingresa tu numero en formato internacional sin `+`:

```
573167821687
```

---

## Configurar camaras IP

### DroidCam (telefono como camara)

1. Instala DroidCam en tu telefono (Android/iOS).
2. Conecta el telefono a la misma red WiFi que el servidor.
3. Abre DroidCam — muestra la IP y puerto (por defecto puerto `4747`).
4. En IPGuard registra la camara con:
   - **Stream URL:** `http://192.168.x.x:4747/video`
   - **Snapshot URL** (opcional): `http://192.168.x.x:4747/shot.jpg`

> La camara debe estar en la misma red local que el servidor para que el stream sea accesible.

### ESP32-CAM

Registra la camara con:
- **Stream URL:** `http://192.168.x.x/stream` o `http://192.168.x.x:81/stream`
- **Snapshot URL** (opcional): `http://192.168.x.x/capture`

### Cualquier camara MJPEG

Cualquier URL que devuelva `multipart/x-mixed-replace` funciona como stream.

---

## Deteccion de personas

La deteccion usa MediaPipe Pose Landmarker con estas configuraciones:

- Confianza minima de deteccion: `0.70`
- Confianza minima de presencia: `0.70`
- Confianza minima de seguimiento: `0.60`
- Solo se confirma una deteccion tras **4 frames consecutivos** con persona valida
- Se valida que esten visibles landmarks de hombros, cadera, rodillas y tobillos
- Alerta WhatsApp con cooldown de **60 segundos** por camara

---

## Configurar Ollama (IA)

```bash
ollama serve
ollama pull gemma3:1b
```

Si usas otro modelo, cambia `OLLAMA_MODEL` en `.env`.

---

## Flujo completo de arranque

```bash
# 1. Entorno virtual
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# o .\venv\Scripts\Activate.ps1  # Windows

# 2. Dependencias
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env
# Edita .env con tus valores

# 4. Migraciones
flask db upgrade

# 5. (Opcional) Levantar WAHA
docker start waserver

# 6. (Opcional) Levantar Ollama
ollama serve &

# 7. Arrancar IPGuard
python run.py
```

---

## Rutas principales

| Ruta | Descripcion |
|------|-------------|
| `/` | Homepage / landing |
| `/login` | Acceso con usuario o email |
| `/register` | Registro de usuario |
| `/dashboard` | Vista principal protegida |
| `/security` | MFA, codigos de respaldo, PEM, cambio de contrasena |
| `/mfa/verify` | Verificacion del segundo factor |
| `/ia` | Chat IA con Ollama |
| `/api/cameras` | `POST` — registrar camara |
| `/api/cameras/<id>` | `DELETE` — eliminar camara |
| `/api/cameras/<id>/stream` | Stream MJPEG procesado con deteccion |
| `/api/cameras/<id>/detection` | `POST` — activar/desactivar deteccion |
| `/api/whatsapp` | `POST` — guardar numero de WhatsApp |
| `/api/login` | Autenticacion JSON |
| `/api/mfa/verify` | Verificacion TOTP / respaldo / PEM |
| `/api/ia/chat` | Consulta al modelo Ollama |

---

## Seguridad y MFA

La app incluye tres formas de segundo factor:

- **Google Authenticator** — codigo TOTP de 6 digitos cada 30s
- **Codigos de respaldo** — codigos de un solo uso generados al activar MFA
- **Archivo PEM** — clave RSA privada local que firma un reto temporal

### Campos cifrados con Fernet

- `users.full_name`
- `users.mfa_secret`
- `users.pem_public_key`
- `cameras.stream_url`
- `cameras.snapshot_url`
- `cameras.location`

---

## Archivos ignorados por git

- `venv/`, `.venv/`, `env/`
- `.env`
- Caches y logs
- Pesos de modelos (`*.task`, `*.tflite`)
- Archivos PEM privados
- Sesiones y tokens locales

---

## Verificacion basica post-instalacion

1. `/` carga la landing correctamente.
2. `/register` crea usuarios en MySQL.
3. `/login` permite entrar con `username` o `email`.
4. `/dashboard` redirige a login si no hay sesion activa.
5. Agregar una camara con DroidCam muestra el stream en vivo.
6. Con el modelo MediaPipe presente, el dashboard marca "Deteccion en PC activa".
7. Al detectar una persona, llega un mensaje de WhatsApp con imagen (si WAHA esta configurado).
8. `/ia` responde si Ollama esta activo.
9. `/security` permite activar Google Authenticator y descargar el PEM.
