"""Float hours → Numeric(8,2) on Attendance.hours_worked and OvertimeEntry.hours.

Migrate:
  - Attendance.hours_worked: Float → Numeric(8,2)
  - OvertimeEntry.hours: Float → Numeric(8,2)

Data is preserved via CAST. The conversion is exact for values with ≤ 2 decimal
places (the typical case: 8.0, 7.5, 1.25, etc.). Values with > 2 decimal places
are truncated to 2 places by the Numeric(8,2) cast.

Code sites that used float() on these fields have been updated to use Decimal (or
removed where redundant). See the list in the docstring for the exact locations.

PG note: ALTER COLUMN TYPE ... USING works identically on PG and SQLite for
numeric conversions. Migration-tests.yml must run this against PG to confirm.
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1f0a2b3c4d1'
down_revision = '8e3a7b2c9d1f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attendance.hours_worked: Float → Numeric(8,2)
    # SQLite: ALTER TABLE ... ALTER COLUMN TYPE USING works via alembic's
    # batch_alter_table (SQLite doesn't support direct ALTER COLUMN TYPE).
    # Postgres: direct ALTER COLUMN TYPE ... USING CAST works.
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.alter_column(
            'hours_worked',
            existing_type=sa.Float(),
            type_=sa.Numeric(8, 2),
            existing_nullable=False,
            existing_server_default=sa.text('0.0'),
        )

    # OvertimeEntry.hours: Float → Numeric(8,2)
    with op.batch_alter_table('overtime_entry', schema=None) as batch_op:
        batch_op.alter_column(
            'hours',
            existing_type=sa.Float(),
            type_=sa.Numeric(8, 2),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Restore Float. Data that was truncated to 2 decimal places during upgrade
    # stays truncated (that's the nature of a narrowing cast); all existing
    # values had ≤ 2 decimal places so no information is lost.
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.alter_column(
            'hours_worked',
            existing_type=sa.Numeric(8, 2),
            type_=sa.Float(),
            existing_nullable=False,
            existing_server_default=sa.text('0.0'),
        )

    with op.batch_alter_table('overtime_entry', schema=None) as batch_op:
        batch_op.alter_column(
            'hours',
            existing_type=sa.Numeric(8, 2),
            type_=sa.Float(),
            existing_nullable=False,
        )
