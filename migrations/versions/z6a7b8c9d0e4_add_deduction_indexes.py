"""Add performance indexes on employee_deduction table

Revision ID: z6a7b8c9d0e4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-22 00:00:00.000000
"""
from alembic import op

revision = 'z6a7b8c9d0e4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE INDEX IF NOT EXISTS idx_deduction_company_id ON employee_deduction(company_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_deduction_employee_id ON employee_deduction(employee_id)')


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_deduction_employee_id')
    op.execute('DROP INDEX IF EXISTS idx_deduction_company_id')
