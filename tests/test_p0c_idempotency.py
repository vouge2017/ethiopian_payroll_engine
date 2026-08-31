"""P0-C: Idempotency middleware tests.

Verifies:
- Replay with same Idempotency-Key returns cached response (no re-execute)
- Without Idempotency-Key the view still executes (with warning)
- Different keys are independent
- Cached response body and status are preserved
- TTL expiry allows re-execution
"""
import time
from unittest.mock import patch

import pytest

from payroll_engine import create_app, db
from payroll_engine.idempotency import _LOCAL_CACHE, _cache_key, _get_cached, _set_cached, idempotent
from payroll_engine.models import Company, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def clear_cache():
    _LOCAL_CACHE.clear()
    yield
    _LOCAL_CACHE.clear()


def test_replay_returns_cached_response(app):
    """Same Idempotency-Key twice -> cached response, handler not called twice."""
    call_count = {'n': 0}

    @app.route('/_test_idem', methods=['POST'])
    @idempotent
    def view():
        call_count['n'] += 1
        return f'count={call_count["n"]}', 200

    client = app.test_client()
    headers = {'Idempotency-Key': 'abc-123'}

    r1 = client.post('/_test_idem', headers=headers)
    r2 = client.post('/_test_idem', headers=headers)

    assert r1.status_code == 200
    assert r1.get_data(as_text=True) == 'count=1'
    assert r2.status_code == 200
    assert r2.get_data(as_text=True) == 'count=1', 'second call must return cached body'
    assert r2.headers.get('Idempotent-Replay') == 'true'
    assert call_count['n'] == 1, 'handler must execute exactly once'


def test_different_keys_are_independent(app):
    call_count = {'n': 0}

    @app.route('/_test_idem2', methods=['POST'])
    @idempotent
    def view():
        call_count['n'] += 1
        return f'n={call_count["n"]}'

    client = app.test_client()
    r1 = client.post('/_test_idem2', headers={'Idempotency-Key': 'k1'})
    r2 = client.post('/_test_idem2', headers={'Idempotency-Key': 'k2'})

    assert r1.get_data(as_text=True) == 'n=1'
    assert r2.get_data(as_text=True) == 'n=2'
    assert call_count['n'] == 2


def test_no_key_still_executes(app):
    call_count = {'n': 0}

    @app.route('/_test_idem3', methods=['POST'])
    @idempotent
    def view():
        call_count['n'] += 1
        return 'ok'

    client = app.test_client()
    r1 = client.post('/_test_idem3')
    r2 = client.post('/_test_idem3')

    assert r1.get_data(as_text=True) == 'ok'
    assert r2.get_data(as_text=True) == 'ok'
    assert call_count['n'] == 2, 'without key, every request executes'


def test_status_and_headers_preserved(app):
    @app.route('/_test_idem4', methods=['POST'])
    @idempotent
    def view():
        return ('created', 201, {'X-Custom': 'yes'})

    client = app.test_client()
    r1 = client.post('/_test_idem4', headers={'Idempotency-Key': 'h1'})
    r2 = client.post('/_test_idem4', headers={'Idempotency-Key': 'h1'})

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.get_data(as_text=True) == 'created'
    # Custom header preserved on replay
    assert r2.headers.get('X-Custom') == 'yes'


def test_cache_key_uses_company(app):
    """Cache keys are scoped per company to prevent cross-tenant collisions."""
    with app.app_context():
        k1 = _cache_key(1, 'POST /a', 'key-1')
        k2 = _cache_key(2, 'POST /a', 'key-1')
        assert k1 != k2


def test_ttl_expiry(app):
    """Cached response expires after TTL."""
    key = _cache_key(1, 'POST /x', 'expire-key')
    _set_cached(key, {'status': 200, 'body': 'cached', 'headers': {}})

    # Manually expire it
    _LOCAL_CACHE[key]['expires'] = time.time() - 1
    assert _get_cached(key) is None


def test_idempotency_decorator_does_not_break_redirect(app):
    """PRG redirect responses (302) are also cached and replayed correctly."""
    from flask import redirect, url_for

    @app.route('/_test_idem5', methods=['POST'])
    @idempotent
    def view():
        return redirect('/somewhere')

    client = app.test_client()
    r1 = client.post('/_test_idem5', headers={'Idempotency-Key': 'r1'})
    r2 = client.post('/_test_idem5', headers={'Idempotency-Key': 'r1'})

    assert r1.status_code in (301, 302, 303)
    assert r2.status_code == r1.status_code
    assert r2.headers.get('Idempotent-Replay') == 'true'