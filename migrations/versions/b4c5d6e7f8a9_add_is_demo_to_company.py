"""Add is_demo flag to Company

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op

revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_demo', sa.Boolean, nullable=False, server_default=sa.text('false')))


def downgrade():
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.drop_column('is_demo')
