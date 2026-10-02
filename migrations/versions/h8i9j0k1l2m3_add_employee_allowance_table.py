"""add_employee_allowance_table

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-07-13 15:45:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'h8i9j0k1l2m3'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('employee_allowance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('allowance_type', sa.String(30), nullable=False),
        sa.Column('custom_type_name', sa.String(100), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('calculation_basis', sa.String(20), nullable=False, server_default='fixed'),
        sa.Column('percentage_of', sa.String(20), nullable=True),
        sa.Column('tax_treatment', sa.String(20), nullable=False, server_default='taxable'),
        sa.Column('exempt_cap_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('exempt_cap_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('exempt_cap_basis', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('regulation_reference', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("tax_treatment IN ('taxable', 'exempt', 'partial')", name='ck_allowance_tax_treatment'),
        sa.CheckConstraint("calculation_basis IN ('fixed', 'percentage')", name='ck_allowance_calc_basis'),
    )
    op.create_index('ix_employee_allowance_company_id', 'employee_allowance', ['company_id'])
    op.create_index('ix_employee_allowance_employee_id', 'employee_allowance', ['employee_id'])


def downgrade():
    op.drop_index('ix_employee_allowance_employee_id', table_name='employee_allowance')
    op.drop_index('ix_employee_allowance_company_id', table_name='employee_allowance')
    op.drop_table('employee_allowance')
