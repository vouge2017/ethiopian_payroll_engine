"""Worker health must inspect the RQ backend without inventing liveness."""

import pytest

from payroll_engine import worker_health


@pytest.fixture(autouse=True)
def clean_redis_environment(monkeypatch):
    for name in ('REDIS_URL', 'REDISTOGO_URL', 'RQ_REDIS_URL', 'CELERY_BROKER_URL'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(worker_health, '_ever_seen', False)


@pytest.mark.parametrize('name', ['REDIS_URL', 'REDISTOGO_URL'])
@pytest.mark.parametrize(
    'url', ['redis://example.invalid:6379/0', 'rediss://example.invalid:6379/0', 'unix:///tmp/fake-redis.sock']
)
def test_health_uses_rq_queue_url(monkeypatch, name, url):
    import redis

    captured = []
    monkeypatch.setenv(name, url)
    monkeypatch.setattr(redis, 'from_url', lambda url, **kwargs: captured.append(url) or object())
    assert worker_health._redis_client() is not None
    assert captured == [url]


def test_queue_url_takes_precedence_over_legacy_health_urls(monkeypatch):
    import redis

    captured = []
    monkeypatch.setenv('REDIS_URL', 'redis://queue.invalid/0')
    monkeypatch.setenv('REDISTOGO_URL', 'redis://secondary.invalid/0')
    monkeypatch.setenv('RQ_REDIS_URL', 'redis://other.invalid/0')
    monkeypatch.setattr(redis, 'from_url', lambda url, **kwargs: captured.append(url) or object())
    worker_health._redis_client()
    assert captured == ['redis://queue.invalid/0']


def test_legacy_health_only_configuration_does_not_claim_rq_health(monkeypatch):
    monkeypatch.setenv('RQ_REDIS_URL', 'redis://other.invalid/0')
    assert worker_health._redis_client() is None
    assert worker_health.heartbeat_status() == 'unknown'


def test_missing_or_failed_redis_is_unknown_and_beat_fails(monkeypatch):
    assert worker_health.heartbeat_status() == 'unknown'
    assert worker_health.beat() is False


def test_cron_write_does_not_create_worker_heartbeat(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.values = {}

        def setex(self, key, _ttl, value):
            self.values[key] = value
            return True

        def exists(self, key):
            return key in self.values

    redis = FakeRedis()
    monkeypatch.setattr(worker_health, '_redis_client', lambda: redis)
    assert worker_health.beat('daily-cron', key=worker_health.CRON_HEARTBEAT_KEY) is True
    assert worker_health.heartbeat_status() == 'unknown'
    assert worker_health.beat() is True
    assert worker_health.heartbeat_status() == 'up'
    del redis.values[worker_health.HEARTBEAT_KEY]
    assert worker_health.heartbeat_status() == 'stale'
    monkeypatch.setattr(worker_health, '_redis_client', lambda: BrokenRedis())
    assert worker_health.heartbeat_status() == 'unknown'
    assert worker_health.beat() is False


class BrokenRedis:
    def exists(self, _key):
        raise ConnectionError('synthetic unavailable Redis')

    def setex(self, *_args):
        raise ConnectionError('synthetic unavailable Redis')
