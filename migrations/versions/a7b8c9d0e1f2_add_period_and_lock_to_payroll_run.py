"""Add period and lock to payroll_run

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-10

Changes:
- Add period column (Ethiopian calendar YYYY-MM)
- Backfill existing runs from their run_date
- Add NOT NULL constraint
- Add partial unique index: one active run per company+period
- Add locked_at and locked_by columns for terminal lock state
"""
import sqlalchemy as sa
from alembic import op

revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    # --- FIX 1: Period identification ---
    # Step 1: Add period column (nullable for backfill)
    op.add_column('payroll_run', sa.Column('period', sa.String(7), nullable=True))

    # Step 2: Backfill existing runs using Ethiopian calendar
    # We need to do this in Python because the conversion is complex
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, run_date FROM payroll_run WHERE period IS NULL")).fetchall()
    for row in rows:
        run_date = row[1]
        if run_date:
            if isinstance(run_date, str):
                from datetime import datetime as dt
                run_date = dt.strptime(run_date[:10], '%Y-%m-%d').date()
            eth_year, eth_month, _ = gregorian_to_ethiopian(run_date)
            period = f'{eth_year}-{eth_month:02d}'
        else:
            period = '0000-00'
        conn.execute(
            sa.text("UPDATE payroll_run SET period = :period WHERE id = :id"),
            {'period': period, 'id': row[0]}
        )

    # Step 3: Make NOT NULL
    op.alter_column('payroll_run', 'period', nullable=False)

    # Step 4: Partial unique index — one active run per company+period
    # Using raw SQL because Alembic doesn't support partial indexes directly
    op.execute("""
        CREATE UNIQUE INDEX uq_company_period_active
        ON payroll_run (company_id, period)
        WHERE status NOT IN ('failed', 'rejected')
    """)

    # --- FIX 2: Locked terminal state ---
    op.add_column('payroll_run', sa.Column('locked_at', sa.DateTime, nullable=True))
    op.add_column('payroll_run', sa.Column('locked_by', sa.Integer, nullable=True))
    op.create_foreign_key('fk_payroll_run_locked_by', 'payroll_run', 'user', ['locked_by'], ['id'])


def downgrade():
    op.drop_constraint('fk_payroll_run_locked_by', 'payroll_run', type_='foreignkey')
    op.drop_column('payroll_run', 'locked_by')
    op.drop_column('payroll_run', 'locked_at')
    op.execute("DROP INDEX IF EXISTS uq_company_period_active")
    op.drop_column('payroll_run', 'period')
