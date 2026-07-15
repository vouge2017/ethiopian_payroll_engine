"""add mfa totp fields to user

Revision ID: m2n3o4p5q6r7
Revises: k1l2m3n4o5p6
Create Date: 2026-07-15 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'm2n3o4p5q6r7'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('totp_secret', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('mfa_enabled')
        batch_op.drop_column('totp_secret')
