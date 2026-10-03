"""Partial unique index on PayrollRun(company_id, period) for non-failed/rejected runs.

CREATE UNIQUE INDEX ON payroll_run (company_id, period)
  WHERE status NOT IN ('failed', 'rejected')

This prevents duplicate payroll runs for the same company+period that are in
a terminal state (completed, locked, processing, etc.). Failed and rejected
runs are excluded because they may be re-run with the same period.

BEFORE creating the index, the migration checks for existing duplicates and
aborts loudly if any are found (the old code didn't enforce this constraint).

PG note: PG and SQLite BOTH support partial indexes (SQLite since 3.8.0), so
the same DDL is emitted on both via postgresql_where + sqlite_where. Alembic
needs both dialect kwargs or the WHERE clause is silently dropped -- which
would produce an over-constraining FULL unique index that also blocks
legitimate re-runs of a failed/rejected period.

CI note: migration-tests.yml must run this against PG to confirm the partial
predicate is emitted and enforced.
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1f0a2b3c4d2'
down_revision = 'e1f0a2b3c4d1'
branch_labels = None
depends_on = None

# Excludes failed/rejected runs: those may legitimately be re-run for the same
# company+period, so they must not be constrained.
PREDICATE = "status NOT IN ('failed', 'rejected')"


def _check_duplicates() -> list:
    """Query for duplicate (company_id, period) among non-failed/rejected runs.

    Returns a list of (company_id, period, count) tuples for any duplicates found.
    """
    conn = op.get_bind()
    sql = sa.text(
        f"""
        SELECT company_id, period, COUNT(*) AS cnt
        FROM payroll_run
        WHERE {PREDICATE}
        GROUP BY company_id, period
        HAVING COUNT(*) > 1
        """
    )
    return [(row[0], row[1], row[2]) for row in conn.execute(sql)]


def upgrade() -> None:
    # Step 1: Check for existing duplicates BEFORE creating the index.
    # If duplicates exist, the index creation will fail — we report them
    # clearly so the developer can resolve them manually.
    duplicates = _check_duplicates()
    if duplicates:
        raise RuntimeError(
            f"Cannot create partial unique index: {len(duplicates)} duplicate "
            f"(company_id, period) pairs found among non-failed/rejected PayrollRun rows. "
            f"Duplicates: {duplicates}. Resolve these manually before re-running migration."
        )

    # Step 2: Create the partial unique index. Both dialect kwargs are required:
    # postgresql_where alone leaves SQLite with a FULL unique index that would
    # wrongly forbid re-running a failed period.
    op.create_index(
        'ix_payrollrun_company_period_unique',
        'payroll_run',
        ['company_id', 'period'],
        unique=True,
        postgresql_where=sa.text(PREDICATE),
        sqlite_where=sa.text(PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_payrollrun_company_period_unique',
        table_name='payroll_run',
    )
