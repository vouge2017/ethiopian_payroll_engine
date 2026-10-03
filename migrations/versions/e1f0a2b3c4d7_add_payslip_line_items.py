"""Add Payslip.line_items (JSON, nullable).

The payslip PDF is generated lazily, long after a run is approved. Under the
elements architecture the earnings/deduction breakdown comes from the engine's
line_items rather than being hardcoded, but the engine runs once at approval
time. Persisting the snapshot on the payslip lets the PDF render exactly what
was paid instead of recomputing (which would silently diverge if an assignment
changed after approval).

JSON rather than relational: line_items is a read-only audit snapshot that is
never queried or joined on.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f0a2b3c4d7'
down_revision = 'e1f0a2b3c4d6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.add_column(sa.Column('line_items', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.drop_column('line_items')
