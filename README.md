# IPGuard

Aplicacion web en Flask para gestion de acceso, autenticacion de usuarios y consultas IA para un sistema de camaras IP.

## Que incluye

- Landing page del proyecto con identidad visual de IPGuard.
- Registro de usuarios con persistencia en MySQL.
- Login por `username` o `email`.
- Passwords hasheadas con Werkzeug.
- Cifrado de datos sensibles recuperables con Fernet.
- Autenticacion multifactor con Google Authenticator, codigos de respaldo y archivo privado PEM.
- Migraciones con Flask-Migrate y Alembic.
- Dashboard autenticado para registrar y visualizar camaras IP.
- Deteccion de personas en streams de camaras IP con OpenCV y MediaPipe Pose.
- Stream MJPEG procesado en el servidor con recuadro sobre la persona detectada.
- Vista `/ia` conectada a Ollama.
- Chat IA responsive con scroll interno solo en el historial de mensajes.
- Compatible con ESP32-CAM que publica imagenes por `http://IP/foto`.

## Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- MySQL
- PyMySQL
- cryptography
- pyotp
- qrcode
- OpenCV
- MediaPipe
- Ollama

## Estructura principal

```text
persona/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── static/
│   │   ├── assets/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── migrations/
├── config.py
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Requisitos

- Python 3.10 o superior
- `pip`
- MySQL Server disponible en `127.0.0.1:3306`
- Modelo local de MediaPipe en `app/models/pose_landmarker_full.task` para activar deteccion de personas
- Ollama instalado si vas a usar la vista `/ia`

## Preparar un equipo nuevo

### 1. Clonar el repositorio

```powershell
git clone <URL_DEL_REPO>
cd persona
```

### 2. Crear y activar entorno virtual

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 4. Crear archivo de entorno

```powershell
Copy-Item .env.example .env
```

Configura `.env` con tus valores reales:

```env
SECRET_KEY=pon-aqui-una-clave-segura
DATA_ENCRYPTION_KEY=clave-fernet-generada-una-sola-vez
DATABASE_URL=mysql+pymysql://root:tu_password@127.0.0.1:3306/camera_detection_db
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=gemma3:1b
MFA_ISSUER_NAME=IPGuard
```

Genera `DATA_ENCRYPTION_KEY` una sola vez y conservala fija:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

No cambies `DATA_ENCRYPTION_KEY` despues de cifrar datos, porque los valores ya guardados no se podrian descifrar con una clave distinta.

## Configurar MySQL desde cero

Entra a MySQL y crea la base de datos:

```sql
CREATE DATABASE camera_detection_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Si vas a usar un usuario distinto a `root`, crea el usuario y dale permisos:

```sql
CREATE USER 'ipguard_user'@'localhost' IDENTIFIED BY 'tu_password';
GRANT ALL PRIVILEGES ON camera_detection_db.* TO 'ipguard_user'@'localhost';
FLUSH PRIVILEGES;
```

Si usas ese usuario, actualiza `DATABASE_URL`:

```env
DATABASE_URL=mysql+pymysql://ipguard_user:tu_password@127.0.0.1:3306/camera_detection_db
```

## Migraciones

### En un equipo nuevo

El repositorio ya incluye la carpeta `migrations/`, asi que solo debes aplicar las migraciones existentes:

```powershell
flask --app main:app db upgrade
```

### Si necesitas crear una migracion nueva

Esto solo aplica cuando cambias modelos:

```powershell
flask --app main:app db migrate -m "Describe el cambio"
flask --app main:app db upgrade
```

### No hagas esto en un clon nuevo

No ejecutes `flask db init` en una maquina nueva si la carpeta `migrations/` ya existe en el repositorio.

## Seguridad y autenticacion multifactor

La aplicacion incluye cifrado de datos sensibles y tres alternativas de segundo factor. El usuario puede completar el acceso con cualquiera de estas opciones:

- Google Authenticator: codigo TOTP de 6 digitos.
- Codigos de respaldo: codigos de un solo uso generados al activar MFA.
- Archivo privado PEM: archivo local que firma un reto temporal de login.

### Cifrado de datos sensibles

El cifrado recuperable se implementa con `cryptography.Fernet` en `app/security.py`. Los modelos usan propiedades para cifrar al guardar y descifrar al leer.

Campos cifrados:

- `users.full_name`
- `users.mfa_secret`
- `users.pem_public_key`
- `cameras.stream_url`
- `cameras.snapshot_url`
- `cameras.location`

Las contrasenas no se cifran: se guardan como hash con Werkzeug. Los codigos de respaldo tampoco se guardan en texto plano: se guardan como hash y se invalidan al usarse.

### Google Authenticator

Desde `/security`, el usuario puede activar MFA escaneando un codigo QR con Google Authenticator o una app TOTP compatible.

Implementacion:

- El servidor genera un secreto TOTP con `pyotp`.
- El secreto se guarda cifrado en `users.mfa_secret`.
- En login, despues de usuario y contrasena, se valida el codigo TOTP.
- Tambien se exige TOTP para operaciones sensibles como cambio de contrasena o regeneracion de codigos de respaldo.

### Codigos de respaldo

Al activar MFA se generan codigos de respaldo de un solo uso.

Implementacion:

- Se muestran una sola vez al usuario.
- Se guarda solo el hash en la tabla `backup_codes`.
- Cada codigo queda marcado como usado cuando se utiliza.
- Los codigos se pueden regenerar desde `/security`; al regenerarlos, los anteriores quedan invalidados.

