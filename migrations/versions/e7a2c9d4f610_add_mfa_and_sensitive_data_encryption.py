"""Add MFA and encrypted sensitive fields

Revision ID: e7a2c9d4f610
Revises: d4c3b2a190ef
Create Date: 2026-05-15 00:00:00.000000

"""
import base64
import hashlib
import os

from alembic import op
import sqlalchemy as sa
from cryptography.fernet import Fernet
from dotenv import load_dotenv


load_dotenv()


revision = 'e7a2c9d4f610'
down_revision = 'd4c3b2a190ef'
branch_labels = None
depends_on = None

ENCRYPTION_PREFIX = 'enc::'


def _fernet():
    configured_key = os.getenv('DATA_ENCRYPTION_KEY', '')
    if configured_key:
        return Fernet(configured_key.encode())

    secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')
    digest = hashlib.sha256(secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_plaintext(value, fernet):
    if value is None:
        return None
    raw_value = str(value)
    if not raw_value or raw_value.startswith(ENCRYPTION_PREFIX):
        return raw_value
    token = fernet.encrypt(raw_value.encode()).decode()
    return f'{ENCRYPTION_PREFIX}{token}'


def _encrypt_existing_values(connection, table_name, id_column, sensitive_columns):
    fernet = _fernet()
    selected_columns = ', '.join([id_column, *sensitive_columns])
    rows = connection.execute(sa.text(f'SELECT {selected_columns} FROM {table_name}')).mappings().all()

    for row in rows:
        updates = {}
        for column in sensitive_columns:
            encrypted_value = _encrypt_plaintext(row[column], fernet)
            if encrypted_value != row[column]:
                updates[column] = encrypted_value

        if not updates:
            continue

        assignments = ', '.join(f'{column} = :{column}' for column in updates)
        params = {**updates, id_column: row[id_column]}
        connection.execute(
            sa.text(f'UPDATE {table_name} SET {assignments} WHERE {id_column} = :{id_column}'),
            params
        )


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'users' in tables:
        user_columns = {column['name']: column for column in inspector.get_columns('users')}

        if 'full_name' in user_columns and user_columns['full_name']['type'].length != 500:
            op.alter_column(
                'users',
                'full_name',
                existing_type=sa.String(length=user_columns['full_name']['type'].length or 150),
                type_=sa.String(length=500),
                existing_nullable=False
            )

        if 'mfa_secret' not in user_columns:
            op.add_column('users', sa.Column('mfa_secret', sa.String(length=500), nullable=True))

        if 'mfa_enabled' not in user_columns:
            op.add_column(
                'users',
                sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.false())
            )
            op.alter_column('users', 'mfa_enabled', server_default=None)

        if 'mfa_confirmed_at' not in user_columns:
            op.add_column('users', sa.Column('mfa_confirmed_at', sa.DateTime(), nullable=True))

    if 'cameras' in tables:
        camera_columns = {column['name']: column for column in inspector.get_columns('cameras')}

        if 'stream_url' in camera_columns and camera_columns['stream_url']['type'].length != 1200:
            op.alter_column(
                'cameras',
                'stream_url',
                existing_type=sa.String(length=camera_columns['stream_url']['type'].length or 500),
                type_=sa.String(length=1200),
                existing_nullable=False
            )

        if 'snapshot_url' in camera_columns and camera_columns['snapshot_url']['type'].length != 1200:
            op.alter_column(
                'cameras',
                'snapshot_url',
                existing_type=sa.String(length=camera_columns['snapshot_url']['type'].length or 500),
                type_=sa.String(length=1200),
                existing_nullable=True
            )

        if 'location' in camera_columns and camera_columns['location']['type'].length != 500:
            op.alter_column(
                'cameras',
                'location',
                existing_type=sa.String(length=camera_columns['location']['type'].length or 120),
                type_=sa.String(length=500),
                existing_nullable=True
            )

    if 'backup_codes' not in tables:
        op.create_table(
            'backup_codes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('code_hash', sa.String(length=255), nullable=False),
            sa.Column('used_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_backup_codes_user_id'), 'backup_codes', ['user_id'], unique=False)

    if 'users' in tables:
        _encrypt_existing_values(connection, 'users', 'id', ['full_name'])

    if 'cameras' in tables:
        camera_columns = {column['name']: column for column in inspector.get_columns('cameras')}
        sensitive_columns = [
            column for column in ['stream_url', 'snapshot_url', 'location']
            if column in camera_columns
        ]
        if sensitive_columns:
            _encrypt_existing_values(connection, 'cameras', 'id', sensitive_columns)


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'backup_codes' in tables:
        op.drop_index(op.f('ix_backup_codes_user_id'), table_name='backup_codes')
        op.drop_table('backup_codes')

    if 'users' in tables:
        user_columns = {column['name']: column for column in inspector.get_columns('users')}
        if 'mfa_confirmed_at' in user_columns:
            op.drop_column('users', 'mfa_confirmed_at')
        if 'mfa_enabled' in user_columns:
            op.drop_column('users', 'mfa_enabled')
        if 'mfa_secret' in user_columns:
            op.drop_column('users', 'mfa_secret')

    if 'cameras' in tables:
        camera_columns = {column['name']: column for column in inspector.get_columns('cameras')}
        if 'location' in camera_columns:
            op.alter_column(
                'cameras',
                'location',
                existing_type=sa.String(length=500),
                type_=sa.String(length=120),
                existing_nullable=True
            )
        if 'snapshot_url' in camera_columns:
            op.alter_column(
                'cameras',
                'snapshot_url',
                existing_type=sa.String(length=1200),
                type_=sa.String(length=500),
                existing_nullable=True
            )
        if 'stream_url' in camera_columns:
            op.alter_column(
                'cameras',
                'stream_url',
                existing_type=sa.String(length=1200),
                type_=sa.String(length=500),
                existing_nullable=False
            )

    if 'users' in tables:
        user_columns = {column['name']: column for column in inspector.get_columns('users')}
        if 'full_name' in user_columns:
            op.alter_column(
                'users',
                'full_name',
                existing_type=sa.String(length=500),
                type_=sa.String(length=150),
                existing_nullable=False
            )
