"""Company: record when the leave-pay basis and divisor were confirmed.

Adviser answer 2026-10-25 (Q3 PARTIAL): no universal leave-pay divisor is
established and a configurable default is not legal approval. A settlement
with leave encashment > 0 may only be finalized once the company has
explicitly confirmed its basis and divisor. Existing companies start
unconfirmed (NULL).
"""

import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8f6'
down_revision = 'f4a5b6c7d8f5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('company') as batch_op:
        batch_op.add_column(sa.Column('leave_rate_confirmed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('leave_rate_confirmed_by', sa.Integer(), nullable=True))


def downgrade():
    conn = op.get_bind()
    # Refuse to silently discard a company's confirmation; restore a backup instead.
    if conn.execute(
        sa.text('SELECT EXISTS (SELECT 1 FROM company WHERE leave_rate_confirmed_at IS NOT NULL)')
    ).scalar():
        raise RuntimeError('Cannot discard company leave-rate confirmations during downgrade.')
    with op.batch_alter_table('company') as batch_op:
        batch_op.drop_column('leave_rate_confirmed_by')
        batch_op.drop_column('leave_rate_confirmed_at')
