"""Worker heartbeat — proves the RQ worker is alive and processing.

The worker writes a Redis key with a short TTL after every job and on a
periodic timer. /readyz reports worker status from that key:

    up      -> key exists (heartbeat within TTL)
    stale   -> key missing but was seen since process start
    unknown -> no Redis configured or never seen (non-fatal)

Failure alerting: job failures are logged at ERROR level, which Sentry
picks up via the existing logging integration; a consecutive-failure
counter raises to CRITICAL so ops alerts fire on burst failures.
"""

import logging
import os
import time

logger = logging.getLogger('payroll_engine.tasks')

HEARTBEAT_KEY = 'worker:heartbeat'
HEARTBEAT_TTL_SECONDS = 180  # 3x the expected idle poll interval


def _redis_client():
    """Best-effort redis client from the broker URL; None if unavailable."""
    url = (
        os.environ.get('RQ_REDIS_URL')
        or os.environ.get('CELERY_BROKER_URL')
        or 'redis://localhost:6379/0'
    )
    if not url.startswith('redis'):
        return None  # memory:// in tests/CI — no persistence to watch
    try:
        import redis

        return redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    except Exception:  # pragma: no cover - defensive
        return None


def beat(worker_id='worker-0'):
    """Record liveness. Safe to call anywhere; never raises."""
    try:
        r = _redis_client()
        if r is not None:
            r.setex(HEARTBEAT_KEY, HEARTBEAT_TTL_SECONDS, str(time.time()))
    except Exception:  # pragma: no cover - never break a job for a heartbeat
        logger.warning('Worker heartbeat write failed', exc_info=True)


def heartbeat_status():
    """Return 'up' | 'stale' | 'unknown' for /readyz."""
    global _ever_seen
    try:
        r = _redis_client()
        if r is None:
            return 'unknown'
        if r.exists(HEARTBEAT_KEY):
            _ever_seen = True
            return 'up'
        return 'stale' if _ever_seen else 'unknown'
    except Exception:  # pragma: no cover
        return 'unknown'


_ever_seen = False

# Consecutive failure tracking for burst-alerting
_consecutive_failures = 0
FAILURE_ALERT_THRESHOLD = 5


def note_job_failure(job_id, exc):
    """Log failures loudly; escalate after repeated consecutive failures."""
    global _consecutive_failures
    _consecutive_failures += 1
    level = (
        logging.CRITICAL
        if _consecutive_failures >= FAILURE_ALERT_THRESHOLD
        else logging.ERROR
    )
    logger.log(
        level,
        'Payslip PDF job failed (job_id=%s, consecutive=%s)',
        job_id,
        _consecutive_failures,
        exc_info=exc,
    )


def note_job_success():
    global _consecutive_failures
    _consecutive_failures = 0
