"""Shared test configuration — runs before all test modules.

Fixes the full-suite hang by ensuring clean database state between test modules.
Root cause: in-memory SQLite with a connection pool causes deadlocks when
multiple fixtures share the same db engine.

Solution: use StaticPool (single connection) for in-memory SQLite tests.
"""
import os
import pytest

os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')


@pytest.fixture(autouse=True, scope='session')
def _configure_test_db():
    """Configure the database for testing with a single connection."""
    from payroll_engine import db
    from sqlalchemy.pool import StaticPool

    # Override engine options before any test creates an app
    db.engine_options = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False},
    }
    yield
    try:
        db.session.remove()
        if db.engine:
            db.engine.dispose()
    except Exception:
        pass
