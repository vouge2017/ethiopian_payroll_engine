"""Worker heartbeat Redis URL resolution (monitoring slice 2026-10-18)."""

import os

import pytest

from payroll_engine import worker_health


@pytest.fixture(autouse=True)
def _clean_broker_env(monkeypatch):
    for name in ('RQ_REDIS_URL', 'REDIS_URL', 'CELERY_BROKER_URL'):
        monkeypatch.delenv(name, raising=False)


def test_redis_url_is_accepted():
    monkey_redis = 'redis://:indexpass@hbhost:6379/3'
    os.environ['REDIS_URL'] = monkey_redis
    try:
        client = worker_health._redis_client()
        assert client is not None
        kwargs = client.connection_pool.connection_kwargs
        assert kwargs['host'] == 'hbhost'
        assert kwargs['port'] == 6379
        assert kwargs['db'] == 3
    finally:
        del os.environ['REDIS_URL']


def test_rq_redis_url_wins_over_redis_url(monkeypatch):
    monkeypatch.setenv('RQ_REDIS_URL', 'redis://broker-a:6379/0')
    monkeypatch.setenv('REDIS_URL', 'redis://broker-b:6379/0')
    client = worker_health._redis_client()
    assert client.connection_pool.connection_kwargs['host'] == 'broker-a'


def test_memory_broker_returns_none(monkeypatch):
    monkeypatch.setenv('CELERY_BROKER_URL', 'memory://')
    assert worker_health._redis_client() is None


def test_defaults_to_local_redis(monkeypatch):
    assert worker_health._redis_client().connection_pool.connection_kwargs['host'] == 'localhost'
