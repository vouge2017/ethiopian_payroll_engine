"""P0-E: Real cron endpoint tests.

Verifies:
- /internal/cron/daily rejects requests without X-Cron-Secret
- With the correct secret, the endpoint runs all tasks and returns a report
- /internal/cron/health is publicly accessible
- The endpoint is idempotent (safe to call multiple times)
"""
import os

import pytest

from payroll_engine import create_app, db


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('CRON_SECRET', 'test-cron-secret-32-bytes-pad!')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_cron_health_endpoint_public(app):
    client = app.test_client()
    r = client.get('/internal/cron/health')
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert data['secret_configured'] is True


def test_cron_daily_rejects_without_secret(app):
    client = app.test_client()
    r = client.post('/internal/cron/daily')
    assert r.status_code == 401
    assert r.get_json()['error'] == 'unauthorized'


def test_cron_daily_rejects_get_method(app):
    """P0-E senior: GET on a state-mutating endpoint must be 405, not 401.
    Otherwise cache layers and link prefetchers could trigger retention
    purges by following a URL.
    """
    client = app.test_client()
    r = client.get('/internal/cron/daily', headers={'X-Cron-Secret': 'test-cron-secret-32-bytes-pad!'})
    assert r.status_code == 405, (
        f'GET on /internal/cron/daily must be 405 Method Not Allowed, got {r.status_code}'
    )


def test_cron_daily_rejects_wrong_secret(app):
    client = app.test_client()
    r = client.post(
        '/internal/cron/daily',
        headers={'X-Cron-Secret': 'wrong-secret'},
    )
    assert r.status_code == 401


def test_cron_daily_runs_with_correct_secret(app):
    client = app.test_client()
    r = client.post(
        '/internal/cron/daily',
        headers={'X-Cron-Secret': 'test-cron-secret-32-bytes-pad!'},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data['ok'] is True
    assert 'started_at' in data
    assert 'finished_at' in data
    assert 'tasks' in data
    # Retention task is always present
    assert 'retention' in data['tasks']
    assert 'compliance' in data['tasks']
    assert 'erca_reminder' in data['tasks']


def test_cron_daily_idempotent(app):
    """Calling twice in a row should not raise and should return ok."""
    client = app.test_client()
    headers = {'X-Cron-Secret': 'test-cron-secret-32-bytes-pad!'}
    r1 = client.post('/internal/cron/daily', headers=headers)
    r2 = client.post('/internal/cron/daily', headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_cron_daily_refused_when_no_secret_configured(monkeypatch):
    """If CRON_SECRET env var is not set, the endpoint must refuse ALL calls."""
    monkeypatch.delenv('CRON_SECRET', raising=False)
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        client = app.test_client()
        r = client.post(
            '/internal/cron/daily',
            headers={'X-Cron-Secret': 'anything'},
        )
        assert r.status_code == 401
        db.session.remove()
        db.drop_all()


def test_cron_health_reflects_secret_status(monkeypatch):
    """When CRON_SECRET is not set, /health reports secret_configured=False."""
    monkeypatch.delenv('CRON_SECRET', raising=False)
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        client = app.test_client()
        r = client.get('/internal/cron/health')
        assert r.status_code == 200
        data = r.get_json()
        assert data['secret_configured'] is False