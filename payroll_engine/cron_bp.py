"""P0-E: Internal cron blueprint for scheduled jobs.

This blueprint provides an authenticated HTTP endpoint that an external
cron service (Render Cron Job, GitHub Actions schedule, etc.) can hit
on a fixed schedule. The endpoint runs all daily/periodic tasks:

- daily_retention_purge (drafts / PDFs / previews / uploads)
- check_deadlines_and_notify (compliance reminders)
- generate_monthly_erca_reminder (20th of month only)
- LoginAttempt.cleanup_old

Authentication: shared-secret header `X-Cron-Secret` matched against
the `CRON_SECRET` env var. The endpoint is NOT exposed in any
external route map (no nav link, no public access).
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

logger = logging.getLogger('payroll_engine.cron')

cron_bp = Blueprint('cron', __name__, url_prefix='/internal/cron')


def _verify_cron_secret() -> bool:
    """Constant-time compare of X-Cron-Secret header against env var."""
    expected = os.environ.get('CRON_SECRET', '').strip()
    if not expected:
        # No secret configured — refuse all calls.
        return False
    provided = request.headers.get('X-Cron-Secret', '').strip()
    if not provided:
        return False
    return hmac.compare_digest(
        hashlib.sha256(provided.encode()).hexdigest(),
        hashlib.sha256(expected.encode()).hexdigest(),
    )


@cron_bp.route('/daily', methods=['POST'])
def daily():
    """Run all daily scheduled tasks.

    Idempotent — safe to call multiple times per day.
    Returns a JSON report of what was done.

    POST only: this is a state-mutating endpoint (retention purge writes
    the audit log, deadlines may notify). Accepting GET would (a) be
    cacheable by intermediaries, (b) make CSRF trivial, (c) be a CSRF
    surface. Render Cron Job uses POST.
    """
    if not _verify_cron_secret():
        logger.warning(
            'cron/daily called without valid secret from %s', request.remote_addr
        )
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    report = {
        'started_at': datetime.utcnow().isoformat() + 'Z',
        'tasks': {},
    }

    # 1. Retention purge
    try:
        from payroll_engine.retention import (
            purge_expired_drafts,
            purge_expired_payslip_pdfs,
            purge_expired_previews,
            purge_expired_uploads,
            purge_old_login_attempts,
        )
        from flask import current_app

        with current_app.app_context():
            n_pdfs = purge_expired_payslip_pdfs(current_app._get_current_object())
            n_drafts = purge_expired_drafts(current_app._get_current_object())
            n_previews = purge_expired_previews(current_app._get_current_object())
            n_uploads = purge_expired_uploads(current_app._get_current_object())
            n_attempts = purge_old_login_attempts()
        report['tasks']['retention'] = {
            'payslip_pdfs': n_pdfs,
            'drafts': n_drafts,
            'previews': n_previews,
            'uploads': n_uploads,
            'login_attempts': n_attempts,
        }
    except Exception as e:  # pragma: no cover
        logger.exception('cron/daily: retention failed')
        report['tasks']['retention'] = {'error': str(e)}

    # 2. Compliance deadline notifications
    try:
        from payroll_engine.scheduled import check_deadlines_and_notify
        check_deadlines_and_notify()
        report['tasks']['compliance'] = {'ok': True}
    except Exception as e:  # pragma: no cover
        logger.exception('cron/daily: compliance failed')
        report['tasks']['compliance'] = {'error': str(e)}

    # 3. Monthly ERCA reminder (only on 20th)
    try:
        if datetime.utcnow().day == 20:
            from payroll_engine.scheduled import generate_monthly_erca_reminder
            generate_monthly_erca_reminder()
            report['tasks']['erca_reminder'] = {'ok': True, 'day': 20}
        else:
            report['tasks']['erca_reminder'] = {'skipped': True, 'reason': 'not the 20th'}
    except Exception as e:  # pragma: no cover
        logger.exception('cron/daily: erca reminder failed')
        report['tasks']['erca_reminder'] = {'error': str(e)}

    # 4. Worker heartbeat (force a write so /readyz reflects activity)
    try:
        from payroll_engine.worker_health import heartbeat
        heartbeat()
        report['tasks']['worker_heartbeat'] = {'ok': True}
    except Exception as e:  # pragma: no cover
        logger.debug('cron/daily: worker heartbeat skipped: %s', e)
        report['tasks']['worker_heartbeat'] = {'skipped': str(e)}

    report['finished_at'] = datetime.utcnow().isoformat() + 'Z'
    report['ok'] = True
    return jsonify(report), 200


@cron_bp.route('/health', methods=['GET'])
def health():
    """Liveness probe for the cron endpoint (no secret required)."""
    return jsonify({
        'ok': True,
        'secret_configured': bool(os.environ.get('CRON_SECRET')),
    })
