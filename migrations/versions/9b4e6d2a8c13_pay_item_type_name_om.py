"""Add pay_item_type.name_om (Afaan Oromoo label).

Schema only, nullable, no data. The company pay-item settings page edits
English, Amharic and Afaan Oromoo labels; existing rows keep NULL and fall
back to English. Downgrade drops the column (labels typed into it are lost,
nothing else is touched).
"""

import sqlalchemy as sa
from alembic import op

revision = '9b4e6d2a8c13'
down_revision = 'c8d9e0f1a2b3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pay_item_type', sa.Column('name_om', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('pay_item_type', 'name_om')
