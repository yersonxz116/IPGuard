"""Create cameras table

Revision ID: b8f8c0d4e2aa
Revises: a1d9c5e4b2f0
Create Date: 2026-05-03 21:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8f8c0d4e2aa'
down_revision = 'a1d9c5e4b2f0'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if 'cameras' not in tables:
        op.create_table(
            'cameras',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('stream_url', sa.String(length=500), nullable=False),
            sa.Column('snapshot_url', sa.String(length=500), nullable=True),
            sa.Column('location', sa.String(length=120), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    indexes = {index['name'] for index in inspector.get_indexes('cameras')}
    index_name = 'ix_cameras_user_id'
    if index_name not in indexes:
        with op.batch_alter_table('cameras', schema=None) as batch_op:
            batch_op.create_index(index_name, ['user_id'], unique=False)


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    if 'cameras' not in tables:
        return

    indexes = {index['name'] for index in inspector.get_indexes('cameras')}
    index_name = 'ix_cameras_user_id'
    if index_name in indexes:
        with op.batch_alter_table('cameras', schema=None) as batch_op:
            batch_op.drop_index(index_name)

    op.drop_table('cameras')
