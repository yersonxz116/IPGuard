"""Add whatsapp_number to users

Revision ID: c1d155fdc075
Revises: f13c8b5a7d20
Create Date: 2026-05-15 12:43:16.703902

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1d155fdc075'
down_revision = 'f13c8b5a7d20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('whatsapp_number', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('whatsapp_number')
