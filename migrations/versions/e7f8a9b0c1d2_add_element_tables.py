"""
Element Database Model — Jurisdiction-Agnostic Payroll Schema

This migration creates the Element and EmployeeElement tables
to support configurable, multi-country payroll calculations.
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = None  # Set to latest existing migration
branch_labels = None
depends_on = None


def upgrade():
    # ─── Element Table ──────────────────────────────────────────────────────
    # Stores the definition of each payroll component (earning, deduction, etc.)
    op.create_table(
        'element',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('country', sa.String(2), nullable=False, index=True),  # 'ET', 'RW', 'KE'
        sa.Column('classification', sa.String(30), nullable=False),  # earning, pre_tax_deduction, etc.
        sa.Column('calc_type', sa.String(30), nullable=False),  # fixed_amount, percent_of_base, etc.
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rate', sa.Numeric(10, 4), nullable=True),  # For percent_of_base
        sa.Column('base_element', sa.String(100), nullable=True),  # Name of element this is based on
        sa.Column('amount', sa.Numeric(14, 2), nullable=True),  # For fixed_amount
        sa.Column('bracket_table', sa.JSON(), nullable=True),  # For bracket_table
        sa.Column('personal_relief', sa.Numeric(14, 2), nullable=True),  # For tax calculations
        sa.Column('is_taxable', sa.Boolean(), default=True),
        sa.Column('is_pension_base', sa.Boolean(), default=False),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('effective_from', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('effective_to', sa.Date(), nullable=True),  # NULL = still active
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    op.create_index('ix_element_country_active', 'element', ['country', 'is_active'])
    op.create_index('ix_element_effective', 'element', ['effective_from', 'effective_to'])

    # ─── EmployeeElement Table ──────────────────────────────────────────────
    # Links employees to their specific element values
    op.create_table(
        'employee_element',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('element_id', sa.Integer(), sa.ForeignKey('element.id'), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=True),  # Override amount for this employee
        sa.Column('rate', sa.Numeric(10, 4), nullable=True),  # Override rate for this employee
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('effective_from', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    )

    op.create_index('ix_emp_element_employee', 'employee_element', ['employee_id', 'is_active'])
    op.create_index('ix_emp_element_element', 'employee_element', ['element_id'])

    # ─── Seed Ethiopia Reference Data ───────────────────────────────────────
    from decimal import Decimal
    from sqlalchemy import table, column, String, Numeric, Boolean, Integer, Text, Date
    from sqlalchemy.sql import select

    element_table = table(
        'element',
        column('id', Integer),
        column('name', String),
        column('country', String),
        column('classification', String),
        column('calc_type', String),
        column('description', Text),
        column('rate', Numeric),
        column('base_element', String),
        column('amount', Numeric),
        column('bracket_table', sa.JSON),
        column('personal_relief', Numeric),
        column('is_taxable', Boolean),
        column('is_pension_base', Boolean),
        column('display_order', Integer),
        column('is_active', Boolean),
        column('effective_from', Date),
    )

    # Ethiopia basic salary
    op.execute(
        element_table().insert().values(
            name='basic_salary',
            country='ET',
            classification='earning',
            calc_type='fixed_amount',
            description='Monthly basic salary',
            is_taxable=True,
            is_pension_base=True,
            display_order=10,
            is_active=True,
            effective_from='2025-07-01',
        )
    )

    # Ethiopia allowance
    op.execute(
        element_table().insert().values(
            name='allowance',
            country='ET',
            classification='earning',
            calc_type='fixed_amount',
            description='Monthly allowances',
            is_taxable=True,
            is_pension_base=False,
            display_order=20,
            is_active=True,
            effective_from='2025-07-01',
        )
    )

    # Ethiopia employee pension (7%)
    op.execute(
        element_table().insert().values(
            name='employee_pension',
            country='ET',
            classification='pre_tax_deduction',
            calc_type='percent_of_base',
            description='Employee pension contribution (7% of basic salary)',
            rate=Decimal('0.07'),
            base_element='basic_salary',
            is_taxable=False,
            is_pension_base=False,
            display_order=40,
            is_active=True,
            effective_from='2025-07-01',
        )
    )

    # Ethiopia income tax (bracket table)
    op.execute(
        element_table().insert().values(
            name='income_tax',
            country='ET',
            classification='pre_tax_deduction',
            calc_type='bracket_table',
            description='Income tax (Proclamation 1395/2025)',
            bracket_table=[
                {"lower": "0", "upper": "2000", "rate": "0.00"},
                {"lower": "2000", "upper": "4000", "rate": "0.15"},
                {"lower": "4000", "upper": "7000", "rate": "0.20"},
                {"lower": "7000", "upper": "10000", "rate": "0.25"},
                {"lower": "10000", "upper": "14000", "rate": "0.30"},
                {"lower": "14000", "upper": None, "rate": "0.35"},
            ],
            personal_relief=Decimal('150'),
            is_taxable=False,
            is_pension_base=False,
            display_order=50,
            is_active=True,
            effective_from='2025-07-01',
        )
    )

    # Ethiopia employer pension (11%)
    op.execute(
        element_table().insert().values(
            name='employer_pension',
            country='ET',
            classification='employer_liability',
            calc_type='percent_of_base',
            description='Employer pension contribution (11% of basic salary)',
            rate=Decimal('0.11'),
            base_element='basic_salary',
            is_taxable=False,
            is_pension_base=False,
            display_order=60,
            is_active=True,
            effective_from='2025-07-01',
        )
    )


def downgrade():
    op.drop_table('employee_element')
    op.drop_table('element')
