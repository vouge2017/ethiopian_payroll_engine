"""In-process RQ worker bootstrap guards."""

import importlib
import threading

import pytest


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    import payroll_engine.inprocess_worker as iw

    monkeypatch.setattr(iw, '_started', False)
    yield


def _collect_thread_names():
    return {t.name for t in threading.enumerate()}


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv('RUN_INPROCESS_WORKER', raising=False)
    monkeypatch.setenv('REDIS_URL', 'redis://127.0.0.1:6399/0')
    import payroll_engine.inprocess_worker as iw

    assert iw.maybe_start_inprocess_worker(None) is False
    assert 'rq-inprocess' not in _collect_thread_names()


def test_requires_redis_url(monkeypatch):
    monkeypatch.setenv('RUN_INPROCESS_WORKER', '1')
    monkeypatch.delenv('REDIS_URL', raising=False)
    monkeypatch.delenv('REDISTOGO_URL', raising=False)
    import payroll_engine.inprocess_worker as iw

    assert iw.maybe_start_inprocess_worker(None) is False
    assert 'rq-inprocess' not in _collect_thread_names()


def test_starts_thread_when_enabled(monkeypatch):
    import payroll_engine.inprocess_worker as iw

    started = {}

    class _StubThread(threading.Thread):
        def __init__(self, target=None, args=None, daemon=None, name=None):
            super().__init__(target=target, args=args, daemon=daemon, name=name)
            started['args'] = args
            started['name'] = name

    monkeypatch.setenv('RUN_INPROCESS_WORKER', 'true')
    monkeypatch.setenv('REDIS_URL', 'redis://redis-test:6379/0')

    class _StubConn:
        def ping(self):
            return True

    monkeypatch.setattr(iw, '_redis_connection', lambda: _StubConn())
    monkeypatch.setattr(threading, 'Thread', _StubThread)

    # stub the long-lived work loop so the thread, if ever really started,
    # exits immediately
    monkeypatch.setattr(iw, '_run_worker_once', lambda conn: None)

    assert iw.maybe_start_inprocess_worker(None) is True
    assert started['name'] == 'rq-inprocess'
    assert len(started['args']) == 1
    assert isinstance(started['args'][0], _StubConn)


def test_run_worker_once_uses_simple_worker(monkeypatch):
    """Guard against switching to forking Worker: threads cannot fork."""
    import payroll_engine.inprocess_worker as iw

    called = {}
    calls = []

    class _StubWorker:
        def __init__(self, queues, connection=None):
            called['queues'] = queues
            called['connection'] = connection

        def work(self, burst=False):
            calls.append({'burst': burst})

    import rq

    monkeypatch.setattr(rq, 'SimpleWorker', _StubWorker)
    iw._run_worker_once('conn')
    assert called['queues'] == ['pdf_generation']
    assert called['connection'] == 'conn'
    assert calls == [{'burst': False}]


def test_no_thread_when_redis_ping_fails(monkeypatch):
    """Real code path: ping raises inside the try, caught, returns None."""
    import sys
    import types

    import payroll_engine.inprocess_worker as iw

    monkeypatch.setenv('RUN_INPROCESS_WORKER', '1')
    monkeypatch.setenv('REDIS_URL', 'redis://unreachable:6379/0')

    class _FakeConn:
        def ping(self):
            raise ConnectionError('down')

    fake_redis = types.ModuleType('redis')
    fake_redis.from_url = lambda *a, **k: _FakeConn()
    monkeypatch.setitem(sys.modules, 'redis', fake_redis)

    assert iw.maybe_start_inprocess_worker(None) is False
    assert 'rq-inprocess' not in _collect_thread_names()


def test_module_importable_and_wired_in_app_factory():
    """create_app must reference the bootstrap so prod picks it up."""
    src = importlib.import_module('payroll_engine')
    factory_src = src.__file__
    with open(factory_src, encoding='utf-8') as fh:
        text = fh.read()
    assert 'maybe_start_inprocess_worker' in text
