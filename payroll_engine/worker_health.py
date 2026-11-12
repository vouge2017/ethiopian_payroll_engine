"""Recent PDF job activity in the RQ worker.

The PDF job writes a Redis key with a short TTL after successful work.
This is evidence of recent job activity, not proof that an idle worker is down.
/readyz reports the status of that key:

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
CRON_HEARTBEAT_KEY = 'cron:heartbeat'
HEARTBEAT_TTL_SECONDS = 180


def _redis_client():
    """Best-effort redis client from the broker URL; None if unavailable."""
    # Match tasks._get_queue and the RQ worker. A health-only URL can point
    # at a different Redis and must not produce a false worker signal.
    url = os.environ.get('REDIS_URL') or os.environ.get('REDISTOGO_URL')
    if not url or not url.startswith(('redis://', 'rediss://', 'unix://')):
        return None
    try:
        import redis

        return redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    except Exception:  # pragma: no cover - defensive
        return None


def beat(worker_id='worker-0', *, key=HEARTBEAT_KEY):
    """Record activity; report failure without disrupting a completed job."""
    try:
        r = _redis_client()
        if r is None:
            return False
        return bool(r.setex(key, HEARTBEAT_TTL_SECONDS, str(time.time())))
    except Exception:  # pragma: no cover - never break a job for a heartbeat
        logger.warning('Worker heartbeat write failed', exc_info=True)
        return False


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
    level = logging.CRITICAL if _consecutive_failures >= FAILURE_ALERT_THRESHOLD else logging.ERROR
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
