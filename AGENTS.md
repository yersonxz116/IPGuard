# Repository Guidelines

## Project Structure & Module Organization
`main.py` is the Flask entry point and should stay thin. Core app logic lives in `app/__init__.py`, where `create_app()` defines routes, session behavior, and the Ollama chat endpoint. Templates are in `app/templates/` (`index.html`, `login.html`, `ia.html`), static files are in `app/static/css/`, `app/static/js/`, and `app/static/assets/`. The `person/` directory is a local dataset for model work and should be treated as generated data, not app code. Keep `venv/` out of edits and commits.

## Build, Test, and Development Commands
Create or activate a virtual environment before working:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

`python main.py` starts the Flask server on `http://0.0.0.0:5000` with debug enabled. If you add a new dependency, update `requirements.txt` in the same change.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation. Use `snake_case` for Python functions, variables, and route helpers; keep template and static filenames lowercase (`login.js`, `style.css`). Keep route handlers inside `create_app()` and avoid adding application logic to `main.py`. Prefer short docstrings for non-obvious endpoints and keep user-facing messages in Spanish consistent with the existing UI.

## Testing Guidelines
There is no test suite yet. Add new tests under a top-level `tests/` package using `pytest`, with filenames like `test_login.py`. For now, verify changes by running `python main.py` and exercising `/login`, `/dashboard`, and `/api/ia/chat`. If you add ML or vision utilities later, isolate them into importable modules so they can be unit-tested without starting Flask.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so no repository-specific commit convention can be inferred. Use short imperative commit messages such as `Add login error handling` or `Refactor Ollama chat route`. Pull requests should include: a concise summary, affected routes or assets, setup notes for new dependencies or models, and screenshots for template or CSS changes.

## Security & Configuration Tips
Do not commit `.env`, session files, model weights, or dataset assets. Replace hardcoded secrets and demo credentials before production use, and document any required local services such as Ollama models in the PR description.
