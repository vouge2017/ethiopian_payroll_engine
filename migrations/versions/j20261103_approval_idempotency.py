"""Store approval retry identity in the approval transaction."""

import sqlalchemy as sa
from alembic import op

revision = 'j20261103a01'
down_revision = 'h1334c2024a1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'approval_idempotency',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('payroll_run_id', sa.Integer(), sa.ForeignKey('payroll_run.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key_digest', sa.String(64), nullable=False),
        sa.Column('payload_digest', sa.String(64), nullable=False),
        sa.UniqueConstraint('company_id', 'key_digest', name='uq_approval_idempotency_company_key'),
    )


def downgrade():
    connection = op.get_bind()
    # Block concurrent approvals until the history check and drop complete.
    if connection.dialect.name == 'postgresql':
        connection.execute(sa.text('LOCK TABLE approval_idempotency IN ACCESS EXCLUSIVE MODE'))
    if connection.execute(sa.text('SELECT 1 FROM approval_idempotency LIMIT 1')).first():
        raise RuntimeError('Cannot downgrade while approval retry records exist; preserve their history')
    op.drop_table('approval_idempotency')
