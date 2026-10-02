"""Collection defaults and per-test database/tenant cleanup.

Database fixtures own their engines; this module makes no full-suite hang claim.
"""

import os
import secrets

import pytest

os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
# Models require a key during collection, before fixtures run. Generate an
# ephemeral test-only default while preserving explicitly configured keys.
if os.environ.get('FLASK_ENV') == 'testing':
    os.environ.setdefault('DB_ENCRYPTION_KEY', secrets.token_hex(32))


@pytest.fixture(autouse=True)
def _db_session_cleanup():
    """Tear down per-test DB and tenant state.

    BOTH cleanups are required:
      * db.session.remove() returns the session's connection to the pool and
        drops the identity map. Without it, ORM objects from a previous test
        stay identity-mapped and stale connections accumulate, which surfaces
        as cross-test contamination (stale objects, leaked connections).
      * TenantQuery context is thread-local, so it must be cleared or it
        leaks into the next test.
    """
    yield
    try:
        from payroll_engine import db

        db.session.rollback()
        db.session.remove()
    except Exception:
        pass
    try:
        from payroll_engine.models import TenantQuery

        TenantQuery.clear_tenant_context()
    except Exception:
        pass
