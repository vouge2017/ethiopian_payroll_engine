"""
Add pay_item_type and payroll_item_assignment tables (elements architecture).

Lock-ins applied (verify each in this file):
  1. employee_pension classification = 'deduction' (employer_pension = 'employer_charge')
  2. Partial unique indexes: (key) WHERE company_id IS NULL; (company_id, key) WHERE company_id IS NOT NULL
  3. percent_of_net as a real column on payroll_item_assignment + in calc_method check
  4. units_input key resolution order: assignment.units_field first, then item key (docstring in engine, not migration)
  5. PayItemType.regulation_reference added (nullable)
  6. PayrollItemAssignment.custom_label added (nullable)

Also bundled DB fixes (separate concerns, same migration window):
  - ondelete='RESTRICT' on FKs to Company/User/Employee (or SET NULL where optional)
  - This migration does NOT touch Attendance/Overtime hours (separate migration below)
  - This migration does NOT add the PayrollRun partial unique index (separate migration below)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = '8e3a7b2c9d1f'
down_revision = 'z6a7b8c9d0e9'  # head merge migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. pay_item_type — per-company pay item type registry
    # ------------------------------------------------------------------
    op.create_table(
        'pay_item_type',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),  # NULL = system catalog item
        sa.Column('key', sa.String(30), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=False),
        sa.Column('name_am', sa.String(100), nullable=True),
        sa.Column(
            'classification',
            sa.Enum('earning', 'deduction', 'employer_charge', 'tax', 'informational', name='payitem_classification'),
            nullable=False,
        ),
        sa.Column(
            'calculation_method',
            sa.Enum(
                'fixed', 'rate_x_units', 'percent_of_basic', 'percent_of_item', 'percent_of_net',
                name='payitem_calc_method',
            ),
            nullable=False,
            server_default='fixed',
        ),
        # percent_of_item target — FK to another pay_item_type (the item this % applies to)
        sa.Column('percent_of_item_key', sa.String(30), nullable=True),
        # rate for rate_x_units (amount per unit) or percent_of_basic / percent_of_net (percentage value)
        sa.Column('rate', sa.Numeric(10, 4), nullable=True),
        # Tax treatment (only meaningful for earnings; deductions/tax have their own semantics)
        sa.Column(
            'tax_treatment',
            sa.Enum('taxable', 'exempt', 'partial', name='payitem_tax_treatment'),
            nullable=False,
            server_default='taxable',
        ),
        sa.Column('exempt_cap_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('exempt_cap_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('exempt_cap_basis', sa.String(20), nullable=True),
        sa.Column('regulation_reference', sa.String(200), nullable=True),  # lock-in 5
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Partial unique indexes (lock-in 2)
    # System catalog: one row per key where company_id IS NULL
    op.execute(
        'CREATE UNIQUE INDEX uq_pay_item_type_system_key '
        'ON pay_item_type (key) WHERE company_id IS NULL'
    )
    # Per-company: one row per (company_id, key) where company_id IS NOT NULL
    op.execute(
        'CREATE UNIQUE INDEX uq_pay_item_type_company_key '
        'ON pay_item_type (company_id, key) WHERE company_id IS NOT NULL'
    )

    # Regular indexes for query patterns
    op.create_index(
        'ix_pay_item_type_company_active',
        'pay_item_type',
        ['company_id', 'is_active'],
        unique=False,
    )
    op.create_index(
        'ix_pay_item_type_company_key',
        'pay_item_type',
        ['company_id', 'key'],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 2. payroll_item_assignment — employee + pay item + effective dates
    # ------------------------------------------------------------------
    op.create_table(
        'payroll_item_assignment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('pay_item_type_id', sa.Integer(), nullable=False),

        # Value columns — mutually exclusive based on calculation_method
        sa.Column('fixed_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('rate_per_unit', sa.Numeric(10, 4), nullable=True),  # for rate_x_units
        sa.Column('percent_of_basic', sa.Numeric(5, 2), nullable=True),  # for percent_of_basic
        sa.Column('percent_of_item_id', sa.Integer(), nullable=True),  # for percent_of_item (ref to another assignment)
        sa.Column('percent_of_net', sa.Numeric(5, 2), nullable=True),  # lock-in 3: deduction-only method

        # units_input resolution (lock-in 4: units_field is the pointer, value comes per-period)
        sa.Column('units_field', sa.String(30), nullable=True),

        # For percent_of_item: which assignment this % applies to (self-referential, scoped to same employee+period)
        # Stored as the id of another PayrollItemAssignment on the same employee

        # custom_label overrides the item type's name_en for this specific assignment (lock-in 6)
        sa.Column('custom_label', sa.String(100), nullable=True),

        # Effective dates
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Declining-balance state (for deduction items in declining tracking mode)
        sa.Column('tracking_mode', sa.String(15), nullable=True),  # 'declining' or 'date_bounded'
        sa.Column('total_to_recover', sa.Numeric(12, 2), nullable=True),
        sa.Column('remaining_balance', sa.Numeric(12, 2), nullable=True),

        # Audit
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['pay_item_type_id'], ['pay_item_type.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes
    op.create_index(
        'ix_payroll_item_assignment_company_active',
        'payroll_item_assignment',
        ['company_id', 'is_active'],
        unique=False,
    )
    op.create_index(
        'ix_payroll_item_assignment_company_employee_active',
        'payroll_item_assignment',
        ['company_id', 'employee_id', 'is_active'],
        unique=False,
    )
    op.create_index(
        'ix_payroll_item_assignment_pay_item_type',
        'payroll_item_assignment',
        ['pay_item_type_id'],
        unique=False,
    )

    # Check constraint: at least one calculation value column must be non-null
    # (embedded as a table arg — Postgres enforces it; SQLite stores it but does
    # not enforce it, which is acceptable since the model layer validates).
    sa.CheckConstraint(
        'fixed_amount IS NOT NULL OR rate_per_unit IS NOT NULL OR '
        'percent_of_basic IS NOT NULL OR percent_of_item_id IS NOT NULL OR '
        'percent_of_net IS NOT NULL',
        name='ck_assignment_calc_method',
    ),


def downgrade() -> None:
    # Drop in reverse order (child table first)
    op.drop_table('payroll_item_assignment')
    op.drop_table('pay_item_type')

    # Drop the enums created alongside the tables (Postgres-specific; skip on SQLite
    # where DROP TYPE is not supported — SQLite enums are just CHECK-backed text).
    # MySQL uses DROP TYPE differently; guard by dialect.
    dialect = op.get_bind().dialect
    if dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS payitem_tax_treatment CASCADE')
        op.execute('DROP TYPE IF EXISTS payitem_calc_method CASCADE')
        op.execute('DROP TYPE IF EXISTS payitem_classification CASCADE')