### Archivo privado PEM

El archivo PEM es una alternativa al codigo TOTP y a los codigos de respaldo. Esta pensado para un flujo similar al uso de claves en servidores, pero adaptado a una app web.

Implementacion:

- En `/security`, el navegador puede generar una llave RSA.
- La clave publica se registra en la cuenta y se guarda cifrada en `users.pem_public_key`.
- El archivo privado `ipguard-login-key.pem` se descarga y queda solo en el equipo del usuario.
- Durante el login, el servidor genera un reto temporal.
- El navegador firma ese reto con el archivo privado PEM usando WebCrypto.
- Flask verifica la firma con la clave publica guardada.
- La clave privada no se envia al servidor.

Notas del formato PEM:

- El archivo privado generado por la app usa formato PKCS#8:

```text
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
```

- La clave publica registrada usa formato SPKI:

```text
-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----
```

No se aceptan claves OpenSSH tipo `ssh-rsa ...` ni claves publicas con encabezado `-----BEGIN RSA PUBLIC KEY-----`.

## Configurar Ollama

La ruta `/ia` depende de Ollama. Si no lo tienes listo, el chat respondera con error de conexion.

Pasos minimos:

```powershell
ollama serve
ollama pull gemma3:1b
```

Si usas otro modelo, cambia `OLLAMA_MODEL` en `.env`.

## Deteccion con OpenCV y MediaPipe

Cambios aplicados el 2026-05-06:

- Se agregaron `opencv-python` y `mediapipe` a `requirements.txt`.
- Se agrego `app/vision.py` para cargar dependencias de vision de forma perezosa.
- Se integro MediaPipe Pose con el modelo local `app/models/pose_landmarker_full.task`.
- Se agrego procesamiento de stream MJPEG para dibujar un recuadro sobre la persona detectada.
- Se agrego el endpoint protegido `/api/cameras/<id>/processed_stream`.
- El dashboard usa el stream procesado cuando la deteccion esta disponible y conserva el stream original como fallback.

Para que la deteccion funcione, confirma que existe este archivo:

```text
app/models/pose_landmarker_full.task
```

Si falta OpenCV, MediaPipe o el modelo local, el dashboard mantiene la camara visible, pero marca la deteccion como no disponible o muestra un frame de estado.

## Ejecutar la aplicacion

```powershell
python main.py
```

La app queda disponible en:

```text
http://127.0.0.1:5000
```

## Flujo recomendado de arranque completo

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
flask --app main:app db upgrade
python main.py
```

Si tambien vas a usar IA:

```powershell
ollama serve
ollama pull gemma3:1b
```

## Rutas principales

- `/` : homepage
- `/login` : acceso
- `/register` : registro de usuario
- `/dashboard` : vista protegida por sesion
- `/security` : configuracion de MFA, codigos de respaldo, archivo PEM y cambio de contrasena
- `/mfa/verify` : verificacion del segundo factor despues del login
- `/api/cameras` : registrar camara IP
- `/api/cameras/<id>` : eliminar camara IP
- `/api/cameras/<id>/processed_stream` : stream MJPEG procesado con OpenCV y MediaPipe
- `/ia` : chat IA publico
- `/api/login` : autenticacion JSON
- `/api/mfa/verify` : verificacion TOTP, codigo de respaldo o firma PEM
- `/api/ia/chat` : consulta al modelo de Ollama

## Verificacion manual basica

Despues de levantar el proyecto, valida:

1. `/` carga correctamente.
2. `/register` crea usuarios en MySQL.
3. `/login` permite entrar con `username` o `email`.
4. `/dashboard` redirige a login si no hay sesion.
5. `/dashboard` permite agregar una camara y mostrar su stream.
6. En una camara con stream compatible, el dashboard muestra la deteccion en PC activa.
7. El boton de deteccion permite alternar entre stream procesado y stream original.
8. `/api/cameras/<id>/processed_stream` entrega un MJPEG si la camara y el modelo estan disponibles.
9. `/ia` abre el chat.
10. `/api/ia/chat` responde si Ollama esta activo.
11. `/security` permite activar Google Authenticator y muestra codigos de respaldo.
12. `/security` permite generar y registrar el archivo PEM.
13. Con MFA o PEM activo, `/login` redirige a `/mfa/verify`.
14. `/mfa/verify` permite entrar con Authenticator, codigo de respaldo o archivo PEM si esta registrado.

## Notas tecnicas

- La app carga variables de entorno desde `.env` con `python-dotenv`.
- La configuracion vive en `config.py`.
- La inicializacion de Flask, rutas y endpoint de IA viven en `app/__init__.py`.
- La logica de cifrado, TOTP, codigos de respaldo y verificacion PEM vive en `app/security.py`.
- La deteccion con OpenCV y MediaPipe vive en `app/vision.py`.
- El modelo `User` vive en `app/models.py`.

## Archivos que no deben subirse

El repositorio ya ignora:

- `venv/`, `.venv/`, `env/`
- `.env`
- caches y logs
- datasets locales como `person/`
- pesos de modelos
- archivos del editor
- sesiones y tokens locales
- archivos privados `.pem`

## Antes de subir al repo

1. Verifica que `.env` no este trackeado.
2. Verifica que `venv/` no este trackeado.
3. Ejecuta `flask --app main:app db upgrade` en local para confirmar que las migraciones aplican.
4. Prueba registro, login y `/ia`.
