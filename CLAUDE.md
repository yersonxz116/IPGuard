# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**IPGuard** - Sistema de Detección de Personas en Cámaras IP mediante Red Neuronal Convolucional y Flask. A home security monitoring system that detects persons in IP camera streams using AI (YOLO11s/Faster R-CNN) and sends WhatsApp notifications.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python main.py
# Server starts at http://0.0.0.0:5000
```

**Dependencies:** torch, torchvision, pillow, tqdm, flask, flask-session, opencv-python, ollama

## Architecture

```
project/
├── main.py              # Entry point - imports create_app from app
├── requirements.txt     # Python dependencies
├── app/
│   ├── __init__.py      # App factory (create_app) - ALL routes defined here
│   ├── templates/       # HTML templates (index.html, login.html, ia.html)
│   └── static/
│       ├── css/         # style.css, login.css
│       ├── js/          # main.js
│       └── assets/      # city.mp4, logo.jpeg
└── person/              # Dataset folder for model training
```

## App Factory Pattern

All Flask routes are defined inside `create_app()` in `app/__init__.py`. Do NOT add routes to `main.py` - that file only bootstraps the app.

## Routes (in app/__init__.py)

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page (index.html) |
| `/login` | GET | Login page (redirects if already logged in) |
| `/logout` | GET | Clear session, redirect to index |
| `/api/login` | POST | Authenticate user (admin/admin123) |
| `/dashboard` | GET | Protected dashboard (requires session) |
| `/ia` | GET | AI assistant page (requires session) |
| `/api/ia/chat` | POST | Ollama chat endpoint (requires session) |

## Login System

- Session-based authentication stored in filesystem
- `session['user_id']`, `session['username']`, `session['logged_in']`
- Dashboard and IA routes check for `session['user_id']` and redirect to login if missing
- Hardcoded credentials: `admin` / `admin123`

## Color Scheme (CSS Variables)

```css
--color-primary: #00A86B;    /* Verde - main accent */
--color-primary-dark: #007A4B;
--color-primary-light: #00D68F;
--color-dark: #1A1A1A;      /* Negro - background */
--color-gray: #4A4A4A;       /* Gris - secondary */
--color-light: #F5F5F5;
--color-white: #FFFFFF;
--color-accent: #00FF95;    /* Verde brillante */
```

**Note:** `ia.html` defines its own `:root` variables inline in a `<style>` block (duplicated).

## UI/UX Guidelines

- **Font:** Inter (Google Fonts) - loaded via Google Fonts CDN
- **Icons:** Font Awesome for UI icons, Devicon for technology logos with `colored` class
- **Video Background:** Only in hero section (`position: absolute`), confined to that section only. No parallax or scroll manipulation.
- **Infinite Carousel:** Backend tech uses CSS keyframe animation (`carousel-scroll`), 25 items (5 logos × 5 duplicates) for seamless loop, pauses on hover
- **Frontend Tech:** Displayed as centered flex grid (not carousel) since only 3 items
- **Animations:** Intersection Observer for fade-in effects on cards (`.mv-card`)
- **Navbar:** Uses `.navbar-brand` (logo + text), `.navbar-links`, `.navbar-right` structure

## Frontend Stack

- HTML5, CSS3, JavaScript (vanilla ES6, no framework)
- Font Awesome 6.5.1 for UI icons
- Devicon for technology logos
- Google Fonts (Inter) for typography
- Responsive breakpoints: 768px (tablet), 480px (mobile)

## Backend Stack

- Flask with Flask-Session (filesystem-based sessions)
- Mock authentication (admin/admin123)
- PyTorch for deep learning model (YOLO11s/Faster R-CNN)
- OpenCV for video stream processing
- Ollama (gemma3:1b) for AI assistant
- ESP32 camera modules for IP cameras
- Twilio for WhatsApp notifications (to be implemented)

## AI Assistant (Ollama Integration)

- `/ia` page provides an AI chat interface
- Uses Ollama with `gemma3:1b` model
- Chat endpoint: `POST /api/ia/chat` with `{"message": "..."}` payload
- Response: `{"success": true, "response": "..."}` or error
