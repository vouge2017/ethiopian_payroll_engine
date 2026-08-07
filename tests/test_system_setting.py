"""Tests for SystemSetting model and DB-backed retention purge."""
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


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_system_setting_get_default(ctx):
    """get() returns default when key doesn't exist."""
    assert SystemSetting.get('nonexistent') is None
    assert SystemSetting.get('nonexistent', 'fallback') == 'fallback'


def test_system_setting_set_and_get(ctx):
    """set() creates a new setting; get() retrieves it."""
    SystemSetting.set('test_key', 'test_value')
    assert SystemSetting.get('test_key') == 'test_value'


def test_system_setting_update(ctx):
    """set() updates existing setting."""
    SystemSetting.set('key1', 'v1')
    SystemSetting.set('key1', 'v2')
    assert SystemSetting.get('key1') == 'v2'
    # Only one row, not two
    assert SystemSetting.query.filter_by(key='key1').count() == 1


def test_system_setting_value_types(ctx):
    """set() converts values to strings."""
    SystemSetting.set('int_key', 42)
    SystemSetting.set('bool_key', True)
    assert SystemSetting.get('int_key') == '42'
    assert SystemSetting.get('bool_key') == 'True'


def test_system_setting_isolation(ctx):
    """Different keys are independent."""
    SystemSetting.set('a', '1')
    SystemSetting.set('b', '2')
    assert SystemSetting.get('a') == '1'
    assert SystemSetting.get('b') == '2'
