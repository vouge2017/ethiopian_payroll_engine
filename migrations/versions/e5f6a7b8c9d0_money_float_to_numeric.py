"""Money Float to Numeric(12,2)

Revision ID: e5f6a7b8c9d0
Revises: b3c4d5e6f7a8, b4c5d6e7f8a9
Create Date: 2026-07-09

Migrates all monetary columns from Float to Numeric(12,2) to prevent
binary floating-point drift in payroll calculations.

Uses ALTER COLUMN with explicit casting to safely convert existing data.
SQLite does not support ALTER COLUMN TYPE — for SQLite, the migration
skips the type change (SQLite stores everything as TEXT/REAL anyway).
For PostgreSQL, it performs a safe CAST.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = ('b3c4d5e6f7a8', 'b4c5d6e7f8a9')
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Money columns on Employee table
    emp_money_cols = ['basic_salary', 'allowances']

    # Money columns on Payslip table
    payslip_money_cols = [
        'gross_salary', 'tax', 'employee_pension',
        'employer_pension', 'net_pay'
    ]

    if dialect == 'postgresql':
        # PostgreSQL: safe ALTER COLUMN with explicit CAST
        for col in emp_money_cols:
            op.alter_column(
                'employee', col,
                existing_type=sa.Float(),
                type_=sa.Numeric(12, 2),
                existing_nullable=False,
                postgresql_using=f'{col}::numeric(12,2)'
            )

        for col in payslip_money_cols:
            op.alter_column(
                'payslip', col,
                existing_type=sa.Float(),
                type_=sa.Numeric(12, 2),
                existing_nullable=False,
                postgresql_using=f'{col}::numeric(12,2)'
            )
    else:
        # SQLite: no ALTER COLUMN TYPE support.
        # SQLite stores NUMERIC as REAL anyway — skip silently.
        # The model change ensures new columns are created correctly.
        pass


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    emp_money_cols = ['basic_salary', 'allowances']
    payslip_money_cols = [
        'gross_salary', 'tax', 'employee_pension',
        'employer_pension', 'net_pay'
    ]

    if dialect == 'postgresql':
        for col in emp_money_cols:
            op.alter_column(
                'employee', col,
                existing_type=sa.Numeric(12, 2),
                type_=sa.Float(),
                existing_nullable=False,
            )

        for col in payslip_money_cols:
            op.alter_column(
                'payslip', col,
                existing_type=sa.Numeric(12, 2),
                type_=sa.Float(),
                existing_nullable=False,
            )
    else:
        pass
