"""add compliance_deadlines to company table

Revision ID: zz1a2b3c4d5e
Revises: a1b2c3d4e5f7
Create Date: 2026-09-07 00:00:00.000000
"""
from migrations.shared_compliance import add_compliance_column, drop_compliance_column_unless_applied

revision = 'zz1a2b3c4d5e'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    add_compliance_column()


def downgrade():
    drop_compliance_column_unless_applied('f4a5b6c7d8ec')
