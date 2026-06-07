import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

logger = logging.getLogger(__name__)

_last_notification_time = {}

COOLDOWN_SECONDS = 60


def get_waha_config():
    return {
        'api_url': current_app.config.get('WAHA_API_URL', ''),
        'session': current_app.config.get('WAHA_SESSION', 'default'),
        'api_key': current_app.config.get('WAHA_API_KEY', ''),
    }


def _should_notify(camera_name):
    now = time.time()
    last_time = _last_notification_time.get(camera_name, 0)
    if now - last_time < COOLDOWN_SECONDS:
        return False
    _last_notification_time[camera_name] = now
    return True


def send_person_detected(camera_name, chat_id, waha_config):
    if not waha_config.get('api_url') or not chat_id:
        return False

    if not _should_notify(camera_name):
        return False

    message = f'⚠️ Persona detectada en la cámara: {camera_name}'

    payload = json.dumps({
        'chatId': chat_id,
        'text': message,
        'session': waha_config['session'],
    }).encode('utf-8')

    url = f"{waha_config['api_url'].rstrip('/')}/api/sendText"
    headers = {'Content-Type': 'application/json'}
    if waha_config.get('api_key'):
        headers['X-Api-Key'] = waha_config['api_key']
    req = Request(url, data=payload, headers=headers, method='POST')

    try:
        with urlopen(req, timeout=10) as response:
            response.read()
        logger.info('Notificacion WhatsApp enviada para camara: %s', camera_name)
        return True
    except (HTTPError, URLError, Exception) as exc:
        logger.warning('Error enviando notificacion WhatsApp: %s', exc)
        return False
