"""Add company_id to payslip for tenant isolation

Revision ID: z6a7b8c9d0e6
Revises: z6a7b8c9d0e5
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'z6a7b8c9d0e6'
down_revision = 'z6a7b8c9d0e5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE payslip
        SET company_id = payroll_run.company_id
        FROM payroll_run
        WHERE payslip.payroll_run_id = payroll_run.id
    """))

    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=False)
        batch_op.create_foreign_key('fk_payslip_company_id', 'payslip', 'company', ['company_id'], ['id'])
        batch_op.create_index('ix_payslip_company_id', 'payslip', ['company_id'])


def downgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.drop_index('ix_payslip_company_id')
        batch_op.drop_constraint('fk_payslip_company_id', 'payslip', type_='foreignkey')
        batch_op.drop_column('company_id')
