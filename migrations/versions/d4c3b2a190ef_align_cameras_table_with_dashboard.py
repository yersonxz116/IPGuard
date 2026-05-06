"""Align cameras table with dashboard model

Revision ID: d4c3b2a190ef
Revises: b8f8c0d4e2aa
Create Date: 2026-05-03 21:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4c3b2a190ef'
down_revision = 'b8f8c0d4e2aa'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'cameras' not in tables:
        return

    columns = {column['name']: column for column in inspector.get_columns('cameras')}

    if 'stream_url' not in columns and 'ip_url' in columns:
        op.execute(
            "ALTER TABLE cameras CHANGE COLUMN ip_url stream_url VARCHAR(500) NOT NULL"
        )
        inspector = sa.inspect(connection)
        columns = {column['name']: column for column in inspector.get_columns('cameras')}

    if 'snapshot_url' not in columns:
        op.add_column('cameras', sa.Column('snapshot_url', sa.String(length=500), nullable=True))

    if 'location' not in columns:
        op.add_column('cameras', sa.Column('location', sa.String(length=120), nullable=True))

    if 'is_active' in columns and columns['is_active']['nullable']:
        op.execute("UPDATE cameras SET is_active = 1 WHERE is_active IS NULL")
        op.alter_column(
            'cameras',
            'is_active',
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.true()
        )


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'cameras' not in tables:
        return

    columns = {column['name']: column for column in inspector.get_columns('cameras')}

    if 'location' in columns:
        op.drop_column('cameras', 'location')

    if 'snapshot_url' in columns:
        op.drop_column('cameras', 'snapshot_url')

    inspector = sa.inspect(connection)
    columns = {column['name']: column for column in inspector.get_columns('cameras')}
    if 'stream_url' in columns and 'ip_url' not in columns:
        op.execute(
            "ALTER TABLE cameras CHANGE COLUMN stream_url ip_url VARCHAR(500) NOT NULL"
        )
