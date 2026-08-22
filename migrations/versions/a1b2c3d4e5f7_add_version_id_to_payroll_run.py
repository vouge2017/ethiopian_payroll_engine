"""add version_id column to payroll_run for optimistic locking

Revision ID: a1b2c3d4e5f7
Revises: 3517083353fc
Create Date: 2026-08-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f7'
down_revision = '3517083353fc'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('payroll_run')]

    if 'version_id' not in columns:
        op.add_column('payroll_run', sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    op.drop_column('payroll_run', 'version_id')
