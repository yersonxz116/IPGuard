import logging
import os
import subprocess
import sys
from pathlib import Path


def _use_project_venv():
    """Relanza la app con el venv local si el comando usa otro Python."""
    venv_python = Path(__file__).resolve().parent / 'venv' / 'Scripts' / 'python.exe'
    if not venv_python.exists():
        return

    current_python = os.path.normcase(os.path.abspath(sys.executable))
    project_python = os.path.normcase(os.path.abspath(venv_python))
    if current_python != project_python:
        command = [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]]
        raise SystemExit(subprocess.call(command))


if __name__ == '__main__':
    _use_project_venv()

from app import create_app

# Configuración de logging para debug
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
