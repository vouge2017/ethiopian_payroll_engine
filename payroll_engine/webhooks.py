"""Webhook delivery service — HTTP POST to configured URLs with retry.

Supported events:
    payroll.approved      — Payroll run approved and finalized
    payroll.completed     — Payroll run calculation completed
    leave.approved        — Leave request approved
    leave.rejected        — Leave request rejected
    employee.created      — New employee added
    employee.updated      — Employee record modified
    payslip.generated     — Individual payslip created

Usage:
    from payroll_engine.webhooks import fire_webhook
    fire_webhook(company_id, 'payroll.approved', {'run_id': 1, 'total_net': 50000})
"""
import os
import hmac
import hashlib
import json
import time
from payroll_engine import db
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger('payroll_engine.webhooks')

# Webhook delivery can be disabled entirely
WEBHOOKS_ENABLED = os.environ.get('WEBHOOKS_ENABLED', 'true').lower() == 'true'

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 30]  # seconds between retries


def _sign_payload(payload_bytes, secret):
    """Generate HMAC-SHA256 signature for the payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


def _deliver(url, payload, secret=None, max_retries=MAX_RETRIES):
    """Deliver webhook payload to URL with retry. Runs in background thread.

    Retries on network errors and 5xx responses (not 4xx — those are permanent failures).
    Uses exponential backoff: 1s, 5s, 30s.
    """
    import requests
    payload_bytes = json.dumps(payload).encode('utf-8')
    event = payload.get('event', 'unknown')

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'EthioPayroll-Webhook/1.0',
        'X-Webhook-Event': event,
        'X-Webhook-Timestamp': payload.get('timestamp', ''),
        'X-Webhook-Delivery': '',  # Set per attempt
    }
    if secret:
        headers['X-Webhook-Signature'] = f'sha256={_sign_payload(payload_bytes, secret)}'

    for attempt in range(max_retries + 1):
        delivery_id = f'{event}-{int(time.time())}-{attempt}'
        headers['X-Webhook-Delivery'] = delivery_id

        try:
            resp = requests.post(url, data=payload_bytes, headers=headers, timeout=10)

            if resp.status_code < 400:
                logger.info(f'Webhook delivered [{delivery_id}] to {url}: {resp.status_code}')
                return True

            # 4xx = permanent failure, don't retry
            if 400 <= resp.status_code < 500:
                logger.warning(
                    f'Webhook rejected [{delivery_id}] by {url}: {resp.status_code} '
                    f'(permanent, no retry)'
                )
                return False

            # 5xx = server error, retry
            logger.warning(
                f'Webhook server error [{delivery_id}] from {url}: {resp.status_code} '
                f'(attempt {attempt + 1}/{max_retries + 1})'
            )

        except requests.exceptions.Timeout:
            logger.warning(
                f'Webhook timeout [{delivery_id}] to {url} '
                f'(attempt {attempt + 1}/{max_retries + 1})'
            )
        except requests.exceptions.ConnectionError:
            logger.warning(
                f'Webhook connection error [{delivery_id}] to {url} '
                f'(attempt {attempt + 1}/{max_retries + 1})'
            )
        except Exception as e:
            logger.error(
                f'Webhook unexpected error [{delivery_id}] to {url}: {e} '
                f'(attempt {attempt + 1}/{max_retries + 1})'
            )

        # Wait before retry (skip wait on last attempt)
        if attempt < max_retries:
            time.sleep(RETRY_DELAYS[attempt])

    logger.error(f'Webhook FAILED after {max_retries + 1} attempts to {url} [{event}]')
    return False


def fire_webhook(company_id, event, data):
    """Fire a webhook event for a company.

    Args:
        company_id: Company ID
        event: Event name (e.g., 'payroll.approved', 'leave.approved')
        data: Event data dict
    """
    if not WEBHOOKS_ENABLED:
        return

    from payroll_engine.models import Company
    company = db.session.get(Company, company_id)
    if not company or not company.webhook_url:
        return

    # Resolve URL and secret before spawning thread (no DB access in thread)
    url = company.webhook_url
    secret = company.webhook_secret
    company_name = company.name

    payload = {
        'event': event,
        'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        'company_id': company_id,
        'company_name': company_name,
        'data': data,
    }

    # Deliver in background thread (non-blocking)
    thread = threading.Thread(
        target=_deliver,
        args=(url, payload, secret),
        daemon=True,
    )
    thread.start()
