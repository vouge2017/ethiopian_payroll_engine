"""In-process RQ worker for PDF generation — the $0 single-service deployment.

Render free plans have no Background Worker service, so the RQ queue used by
`payroll_engine.tasks` would otherwise accept jobs nobody consumes. This module
starts a daemon thread running an RQ `SimpleWorker` inside the web process when
explicitly enabled with RUN_INPROCESS_WORKER=1 and REDIS_URL present.

SimpleWorker is mandatory here: the standard RQ Worker forks, and forking is
not permitted from a thread. A single free web instance runs one gunicorn
sync worker process, so one thread is sufficient; competing consumers on
plain RQ semantics mean additional workers stay safe.

Fails closed: any startup problem (missing redis, ping failure) logs a warning
and leaves the queue to the inline fallback in tasks._get_queue callers.
"""

import logging
import os
import threading

logger = logging.getLogger('payroll_engine.inprocess_worker')

_lock = threading.Lock()
_started = False


def _wants_worker():
    return os.environ.get('RUN_INPROCESS_WORKER', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _redis_connection():
    redis_url = os.environ.get('REDIS_URL') or os.environ.get('REDISTOGO_URL')
    if not redis_url:
        return None
    try:
        import redis

        conn = redis.from_url(redis_url)
        conn.ping()
        return conn
    except Exception as e:  # pragma: no cover - depends on live Redis
        logger.warning('in-process worker: Redis ping failed, not starting: %s', e)
        return None


def _thread_worker_class():
    """SimpleWorker subclass that never touches signal handlers.

    RQ installs SIGINT/SIGTERM handlers in work(); signal.signal only works
    in the main interpreter thread, so an in-thread worker must override it.
    """
    from rq import SimpleWorker

    return type('ThreadWorker', (SimpleWorker,), {'_install_signal_handlers': lambda self: None})


def _run_worker_thread(conn):
    """Long-lived work loop for the daemon thread."""
    worker = _thread_worker_class()(['pdf_generation'], connection=conn)
    try:
        worker.work(burst=False)
    except Exception as e:  # pragma: no cover - long-lived loop guard
        logger.error('in-process worker stopped: %s', e)


def maybe_start_inprocess_worker(app=None):
    """Start the in-process RQ worker thread when configured.

    Returns True if a worker thread was started (or is already running),
    False when the feature is disabled/Redis missing.
    """
    global _started
    if not _wants_worker():
        return False
    with _lock:
        if _started:
            return True
        conn = _redis_connection()
        if conn is None:
            return False
        try:
            logger.info('in-process worker starting on queue pdf_generation (pid=%s)', os.getpid())
            thread = threading.Thread(target=_run_worker_thread, args=(conn,), daemon=True, name='rq-inprocess')
            thread.start()
            _started = True
            if app is not None:
                app.extensions['inprocess_pdf_worker'] = thread
            return True
        except Exception as e:  # pragma: no cover - defensive
            logger.error('in-process worker failed to start: %s', e)
            return False
