import base64
import hashlib
import io
import secrets
from datetime import datetime

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash


ENCRYPTION_PREFIX = 'enc::'


def _fernet_key():
    configured_key = current_app.config.get('DATA_ENCRYPTION_KEY')
    if configured_key:
        return configured_key.encode()

    digest = hashlib.sha256(current_app.config['SECRET_KEY'].encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(value):
    """Encrypt a recoverable sensitive value, preserving empty values."""
    if value is None:
        return None

    raw_value = str(value)
    if not raw_value or raw_value.startswith(ENCRYPTION_PREFIX):
        return raw_value

    token = Fernet(_fernet_key()).encrypt(raw_value.encode()).decode()
    return f'{ENCRYPTION_PREFIX}{token}'


def decrypt_value(value):
    """Decrypt a value encrypted by encrypt_value; legacy plaintext is returned."""
    if value is None:
        return None

    raw_value = str(value)
    if not raw_value.startswith(ENCRYPTION_PREFIX):
        return raw_value

    token = raw_value[len(ENCRYPTION_PREFIX):]
    try:
        return Fernet(_fernet_key()).decrypt(token.encode()).decode()
    except InvalidToken:
        return ''


def generate_totp_secret():
    return pyotp.random_base32()


def totp_uri(secret, username):
    return pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=current_app.config.get('MFA_ISSUER_NAME', 'IPGuard')
    )


def verify_totp(secret, code):
    if not secret or not code:
        return False

    return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=1)


def generate_pem_challenge():
    return secrets.token_urlsafe(32)


def validate_public_key_pem(public_key_pem):
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
    except (TypeError, ValueError):
        return False
    return isinstance(public_key, rsa.RSAPublicKey)


def verify_pem_signature(public_key_pem, challenge, signature_b64):
    if not public_key_pem or not challenge or not signature_b64:
        return False

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            challenge.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except (InvalidSignature, TypeError, ValueError):
        return False

    return True


def qr_code_data_uri(uri):
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f'data:image/png;base64,{encoded}'


def generate_backup_code():
    left = secrets.token_hex(3).upper()
    right = secrets.token_hex(3).upper()
    return f'{left}-{right}'


def generate_backup_codes(count=10):
    return [generate_backup_code() for _ in range(count)]


def hash_backup_code(code):
    return generate_password_hash(normalize_backup_code(code))


def verify_backup_code(code_hash, code):
    return check_password_hash(code_hash, normalize_backup_code(code))


def normalize_backup_code(code):
    return str(code or '').strip().upper().replace(' ', '')


def now_utc():
    return datetime.utcnow()
