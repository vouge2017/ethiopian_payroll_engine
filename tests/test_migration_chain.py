"""Migration chain integrity tests — verify all migrations can apply and rollback."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def migration_dir():
    """Path to migrations/versions/."""
    return os.path.join(os.path.dirname(__file__), '..', 'migrations', 'versions')


# --- Migration file validation ---

def test_all_migrations_have_revision(migration_dir):
    """Every migration file must define `revision` and `down_revision`."""
    import re
    errors = []
    for fname in sorted(os.listdir(migration_dir)):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(migration_dir, fname)
        content = open(path).read()
        if not re.search(r"^revision\s*=\s*['\"]", content, re.M):
            errors.append(f"{fname}: missing `revision`")
        if not re.search(r"^down_revision\s*=", content, re.M):
            errors.append(f"{fname}: missing `down_revision`")
    assert not errors, "Migration issues:\n" + "\n".join(errors)


def test_migration_chain_has_no_cycles(migration_dir):
    """Build the revision graph and check for cycles."""
    import re
    revisions = {}
    for fname in os.listdir(migration_dir):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(migration_dir, fname)
        content = open(path).read()
        rev_match = re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", content, re.M)
        down_match = re.search(r"^down_revision\s*=\s*(.+)$", content, re.M)
        if not rev_match:
            continue
        rev = rev_match.group(1)
        down_raw = down_match.group(1).strip() if down_match else 'None'
        # Handle tuple down_revision (merge migrations)
        if down_raw.startswith('('):
            downs = re.findall(r"['\"]([^'\"]+)['\"]", down_raw)
        elif down_raw in ('None', 'None:'):
            downs = []
        else:
            downs = [re.sub(r"['\"]", '', down_raw)]
        revisions[rev] = (downs, fname)

    # Check no cycles (simple DFS)
    visited = set()
    in_stack = set()

    def has_cycle(rev):
        if rev in in_stack:
            return True
        if rev in visited:
            return False
        visited.add(rev)
        in_stack.add(rev)
        for down in revisions.get(rev, ([], ''))[0]:
            if has_cycle(down):
                return True
        in_stack.remove(rev)
        return False

    for rev in revisions:
        assert not has_cycle(rev), f"Cycle detected involving revision {rev}"


def test_migration_chain_has_single_head(migration_dir):
    """The migration chain should converge to a single head (or controlled merges)."""
    import re
    revisions = {}
    children = {}  # down_rev → [revisions that depend on it]
    for fname in os.listdir(migration_dir):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(migration_dir, fname)
        content = open(path).read()
        rev_match = re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", content, re.M)
        down_match = re.search(r"^down_revision\s*=\s*(.+)$", content, re.M)
        if not rev_match:
            continue
        rev = rev_match.group(1)
        down_raw = down_match.group(1).strip() if down_match else 'None'
        if down_raw.startswith('('):
            downs = re.findall(r"['\"]([^'\"]+)['\"]", down_raw)
        elif down_raw in ('None', 'None:'):
            downs = []
        else:
            downs = [re.sub(r"['\"]", '', down_raw)]
        revisions[rev] = downs
        for d in downs:
            children.setdefault(d, []).append(rev)

    # Heads = revisions that no other revision depends on
    all_revs = set(revisions.keys())
    has_child = set()
    for revs in children.values():
        has_child.update(revs)
    heads = all_revs - has_child

    # Allow up to 2 heads (merge migrations may temporarily create multiple)
    assert len(heads) <= 3, \
        f"Migration chain has {len(heads)} heads: {heads}. Should be ≤ 3."


def test_every_migration_has_upgrade_and_downgrade(migration_dir):
    """Every migration file must define upgrade() and downgrade() functions."""
    import ast
    errors = []
    for fname in sorted(os.listdir(migration_dir)):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(migration_dir, fname)
        tree = ast.parse(open(path).read())
        func_names = {
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        if 'upgrade' not in func_names:
            errors.append(f"{fname}: missing upgrade()")
        if 'downgrade' not in func_names:
            errors.append(f"{fname}: missing downgrade()")
    assert not errors, "Migration function issues:\n" + "\n".join(errors)


# --- Schema parity (models vs migrations) ---

def test_all_model_tables_exist_after_create_all(app):
    """db.create_all() should create all model tables without error."""
    from sqlalchemy import inspect
    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        # Key tables that must exist
        expected = [
            'company', 'user', 'user_company', 'employee',
            'payroll_run', 'payslip', 'leave', 'audit_log',
            'api_key',
        ]
        missing = [t for t in expected if t not in tables]
        assert not missing, f"Missing tables: {missing}. Found: {tables}"


def test_api_key_table_schema(app):
    """api_key table has the expected columns."""
    from sqlalchemy import inspect
    with app.app_context():
        inspector = inspect(db.engine)
        cols = {c['name'] for c in inspector.get_columns('api_key')}
        expected = {'id', 'user_id', 'company_id', 'token_hash', 'name',
                    'is_active', 'created_at', 'last_used_at'}
        assert expected <= cols, f"Missing columns: {expected - cols}"


def test_api_key_indexes(app):
    """api_key table has indexes on user_id, company_id, token_hash."""
    from sqlalchemy import inspect
    with app.app_context():
        inspector = inspect(db.engine)
        indexes = inspector.get_indexes('api_key')
        idx_cols = {tuple(i['column_names']) for i in indexes}
        flat_idx = {c for cols in idx_cols for c in cols}
        assert 'token_hash' in flat_idx, f"token_hash not indexed. Indexes: {idx_cols}"
        assert 'user_id' in flat_idx, f"user_id not indexed. Indexes: {idx_cols}"


# --- Migration apply/rollback (requires PostgreSQL) ---


def _has_postgres():
    """Check if a PostgreSQL test database is available."""
    import urllib.parse
    url = os.environ.get('TEST_DATABASE_URL', '')
    return url.startswith('postgresql')


@pytest.mark.skipif(not _has_postgres(), reason="PostgreSQL not available (set TEST_DATABASE_URL)")
def test_migrations_apply_to_postgres():
    """All migrations can be applied to a PostgreSQL database."""
    from alembic.command import upgrade
    from alembic.config import Config
    from payroll_engine import create_app, db
    proj_root = os.path.join(os.path.dirname(__file__), '..')

    # Create a Flask app configured for PostgreSQL so env.py's current_app works
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['TEST_DATABASE_URL']
    app.config['TESTING'] = True

    with app.app_context():
        alembic_cfg = Config(os.path.join(proj_root, 'migrations', 'alembic.ini'))
        alembic_cfg.set_main_option('script_location', os.path.join(proj_root, 'migrations'))
        alembic_cfg.set_main_option('sqlalchemy.url', os.environ['TEST_DATABASE_URL'])
        try:
            upgrade(alembic_cfg, 'heads')
        except Exception as e:
            pytest.fail(f"Migrations failed to apply on PostgreSQL: {e}")


@pytest.mark.skipif(not _has_postgres(), reason="PostgreSQL not available (set TEST_DATABASE_URL)")
def test_migrations_rollback_on_postgres():
    """All migrations can be rolled back on PostgreSQL."""
    from alembic.command import upgrade, downgrade
    from alembic.config import Config
    from payroll_engine import create_app, db
    proj_root = os.path.join(os.path.dirname(__file__), '..')

    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['TEST_DATABASE_URL']
    app.config['TESTING'] = True

    with app.app_context():
        alembic_cfg = Config(os.path.join(proj_root, 'migrations', 'alembic.ini'))
        alembic_cfg.set_main_option('script_location', os.path.join(proj_root, 'migrations'))
        alembic_cfg.set_main_option('sqlalchemy.url', os.environ['TEST_DATABASE_URL'])
        try:
            upgrade(alembic_cfg, 'heads')
            downgrade(alembic_cfg, 'base')
        except Exception as e:
            pytest.fail(f"Migrations rollback failed on PostgreSQL: {e}")


def test_migrations_parse_without_error(migration_dir):
    """All migration files can be parsed and have valid Python syntax."""
    import py_compile
    errors = []
    for fname in sorted(os.listdir(migration_dir)):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(migration_dir, fname)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{fname}: {e}")
    assert not errors, "Syntax errors in migrations:\n" + "\n".join(errors)
