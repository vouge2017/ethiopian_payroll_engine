"""Add employee_deduction table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-10

Flexible deduction module for cost-sharing, court orders, penalties, loans.
Supports fixed ETB and percentage-of-net-pay amounts.
Supports declining-balance and date-bounded tracking.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'employee_deduction',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id'), nullable=False),
        sa.Column('employee_id', sa.Integer, sa.ForeignKey('employee.id'), nullable=False),

        # What
        sa.Column('deduction_type', sa.String(30), nullable=False),
        sa.Column('label', sa.String(200), nullable=False),

        # How much
        sa.Column('amount_mode', sa.String(15), nullable=False, server_default='fixed'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),

        # Balance tracking
        sa.Column('tracking_mode', sa.String(15), nullable=False, server_default='declining'),
        sa.Column('total_to_recover', sa.Numeric(12, 2), nullable=True),
        sa.Column('remaining_balance', sa.Numeric(12, 2), nullable=True),

        # Date bounds
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=True),

        # Document trail
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('document_path', sa.String(255), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('stopped_reason', sa.String(200), nullable=True),

        # Audit
        sa.Column('created_by', sa.Integer, sa.ForeignKey('user.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Indexes for common queries
    op.create_index('ix_deduction_company_id', 'employee_deduction', ['company_id'])
    op.create_index('ix_deduction_employee_id', 'employee_deduction', ['employee_id'])
    op.create_index('ix_deduction_active', 'employee_deduction', ['employee_id', 'is_active'])

    # Check constraints
    op.execute("""
        ALTER TABLE employee_deduction
        ADD CONSTRAINT ck_deduction_amount_mode
        CHECK (amount_mode IN ('fixed', 'percentage'))
    """)
    op.execute("""
        ALTER TABLE employee_deduction
        ADD CONSTRAINT ck_deduction_tracking_mode
        CHECK (tracking_mode IN ('declining', 'date_bounded'))
    """)
    op.execute("""
        ALTER TABLE employee_deduction
        ADD CONSTRAINT ck_deduction_type
        CHECK (deduction_type IN ('cost_sharing', 'court_order', 'penalty', 'loan', 'other'))
    """)


def downgrade():
    op.drop_index('ix_deduction_active', table_name='employee_deduction')
    op.drop_index('ix_deduction_employee_id', table_name='employee_deduction')
    op.drop_index('ix_deduction_company_id', table_name='employee_deduction')
    op.drop_table('employee_deduction')
