"""P0-E: Real cron endpoint tests.

Verifies:
- /internal/cron/daily rejects requests without X-Cron-Secret
- With the correct secret, the endpoint runs all tasks and returns a report
- /internal/cron/health is publicly accessible
- The endpoint is idempotent (safe to call multiple times)
"""

from datetime import UTC, datetime, timedelta

import pytest

from payroll_engine import create_app, db


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv('CRON_SECRET', 'test-cron-secret-32-bytes-pad!')
    app = create_app()
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
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
    assert r.status_code == 405, f'GET on /internal/cron/daily must be 405 Method Not Allowed, got {r.status_code}'


def test_cron_daily_rejects_wrong_secret(app):
    client = app.test_client()
    r = client.post(
        '/internal/cron/daily',
        headers={'X-Cron-Secret': 'wrong-secret'},
    )
    assert r.status_code == 401


def test_cron_daily_runs_with_correct_secret(app, monkeypatch):
    from payroll_engine import worker_health
    from payroll_engine.models import LoginAttempt

    monkeypatch.setattr(worker_health, 'beat', lambda *args, **kwargs: True)
    now = datetime.now(UTC).replace(tzinfo=None)
    db.session.add_all(
        [
            LoginAttempt(identifier='expired@example.test', success=False, created_at=now - timedelta(days=8)),
            LoginAttempt(identifier='recent@example.test', success=False, created_at=now - timedelta(days=1)),
        ]
    )
    db.session.commit()
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
    assert 'error' not in data['tasks']['retention']
    assert 'compliance' in data['tasks']
    assert 'erca_reminder' in data['tasks']
    # A new session must see the deletion, not an uncommitted DELETE.
    db.session.remove()
    assert LoginAttempt.query.filter_by(identifier='expired@example.test').count() == 0
    assert LoginAttempt.query.filter_by(identifier='recent@example.test').count() == 1


@pytest.mark.parametrize('succeeded', [True, False])
def test_cron_heartbeat_is_separate_and_reports_result(app, monkeypatch, succeeded):
    from payroll_engine import worker_health

    calls = []

    def fake_beat(worker_id='worker-0', *, key):
        calls.append((worker_id, key))
        return succeeded

    monkeypatch.setattr(worker_health, 'beat', fake_beat)
    response = app.test_client().post(
        '/internal/cron/daily', headers={'X-Cron-Secret': 'test-cron-secret-32-bytes-pad!'}
    )
    assert response.status_code == 200
    assert calls == [('daily-cron', worker_health.CRON_HEARTBEAT_KEY)]
    assert response.get_json()['tasks']['cron_heartbeat']['ok'] is succeeded
    assert response.get_json()['ok'] is succeeded
    assert response.get_json()['tasks']['worker_heartbeat'] == {
        'skipped': True,
        'reason': 'Cron does not establish worker liveness',
    }


def test_cron_retention_error_makes_overall_result_false(app, monkeypatch):
    from payroll_engine import retention, worker_health

    def fail_retention(_app):
        raise RuntimeError('synthetic retention failure')

    monkeypatch.setattr(retention, 'purge_old_login_attempts', fail_retention)
    monkeypatch.setattr(worker_health, 'beat', lambda *args, **kwargs: True)
    response = app.test_client().post(
        '/internal/cron/daily', headers={'X-Cron-Secret': 'test-cron-secret-32-bytes-pad!'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is False
    assert data['tasks']['retention']['error'] == 'synthetic retention failure'


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
