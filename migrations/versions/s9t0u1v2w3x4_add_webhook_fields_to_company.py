"""add webhook fields to company

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op

revision = 's9t0u1v2w3x4'
down_revision = 'r8s9t0u1v2w3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('company') as batch_op:
        batch_op.add_column(sa.Column('webhook_url', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('webhook_secret', sa.String(64), nullable=True))


def downgrade():
    with op.batch_alter_table('company') as batch_op:
        batch_op.drop_column('webhook_secret')
        batch_op.drop_column('webhook_url')
