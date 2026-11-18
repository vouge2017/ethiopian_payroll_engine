"""Add salary edit permission and version audit hashes without rewriting history."""

import sqlalchemy as sa
from alembic import op

revision = 'k20261118a01'
down_revision = 'k20261104a01'
branch_labels = None
depends_on = None

_PROTECTED = "'salary_changed', 'employee_salary_changed', 'salary_permission_changed'"


def upgrade():
    op.add_column('user_company', sa.Column('can_edit_salary', sa.Boolean(), server_default=sa.false(), nullable=False))
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(f"""
            CREATE FUNCTION protect_salary_audit_record() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                IF OLD.hash LIKE 'v2:%' AND OLD.action IN ({_PROTECTED}) THEN
                    RAISE EXCEPTION 'Salary audit records cannot be modified or deleted';
                END IF;
                IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                RETURN NEW;
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER protect_salary_audit_record
            BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW
            EXECUTE FUNCTION protect_salary_audit_record()
        """)
    elif op.get_bind().dialect.name == 'sqlite':
        for operation in ('UPDATE', 'DELETE'):
            op.execute(f"""
                CREATE TRIGGER protect_salary_audit_{operation.lower()}
                BEFORE {operation} ON audit_log
                WHEN OLD.hash LIKE 'v2:%' AND OLD.action IN ({_PROTECTED})
                BEGIN SELECT RAISE(ABORT, 'Salary audit records cannot be modified or deleted'); END
            """)


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER protect_salary_audit_record ON audit_log')
        op.execute('DROP FUNCTION protect_salary_audit_record()')
    elif op.get_bind().dialect.name == 'sqlite':
        for operation in ('update', 'delete'):
            op.execute(f'DROP TRIGGER protect_salary_audit_{operation}')
    op.drop_column('user_company', 'can_edit_salary')
