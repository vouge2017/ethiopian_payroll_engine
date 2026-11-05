"""Bind new approval retry records to the reviewed payroll version."""

import sqlalchemy as sa
from alembic import op

revision = 'k20261104a01'
down_revision = 'j20261103a01'
branch_labels = None
depends_on = None


def upgrade():
    # Prior retry records cannot reliably reconstruct their review version.
    op.add_column('approval_idempotency', sa.Column('reviewed_version', sa.Integer(), nullable=True))


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text('LOCK TABLE approval_idempotency IN ACCESS EXCLUSIVE MODE'))
    if connection.execute(
        sa.text('SELECT 1 FROM approval_idempotency WHERE reviewed_version IS NOT NULL LIMIT 1')
    ).first():
        raise RuntimeError('Cannot downgrade while approval retry records exist; preserve their history')
    op.drop_column('approval_idempotency', 'reviewed_version')
