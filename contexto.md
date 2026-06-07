# Contexto del Proyecto — IPGuard

## Descripcion General

**IPGuard** es un sistema de seguridad domestica que monitorea camaras IP en tiempo real, detecta personas mediante inteligencia artificial y envia notificaciones por WhatsApp cuando se identifica presencia humana. Fue disenado para funcionar con camaras ESP32-CAM y aplicaciones como DroidCam.

## Stack Tecnologico

### Backend

| Tecnologia | Funcion |
|-----------|---------|
| **Python 3** | Lenguaje principal del servidor |
| **Flask** | Framework web (patron app factory) |
| **Flask-SQLAlchemy** | ORM para interactuar con la base de datos |
| **Flask-Migrate (Alembic)** | Migraciones de esquema de base de datos |
| **PyMySQL** | Driver de conexion a MySQL |
| **python-dotenv** | Carga de variables de entorno desde `.env` |
| **Werkzeug** | Hashing de contrasenas (scrypt) |
| **cryptography (Fernet)** | Encriptacion en reposo de campos sensibles |
| **pyotp** | Generacion y verificacion de codigos TOTP (Google Authenticator) |
| **qrcode** | Generacion de codigos QR para configuracion MFA |

### Deteccion de Personas

| Tecnologia | Funcion |
|-----------|---------|
| **MediaPipe Pose** | Modelo de deteccion de poses humanas (modo VIDEO) |
| **OpenCV (cv2)** | Captura de video, procesamiento de frames y codificacion MJPEG |
| **Modelo:** `pose_landmarker_full.task` | Archivo local de MediaPipe (no incluido en git) |

### Notificaciones WhatsApp

| Tecnologia | Funcion |
|-----------|---------|
| **WAHA (WhatsApp HTTP API)** | Contenedor Docker que expone WhatsApp como API REST |
| **Docker** | Ejecuta el servicio WAHA localmente |
| **Protocolo:** HTTP POST a `/api/sendText` | Envio de mensajes con header `X-Api-Key` |

### Inteligencia Artificial (Chat)

| Tecnologia | Funcion |
|-----------|---------|
| **Ollama** | Servidor local de modelos de lenguaje |
| **gemma3:1b** | Modelo de lenguaje para el chat integrado |
| **Protocolo:** HTTP POST via `urllib` | Comunicacion con Ollama (sin SDK externo) |

### Frontend

| Tecnologia | Funcion |
|-----------|---------|
| **HTML5 + Jinja2** | Templates del servidor |
| **CSS3 (variables custom)** | Estilos con tema oscuro verde/negro |
| **JavaScript (vanilla)** | Interactividad del dashboard sin frameworks |
| **Font Awesome 6.5.1** | Iconografia (vendored localmente) |
| **Devicon** | Logos de tecnologias (vendored localmente) |
| **Google Fonts (Inter)** | Tipografia principal |

### Base de Datos

| Tecnologia | Funcion |
|-----------|---------|
| **MySQL** | Base de datos relacional principal |
| **Base:** `camera_detection_db` | Nombre de la base de datos |
| **Tablas:** `users`, `cameras`, `backup_codes` | Modelos principales |

### Hardware Compatible

| Dispositivo | Uso |
|------------|-----|
| **ESP32-CAM** | Camara IP economica con stream MJPEG (`/stream`, `/capture`) |
| **DroidCam** | App Android que convierte el celular en camara IP (`/video`) |
| **Cualquier camara MJPEG** | Endpoints tipo `/stream`, `/mjpeg`, `.mjpg` |

## Arquitectura del Sistema

```
[Camara IP / DroidCam / ESP32-CAM]
        |
        | Stream MJPEG (HTTP)
        v
[Flask Backend (Python)]
        |
        |--- OpenCV captura frames
        |--- MediaPipe Pose analiza cada frame
        |--- Si detecta persona:
        |       |
        |       v
        |   [WAHA Docker] ---> WhatsApp (notificacion)
        |
        v
[Dashboard Web (navegador)]
        |
        |--- Stream MJPEG con bounding boxes
        |--- Toggle deteccion (sin cortar stream)
        |--- Gestion de camaras
        |--- Chat IA (Ollama)
```

## Seguridad Implementada

- **Autenticacion multifactor (MFA):** Contrasena + TOTP (Google Authenticator) + Archivo PEM (RSA)
- **Encriptacion en reposo:** Campos sensibles encriptados con Fernet (AES-128-CBC). Prefijo `enc::` identifica valores encriptados en la base de datos
- **Codigos de respaldo:** 10 codigos de un solo uso (`XXXXXX-XXXXXX`) hasheados con scrypt
- **Sesiones:** Flask session con `SECRET_KEY` para firmado

## Servicios Externos Requeridos

1. **MySQL** — Puerto 3306 (debe estar corriendo antes de iniciar la app)
2. **WAHA (Docker)** — Puerto 3000 (necesario para notificaciones WhatsApp)
3. **Ollama** — Puerto 11434 (necesario para el chat IA)

## Variables de Entorno (.env)

```
SECRET_KEY=<clave-secreta-para-sesiones>
DATA_ENCRYPTION_KEY=<clave-fernet-44-caracteres>
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/camera_detection_db
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=gemma3:1b
MFA_ISSUER_NAME=IPGuard
WAHA_API_URL=http://localhost:3000
WAHA_SESSION=default
WAHA_API_KEY=mykey123
```

## Flujo de Deteccion y Notificacion

1. El usuario registra una camara en el dashboard (URL del stream)
2. Al abrir el dashboard, Flask abre una conexion al stream de la camara
3. Cada frame se procesa con MediaPipe Pose buscando landmarks humanos
4. Si se detectan >= 4 landmarks visibles, se dibuja un bounding box verde
5. Se envia una notificacion WhatsApp al numero configurado por el usuario
6. Cooldown de 1 minuto por camara para evitar spam
7. El usuario puede activar/desactivar la deteccion sin interrumpir el stream

## Comandos para Ejecutar

```bash
# Iniciar MySQL (debe estar corriendo)
# Iniciar Docker Desktop + contenedor WAHA
docker start waha

# Iniciar Ollama (para chat IA)
ollama serve

# Iniciar la aplicacion
python main.py
```

La app queda disponible en `http://127.0.0.1:5000`.
