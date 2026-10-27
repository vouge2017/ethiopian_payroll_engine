"""Add pay_item_type.default_amount (catalog PR 5, employee assignments).

Schema only, nullable, no data. The company's default monthly amount for a
fixed-amount earning or deduction. It pre-fills new employee assignments,
and the employee page marks an assignment whose own amount differs from it
as a per-employee override. **No calculation reads it**: payroll keeps
using the amount stored on each assignment, so no amount changes.

Plain ADD / DROP COLUMN (no batch table rebuild), like 9b4e6d2a8c13 and
d1e2f3a4b5c6, so the partial unique indexes and PostgreSQL triggers on
pay_item_type are never recreated. Downgrade drops the column (default
amounts typed into it are lost; assignments keep their own amounts).
"""

import sqlalchemy as sa
from alembic import op

revision = 'a4b5c6d7e8f9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pay_item_type', sa.Column('default_amount', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade():
    op.drop_column('pay_item_type', 'default_amount')
