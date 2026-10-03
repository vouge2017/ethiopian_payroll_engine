"""Add CHECK constraint on PayItemType.max_percent_of_net.

max_percent_of_net is a percentage of net pay, so values outside 0-100 are
meaningless (and >100 would silently allow a deduction larger than net). The
column is nullable: NULL means "no documented ceiling" and is exempt from the
check.

Rebuilds the table via batch_alter_table because SQLite cannot ADD CONSTRAINT
to an existing table; on Postgres this emits a real ALTER TABLE ... ADD
CONSTRAINT.

The CHECK is also enforced in the engine (percent_of_net deductions are
clamped to the ceiling), so a bad row that predates this constraint still
cannot over-deduct at calculation time.
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1f0a2b3c4d6'
down_revision = 'e1f0a2b3c4d5'
branch_labels = None
depends_on = None

CONSTRAINT = 'ck_pay_item_type_max_percent_of_net'


def upgrade() -> None:
    with op.batch_alter_table('pay_item_type', schema=None) as batch_op:
        batch_op.create_check_constraint(
            CONSTRAINT,
            'max_percent_of_net IS NULL OR (max_percent_of_net >= 0 AND max_percent_of_net <= 100)',
        )


def downgrade() -> None:
    with op.batch_alter_table('pay_item_type', schema=None) as batch_op:
        batch_op.drop_constraint(CONSTRAINT, type_='check')
