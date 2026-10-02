"""Add company_id to attendance for tenant isolation

Revision ID: z6a7b8c9d0e8
Revises: z6a7b8c9d0e7
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'z6a7b8c9d0e8'
down_revision = 'z6a7b8c9d0e7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))

    conn = op.get_bind()
    # Correlated subquery works on both PostgreSQL and SQLite
    conn.execute(sa.text("""
        UPDATE attendance
        SET company_id = (
            SELECT employee.company_id FROM employee
            WHERE employee.id = attendance.employee_id
        )
        WHERE company_id IS NULL
    """))

    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=False)
        batch_op.create_foreign_key('fk_attendance_company_id', 'company', ['company_id'], ['id'])
        batch_op.create_index('ix_attendance_company_id', ['company_id'])


def downgrade():
    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.drop_index('ix_attendance_company_id')
        batch_op.drop_constraint('fk_attendance_company_id', 'attendance', type_='foreignkey')
        batch_op.drop_column('company_id')
