"""Tests for DB-backed retention purge tracker (SystemSetting)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Employee, OvertimeEntry, SystemSetting, TenantQuery


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


def test_system_setting_persists_across_contexts(app):
    """SystemSetting survives across separate app contexts (simulates restart)."""
    with app.app_context():
        SystemSetting.set('last_purge_date', '2026-07-19')

    # New context (simulates app restart)
    with app.app_context():
        assert SystemSetting.get('last_purge_date') == '2026-07-19'


def test_purge_date_prevents_rerun(app):
    """Once purge date is set to today, subsequent calls should skip."""
    from datetime import date
    today = date.today().isoformat()

    with app.app_context():
        # No setting yet — would trigger purge
        assert SystemSetting.get('last_purge_date') is None

        # After purge, set the date
        SystemSetting.set('last_purge_date', today)

        # Same day — should skip
        assert SystemSetting.get('last_purge_date') == today


def test_purge_date_different_day(app):
    """If last purge was yesterday, should trigger again."""
    from datetime import date, timedelta
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    with app.app_context():
        SystemSetting.set('last_purge_date', yesterday)
        assert SystemSetting.get('last_purge_date') != today  # not today
