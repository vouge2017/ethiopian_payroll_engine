"""Add PayrollItemAssignment.legacy_source (String(60), nullable, indexed).

Provenance marker for the data backfill: 'legacy_basic:<employee_id>',
'legacy_allowance:<id>' or 'legacy_deduction:<id>'.

It is a separate column rather than reusing reference_number because
reference_number carries real business data -- court case numbers, MoE batch
codes -- which must survive the backfill verbatim. Without a dedicated tag
column, making the backfill idempotent would mean destroying that data.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f0a2b3c4d9'
down_revision = 'e1f0a2b3c4d8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payroll_item_assignment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('legacy_source', sa.String(length=60), nullable=True))
        batch_op.create_index(
            'ix_payroll_item_assignment_legacy_source',
            'legacy_source',
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('payroll_item_assignment', schema=None) as batch_op:
        batch_op.drop_index('ix_payroll_item_assignment_legacy_source')
        batch_op.drop_column('legacy_source')
