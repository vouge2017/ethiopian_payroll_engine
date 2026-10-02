"""Add progressive profiling fields to User

Adds:
- first_name VARCHAR(50)
- middle_name VARCHAR(50)
- last_name VARCHAR(50)
- must_complete_profile BOOLEAN NOT NULL DEFAULT FALSE

These columns back the new 2-step registration flow (commit f18b86a):
Step 1 collects phone + password; step 2 collects name + company.
must_complete_profile=True on register, False once /auth/setup-profile
is completed.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9b8c7d6e5f4'
down_revision = ('z6a7b8c9d0e9', 'e9a0b1c2d3e4', 'p0f1a2b3c4d5')  # merge all 3 heads
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column('first_name', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'user',
        sa.Column('middle_name', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'user',
        sa.Column('last_name', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'user',
        sa.Column(
            'must_complete_profile',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        )
    )


def downgrade():
    op.drop_column('user', 'must_complete_profile')
    op.drop_column('user', 'last_name')
    op.drop_column('user', 'middle_name')
    op.drop_column('user', 'first_name')
