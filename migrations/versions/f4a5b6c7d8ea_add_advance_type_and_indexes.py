"""Update ck_deduction_type to include 'advance' + add missing indexes

Revision ID: f4a5b6c7d8ea
Revises: z6a7b8c9d0e9_merge_all_heads
Create Date: 2026-09-24

Adds 'advance' to the deduction_type CHECK constraint and creates
indexes on employee.name and payslip.generated_at for query performance.
"""
from alembic import op
import sqlalchemy as sa

revision = 'f4a5b6c7d8ea'
down_revision = 'e1f0a2b3c4ea'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old constraint and add new one with 'advance' included
    op.execute("ALTER TABLE employee_deduction DROP CONSTRAINT IF EXISTS ck_deduction_type")
    op.execute("""
        ALTER TABLE employee_deduction
        ADD CONSTRAINT ck_deduction_type
        CHECK (deduction_type IN ('cost_sharing', 'court_order', 'penalty', 'loan', 'advance', 'other'))
    """)

    # Missing indexes for query performance
    op.create_index('idx_employee_name', 'employee', ['name'])
    op.create_index('idx_payslip_generated_at', 'payslip', ['generated_at'])


def downgrade():
    op.drop_index('idx_payslip_generated_at', table_name='payslip')
    op.drop_index('idx_employee_name', table_name='employee')
    op.execute("ALTER TABLE employee_deduction DROP CONSTRAINT IF EXISTS ck_deduction_type")
    op.execute("""
        ALTER TABLE employee_deduction
        ADD CONSTRAINT ck_deduction_type
        CHECK (deduction_type IN ('cost_sharing', 'court_order', 'penalty', 'loan', 'other'))
    """)
