"""add referral fields to user

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op

revision = 't0u1v2w3x4y5'
down_revision = 's9t0u1v2w3x4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('referral_code', sa.String(20), unique=True, nullable=True))
        batch_op.add_column(sa.Column('referred_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('referred_by')
        batch_op.drop_column('referral_code')
