"""Add PayItemType.max_percent_of_net.

Stores the legal ceiling on a deduction item's percent_of_net so the route
layer reads the rule from the type row instead of hardcoding
`deduction_type == 'court_order' and amount > 50`.

NULL means "no documented ceiling", preserving today's behaviour for every
item except court_order (which the catalog seeds at 50).
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1f0a2b3c4d4'
down_revision = 'e1f0a2b3c4d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('pay_item_type', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('max_percent_of_net', sa.Numeric(5, 2), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('pay_item_type', schema=None) as batch_op:
        batch_op.drop_column('max_percent_of_net')
