"""Add PEM public key factor

Revision ID: f13c8b5a7d20
Revises: e7a2c9d4f610
Create Date: 2026-05-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f13c8b5a7d20'
down_revision = 'e7a2c9d4f610'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'users' not in tables:
        return

    columns = {column['name']: column for column in inspector.get_columns('users')}
    if 'pem_public_key' not in columns:
        op.add_column('users', sa.Column('pem_public_key', sa.Text(), nullable=True))


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'users' not in tables:
        return

    columns = {column['name']: column for column in inspector.get_columns('users')}
    if 'pem_public_key' in columns:
        op.drop_column('users', 'pem_public_key')
