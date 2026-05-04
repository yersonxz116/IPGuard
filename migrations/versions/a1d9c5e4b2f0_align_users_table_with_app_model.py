"""Align users table with current app model

Revision ID: a1d9c5e4b2f0
Revises: 63b768f1f427
Create Date: 2026-05-03 09:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1d9c5e4b2f0'
down_revision = '63b768f1f427'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {column['name'] for column in inspector.get_columns('users')}

    if 'full_name' not in columns:
        op.add_column(
            'users',
            sa.Column('full_name', sa.String(length=150), nullable=True)
        )
        op.execute("UPDATE users SET full_name = username WHERE full_name IS NULL")
        op.alter_column('users', 'full_name', existing_type=sa.String(length=150), nullable=False)


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {column['name'] for column in inspector.get_columns('users')}

    if 'full_name' in columns:
        op.drop_column('users', 'full_name')
