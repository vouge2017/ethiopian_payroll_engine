"""add_reference_to_payroll_run

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payroll_run', sa.Column('reference', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('payroll_run', 'reference')
