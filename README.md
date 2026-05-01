# IPGuard

Aplicacion web en Flask para monitoreo y control de un sistema de deteccion de personas en camaras IP, con interfaz de acceso, dashboard y asistente IA integrado con Ollama.

## Caracteristicas

- Landing page informativa del proyecto.
- Pantallas de `login` y `register` con interfaz visual personalizada.
- Dashboard protegido por sesion.
- Endpoint de autenticacion mock para pruebas locales.
- Endpoint de chat IA conectado a Ollama.
- Assets estaticos para UI, imagenes y video de fondo.

## Estructura del proyecto

```text
persona/
├── app/
│   ├── __init__.py
│   ├── static/
│   │   ├── assets/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── main.py
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.10 o superior
- `pip`
- Ollama instalado localmente
- Modelo disponible en Ollama:
  - `gemma3:1b`

## Instalacion

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecucion

```powershell
python main.py
```

La aplicacion queda disponible en:

```text
http://127.0.0.1:5000
```

## Rutas principales

- `/` : pagina principal
- `/login` : acceso al sistema
- `/register` : registro visual de usuario
- `/dashboard` : vista protegida
- `/ia` : asistente IA protegido
- `/api/login` : autenticacion mock
- `/api/ia/chat` : chat con Ollama

## Credenciales de prueba actuales

El backend de autenticacion mock acepta:

```text
usuario: admin
contrasena: admin123
```

Esto esta definido en [app/__init__.py](</C:/Users/KOLD/Documents/2026/gestion de proyectos/persona/app/__init__.py>).

## Notas de desarrollo

- `register` actualmente es una vista visual; aun no tiene logica de registro real.
- El proyecto usa sesion Flask en memoria/archivo local.
- El endpoint `/api/ia/chat` requiere que Ollama este activo y que el modelo configurado exista localmente.

## Archivos ignorados por Git

El `.gitignore` excluye:

- entorno virtual
- variables de entorno
- sesiones locales
- dataset `person/`
- modelos y archivos generados
- caches, logs y archivos temporales

## Sugerencias antes de subir a GitHub

1. Reemplazar las credenciales mock por autenticacion real.
2. Mover secretos y configuraciones sensibles a variables de entorno.
3. Agregar pruebas con `pytest`.
4. Documentar despliegue y dependencias de Ollama si el repositorio sera compartido.
# cipherLead
