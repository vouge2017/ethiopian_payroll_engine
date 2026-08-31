"""P0-C: Idempotency middleware for critical financial POST endpoints.

Mechanism: when a client sends `Idempotency-Key: <uuid>` header, the middleware
stores `(company_id, route, key) -> response_status` in Redis (or local cache
when Redis is unavailable) with a 24h TTL. Replays of the same key return
the cached response WITHOUT re-executing the handler.

Without an Idempotency-Key, requests pass through but are logged with a
warning so we can monitor retry-prone clients.

Protected routes (opt-in via decorator @idempotent):
- payroll.calculate
- payroll.approve_payroll
- payroll.disburse
- payroll.confirm_payment
- employees.terminate
- employees.invite
- adjustment.create
- filing.mark
"""
import functools
import hashlib
import json
import logging
import time
from typing import Optional

from flask import current_app, jsonify, make_response, request

logger = logging.getLogger('payroll_engine.idempotency')

# In-process fallback cache when Redis is unavailable. Keeps the
# last N responses to provide at-least-once safety in a single
# gunicorn worker. NOT safe across multiple workers; Redis is
# required for full safety.
_LOCAL_CACHE: dict = {}
_LOCAL_CACHE_MAX = 1024
_LOCAL_TTL_SECONDS = 86400


def _cache_key(company_id: int, route: str, idem_key: str) -> str:
    return f'idem:{company_id}:{route}:{idem_key}'


def _get_cached(key: str) -> Optional[dict]:
    """Return cached response dict or None."""
    # Try Redis first
    try:
        import redis as _redis

        from flask import current_app as _ca

        url = _ca.config.get('RATELIMIT_STORAGE_URI') or _ca.config.get('REDIS_URL')
        if url and not url.startswith('memory://'):
            r = _redis.Redis.from_url(url, decode_responses=True)
            raw = r.get(key)
            if raw:
                return json.loads(raw)
            return None
    except Exception as e:  # pragma: no cover - fall through to local
        logger.debug('idempotency redis lookup failed: %s', e)

    # Local fallback
    entry = _LOCAL_CACHE.get(key)
    if not entry:
        return None
    if entry['expires'] < time.time():
        _LOCAL_CACHE.pop(key, None)
        return None
    return entry['response']


def _set_cached(key: str, response: dict) -> None:
    """Store response dict in cache with 24h TTL."""
    try:
        import redis as _redis

        from flask import current_app as _ca

        url = _ca.config.get('RATELIMIT_STORAGE_URI') or _ca.config.get('REDIS_URL')
        if url and not url.startswith('memory://'):
            r = _redis.Redis.from_url(url, decode_responses=True)
            r.setex(key, _LOCAL_TTL_SECONDS, json.dumps(response))
            return
    except Exception as e:  # pragma: no cover
        logger.debug('idempotency redis set failed: %s', e)

    # Local fallback (LRU-ish)
    if len(_LOCAL_CACHE) >= _LOCAL_CACHE_MAX:
        # Drop the oldest
        try:
            oldest = next(iter(_LOCAL_CACHE))
            _LOCAL_CACHE.pop(oldest, None)
        except StopIteration:
            pass
    _LOCAL_CACHE[key] = {'response': response, 'expires': time.time() + _LOCAL_TTL_SECONDS}


def idempotent(view):
    """Decorator: mark a view as idempotent.

    Behaviour:
    - If `Idempotency-Key` header is present and a cached response exists
      for (company, route, key), return the cached response without
      executing the view.
    - If the header is present and no cached response exists, execute
      the view and cache the response (status + body) afterwards.
    - If the header is absent, the view executes normally and a warning
      is logged so we can identify clients that need to add the header.
    """
    import inspect

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        idem_key = request.headers.get('Idempotency-Key') or request.form.get('idempotency_key')
        if not idem_key:
            logger.warning(
                'idempotent view %s called without Idempotency-Key from %s',
                view.__name__,
                request.remote_addr,
            )
            return view(*args, **kwargs)

        # Tenant scope — must be present.
        company_id = None
        try:
            from flask_login import current_user

            if current_user.is_authenticated:
                company_id = (
                    current_user.company_id
                    or (current_user.get_role_for_company(None) and None)
                )
                # session active_company_id is authoritative for multi-company
                from flask import session

                company_id = session.get('active_company_id') or company_id
        except Exception:
            company_id = None

        route = f'{request.method} {request.path}'
        key = _cache_key(company_id or 0, route, idem_key)

        cached = _get_cached(key)
        if cached:
            logger.info('idempotent replay key=%s route=%s', idem_key, route)
            resp = make_response(cached.get('body', ''), cached.get('status', 200))
            resp.headers['Idempotent-Replay'] = 'true'
            for hk, hv in (cached.get('headers') or {}).items():
                resp.headers[hk] = hv
            return resp

        # Execute view
        response = view(*args, **kwargs)

        # Cache the response
        try:
            from flask import Response

            body = ''
            status = 200
            headers = {}
            if isinstance(response, tuple):
                # Flask tuple response: (body, status, headers)
                response_obj = make_response(response[0], response[1] if len(response) > 1 else 200)
                if len(response) > 2 and isinstance(response[2], dict):
                    response_obj.headers.update(response[2])
                body = response_obj.get_data(as_text=True)
                status = response_obj.status_code
                headers = dict(response_obj.headers)
            elif isinstance(response, Response):
                body = response.get_data(as_text=True)
                status = response.status_code
                headers = dict(response.headers)
            else:
                body = str(response)

            _set_cached(key, {'status': status, 'body': body, 'headers': headers})
        except Exception as e:  # pragma: no cover
            logger.warning('idempotency cache write failed: %s', e)

        return response

    return wrapper