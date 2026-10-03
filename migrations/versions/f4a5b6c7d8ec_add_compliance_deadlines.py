"""Add compliance_deadlines column to Company.

Revision ID: f4a5b6c7d8ec
Revises: f4a5b6c7d8eb
Create Date: 2026-09-27
"""
from migrations.shared_compliance import add_compliance_column, drop_compliance_column_unless_applied

revision = 'f4a5b6c7d8ec'
down_revision = 'f4a5b6c7d8eb'
branch_labels = None
depends_on = None


def upgrade():
    add_compliance_column()


def downgrade():
    drop_compliance_column_unless_applied('zz1a2b3c4d5e')
