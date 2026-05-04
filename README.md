# IPGuard

Aplicacion web en Flask para gestion de acceso, autenticacion de usuarios y consultas IA para un sistema de camaras IP.

## Que incluye

- Landing page del proyecto con identidad visual de IPGuard.
- Registro de usuarios con persistencia en MySQL.
- Login por `username` o `email`.
- Passwords hasheadas con Werkzeug.
- Migraciones con Flask-Migrate y Alembic.
- Vista `/ia` conectada a Ollama.
- Chat IA responsive con scroll interno solo en el historial de mensajes.

## Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- MySQL
- PyMySQL
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
DATABASE_URL=mysql+pymysql://root:tu_password@127.0.0.1:3306/camera_detection_db
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=gemma3:1b
```

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

## Configurar Ollama

La ruta `/ia` depende de Ollama. Si no lo tienes listo, el chat respondera con error de conexion.

Pasos minimos:

```powershell
ollama serve
ollama pull gemma3:1b
```

Si usas otro modelo, cambia `OLLAMA_MODEL` en `.env`.

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
- `/ia` : chat IA publico
- `/api/login` : autenticacion JSON
- `/api/ia/chat` : consulta al modelo de Ollama

## Verificacion manual basica

Despues de levantar el proyecto, valida:

1. `/` carga correctamente.
2. `/register` crea usuarios en MySQL.
3. `/login` permite entrar con `username` o `email`.
4. `/dashboard` redirige a login si no hay sesion.
5. `/ia` abre el chat.
6. `/api/ia/chat` responde si Ollama esta activo.

## Notas tecnicas

- La app carga variables de entorno desde `.env` con `python-dotenv`.
- La configuracion vive en `config.py`.
- La inicializacion de Flask, rutas y endpoint de IA viven en `app/__init__.py`.
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

## Antes de subir al repo

1. Verifica que `.env` no este trackeado.
2. Verifica que `venv/` no este trackeado.
3. Ejecuta `flask --app main:app db upgrade` en local para confirmar que las migraciones aplican.
4. Prueba registro, login y `/ia`.
