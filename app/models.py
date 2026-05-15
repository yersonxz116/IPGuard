from datetime import datetime

from .extensions import db
from .security import decrypt_value, encrypt_value


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    _full_name = db.Column('full_name', db.String(500), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    _mfa_secret = db.Column('mfa_secret', db.String(500), nullable=True)
    _pem_public_key = db.Column('pem_public_key', db.Text, nullable=True)
    mfa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    mfa_confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cameras = db.relationship(
        'Camera',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy=True
    )
    backup_codes = db.relationship(
        'BackupCode',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy=True
    )

    @property
    def full_name(self):
        return decrypt_value(self._full_name)

    @full_name.setter
    def full_name(self, value):
        self._full_name = encrypt_value(value)

    @property
    def mfa_secret(self):
        return decrypt_value(self._mfa_secret)

    @mfa_secret.setter
    def mfa_secret(self, value):
        self._mfa_secret = encrypt_value(value)

    @property
    def pem_public_key(self):
        return decrypt_value(self._pem_public_key)

    @pem_public_key.setter
    def pem_public_key(self, value):
        self._pem_public_key = encrypt_value(value)

    @property
    def pem_enabled(self):
        return bool(self.pem_public_key)

    def __repr__(self):
        return f'<User {self.username}>'


class Camera(db.Model):
    __tablename__ = 'cameras'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    _stream_url = db.Column('stream_url', db.String(1200), nullable=False)
    _snapshot_url = db.Column('snapshot_url', db.String(1200), nullable=True)
    _location = db.Column('location', db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', back_populates='cameras')

    @property
    def stream_url(self):
        return decrypt_value(self._stream_url)

    @stream_url.setter
    def stream_url(self, value):
        self._stream_url = encrypt_value(value)

    @property
    def snapshot_url(self):
        return decrypt_value(self._snapshot_url)

    @snapshot_url.setter
    def snapshot_url(self, value):
        self._snapshot_url = encrypt_value(value)

    @property
    def location(self):
        return decrypt_value(self._location)

    @location.setter
    def location(self, value):
        self._location = encrypt_value(value)

    def __repr__(self):
        return f'<Camera {self.name}>'


class BackupCode(db.Model):
    __tablename__ = 'backup_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', back_populates='backup_codes')

    def __repr__(self):
        status = 'used' if self.used_at else 'available'
        return f'<BackupCode {self.user_id} {status}>'
