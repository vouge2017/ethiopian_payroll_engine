"""Webhook delivery service — fire-and-forget HTTP POST to configured URLs.

Usage:
    from payroll_engine.webhooks import fire_webhook
    fire_webhook(company_id, 'payroll.approved', {'run_id': 1, 'total_net': 50000})
"""
import os
import hmac
import hashlib
import json
from payroll_engine import db
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger('payroll_engine.webhooks')

# Webhook delivery can be disabled entirely
WEBHOOKS_ENABLED = os.environ.get('WEBHOOKS_ENABLED', 'true').lower() == 'true'


def _sign_payload(payload_bytes, secret):
    """Generate HMAC-SHA256 signature for the payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


def _deliver(url, payload, secret=None):
    """Deliver webhook payload to URL. Runs in background thread."""
    try:
        import requests
        payload_bytes = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'EthioPayroll-Webhook/1.0',
            'X-Webhook-Event': payload.get('event', 'unknown'),
            'X-Webhook-Timestamp': payload.get('timestamp', ''),
        }
        if secret:
            headers['X-Webhook-Signature'] = f'sha256={_sign_payload(payload_bytes, secret)}'

        resp = requests.post(url, data=payload_bytes, headers=headers, timeout=10)
        logger.info(f'Webhook delivered to {url}: {resp.status_code}')
    except Exception as e:
        logger.error(f'Webhook delivery failed to {url}: {e}')


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
