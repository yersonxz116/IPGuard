# IPGuard

Aplicacion web en Flask para acceso, monitoreo y gestion de un sistema de camaras IP.

## Caracteristicas

- Pagina principal informativa del proyecto.
- Pantallas de `login` y `register` con interfaz personalizada.
- Dashboard protegido por sesion.
- Endpoint de autenticacion mock para pruebas locales.
- Assets estaticos para interfaz, imagenes y video de fondo.

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
- `/api/login` : autenticacion mock

## Credenciales de prueba actuales

El backend de autenticacion mock acepta:

```text
usuario: admin
contrasena: admin123
```

## Notas de desarrollo

- `register` actualmente es una vista visual; aun no tiene logica de registro real.
- El proyecto usa sesion Flask local.

## Archivos ignorados por Git

El `.gitignore` excluye:

- entorno virtual
- variables de entorno
- sesiones locales
- dataset `person/`
- modelos y archivos generados
- caches, logs y archivos temporales
- archivos locales de asistentes y tooling

## Sugerencias antes de subir a GitHub

1. Reemplazar las credenciales mock por autenticacion real.
2. Mover secretos y configuraciones sensibles a variables de entorno.
3. Agregar pruebas con `pytest`.
