"""Collection defaults and per-test database/tenant cleanup.

Database fixtures own their engines; this module makes no full-suite hang claim.
"""

import os
import secrets
from types import SimpleNamespace

import pytest

os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
# Models require a key during collection, before fixtures run. Generate an
# ephemeral test-only default while preserving explicitly configured keys.
if os.environ.get('FLASK_ENV') == 'testing':
    os.environ.setdefault('DB_ENCRYPTION_KEY', secrets.token_hex(32))


@pytest.fixture
def synthetic_calculation_rule(monkeypatch):
    """Supply an explicit test rule to pure calculator tests without an app."""
    from flask import has_app_context

    from payroll_engine.models import TaxRule
    from payroll_engine.pension import invalidate_pension_cache
    from payroll_engine.tax import invalidate_tax_cache

    brackets = [
        {'max': 2000, 'rate': '0'},
        {'max': 4000, 'rate': '0.15'},
        {'max': 7000, 'rate': '0.20'},
        {'max': 10000, 'rate': '0.25'},
        {'max': 14000, 'rate': '0.30'},
        {'max': None, 'rate': '0.35'},
    ]
    rule = SimpleNamespace(
        brackets=brackets,
        personal_relief=0,
        rules_json={'brackets': brackets, 'pension': {'employee_rate': '0.07', 'employer_rate': '0.11'}},
    )
    lookup = TaxRule.get_active_rule

    def get_rule(for_date=None, country='ET'):
        return lookup(for_date, country) if has_app_context() else rule

    monkeypatch.setattr(TaxRule, 'get_active_rule', get_rule)
    invalidate_tax_cache()
    invalidate_pension_cache()
    yield
    invalidate_tax_cache()
    invalidate_pension_cache()


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
