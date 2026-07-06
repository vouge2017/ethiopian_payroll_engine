"""add validation and payroll lifecycle

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add lifecycle fields to payroll_run
    op.add_column('payroll_run', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.add_column('payroll_run', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('payroll_run', sa.Column('approval_ip', sa.String(length=45), nullable=True))
    op.create_foreign_key('fk_payroll_run_approved_by', 'payroll_run', 'user', ['approved_by'], ['id'])

    # Create validation_rule table
    op.create_table('validation_rule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rule_code', sa.String(length=50), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.Column('config_json', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rule_code')
    )

    # Create payroll_validation_result table
    op.create_table('payroll_validation_result',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('payroll_run_id', sa.Integer(), nullable=False),
    sa.Column('rule_code', sa.String(length=50), nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('employee_id', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('details_json', sa.JSON(), nullable=True),
    sa.Column('overridden', sa.Boolean(), nullable=True),
    sa.Column('override_reason', sa.Text(), nullable=True),
    sa.Column('overridden_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['employee_id'], ['employee.id'], ),
    sa.ForeignKeyConstraint(['overridden_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['payroll_run_id'], ['payroll_run.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('payroll_validation_result')
    op.drop_table('validation_rule')
    op.drop_constraint('fk_payroll_run_approved_by', 'payroll_run', type_='foreignkey')
    op.drop_column('payroll_run', 'approval_ip')
    op.drop_column('payroll_run', 'approved_at')
    op.drop_column('payroll_run', 'approved_by')
