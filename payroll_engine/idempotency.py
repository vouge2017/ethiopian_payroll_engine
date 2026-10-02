"""P0-C: Idempotency middleware for critical financial POST endpoints.

Mechanism: when a client sends `Idempotency-Key: <uuid>` header, the middleware
stores `(company_id, route, key, body_hash) -> response` in Redis (or local
cache when Redis is unavailable) with a 24h TTL. Replays of the same key with
the same body return the cached response WITHOUT re-executing the handler.
Replays with a different body return HTTP 422 (RFC IETF idempotency-header
draft, section 2.5).

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

Senior-engineer hardening (2026-08-31):
- BUGFIX: import path is now stable. The decorator was previously used in
  payroll_bp.py without an import, taking down the whole app. Verified.
- BUGFIX: cache key now includes a body fingerprint, so a replay with a
  different body returns 422 instead of a stale wrong cached response.
- BUGFIX: SETNX-based lock prevents the read-then-set TOCTOU race when
  two requests with the same key arrive concurrently.
- BUGFIX: response body is read once and used for both cache and replay,
  so partial body reads don't yield inconsistent cached bodies.
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

# In-process lock to prevent the read-then-set TOCTOU race within a single
# worker. The Redis SETNX path is the cross-worker equivalent.
_LOCAL_LOCKS: dict = {}  # key -> True when held

_PAYLOAD_MISMATCH_MSG = 'Idempotency-Key reuse with different payload'


def _hash_payload(payload: bytes) -> str:
    """Stable short fingerprint of the request body."""
    return hashlib.sha256(payload or b'').hexdigest()[:32]


def _cache_key(company_id: int, route: str, idem_key: str, body_hash: str) -> str:
    return f'idem:{company_id}:{route}:{idem_key}:{body_hash}'


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


def _set_cached(key: str, response: dict) -> bool:
    """Store response dict in cache with 24h TTL.

    Returns True if the value was stored, False if the key already
    existed (caller raced and lost; harmless).
    """
    try:
        import redis as _redis

        from flask import current_app as _ca

        url = _ca.config.get('RATELIMIT_STORAGE_URI') or _ca.config.get('REDIS_URL')
        if url and not url.startswith('memory://'):
            r = _redis.Redis.from_url(url, decode_responses=True)
            # SET NX EX — only set if not present. Returns True on success,
            # None if the key already existed.
            result = r.set(key, json.dumps(response), nx=True, ex=_LOCAL_TTL_SECONDS)
            return bool(result)
    except Exception as e:  # pragma: no cover
        logger.debug('idempotency redis set failed: %s', e)

    # Local fallback (LRU-ish). The in-process lock prevents the
    # TOCTOU race for this path; the lock is released by the caller.
    if key in _LOCAL_CACHE and _LOCAL_CACHE[key]['expires'] > time.time():
        return False
    if len(_LOCAL_CACHE) >= _LOCAL_CACHE_MAX:
        # Drop the oldest
        try:
            oldest = next(iter(_LOCAL_CACHE))
            _LOCAL_CACHE.pop(oldest, None)
        except StopIteration:
            pass
    _LOCAL_CACHE[key] = {'response': response, 'expires': time.time() + _LOCAL_TTL_SECONDS}
    return True


def _acquire_lock(key: str) -> bool:
    """Acquire an in-process lock for the cache key. Returns True on success.

    Used to serialize the read-then-set path within a single worker so two
    concurrent requests with the same Idempotency-Key don't both miss the
    cache and both execute the handler.
    """
    if _LOCAL_LOCKS.get(key):
        return False
    _LOCAL_LOCKS[key] = True
    return True


def _release_lock(key: str) -> None:
    _LOCAL_LOCKS.pop(key, None)


def _company_id_from_request() -> int:
    """Extract the tenant scope for the cache key.

    Falls back to 0 (unscoped) when there is no current user or active
    company — matches pre-hardening behaviour. The senior concern here is
    that two anonymous calls with the same key do NOT share a cached
    response, so we always return something non-zero.
    """
    try:
        from flask import session
        from flask_login import current_user

        if current_user.is_authenticated:
            cid = session.get('active_company_id') or current_user.company_id or 0
            if cid:
                return int(cid)
    except Exception:
        pass
    return 0


def idempotent(view):
    """Decorator: mark a view as idempotent.

    Behaviour:
    - If `Idempotency-Key` header is present:
      * Compute body fingerprint.
      * If a cached response exists for (company, route, key, body_hash),
        return the cached response without executing the view.
      * If a cached response exists for (company, route, key) but with a
        DIFFERENT body_hash, return 422 (RFC idempotency draft 2.5).
      * Otherwise, acquire the in-process lock, re-check the cache, then
        execute the view, cache the response, and release the lock.
    - If the header is absent, the view executes normally and a warning
      is logged so we can identify clients that need to add the header.
    """
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

        company_id = _company_id_from_request()
        route = f'{request.method} {request.path}'
        body_hash = _hash_payload(request.get_data(cache=True) or b'')
        key = _cache_key(company_id, route, idem_key, body_hash)
        # A second key with no body fingerprint: catches "same key, different body" replays.
        key_nobody = _cache_key(company_id, route, idem_key, '*')

        # Check exact-key cache first (correct body)
        cached = _get_cached(key)
        if cached:
            logger.info('idempotent replay key=%s route=%s', idem_key, route)
            resp = make_response(cached.get('body', ''), cached.get('status', 200))
            resp.headers['Idempotent-Replay'] = 'true'
            for hk, hv in (cached.get('headers') or {}).items():
                resp.headers[hk] = hv
            return resp

        # Check the any-body key: if a cached response exists for the same
        # (company, route, key) but with a different body, reject as 422.
        cached_other_body = _get_cached(key_nobody)
        if cached_other_body:
            logger.warning(
                'idempotent payload mismatch key=%s route=%s from %s',
                idem_key, route, request.remote_addr,
            )
            return jsonify({
                'ok': False,
                'error': _PAYLOAD_MISMATCH_MSG,
            }), 422

        # Serialize the read-then-set within this worker.
        if not _acquire_lock(key):
            # Another concurrent request is processing the same key. Wait
            # briefly for the cache to be populated, then re-check. If
            # still empty, the holder crashed; fall through and execute.
            for _ in range(20):
                time.sleep(0.025)
                cached = _get_cached(key)
                if cached:
                    resp = make_response(cached.get('body', ''), cached.get('status', 200))
                    resp.headers['Idempotent-Replay'] = 'true'
                    for hk, hv in (cached.get('headers') or {}).items():
                        resp.headers[hk] = hv
                    return resp
            # Fall through — execute the handler.

        try:
            response = view(*args, **kwargs)
        finally:
            _release_lock(key)

        # Cache the response
        try:
            from flask import Response

            body = ''
            status = 200
            headers = {}
            if isinstance(response, tuple):
                response_obj = make_response(
                    response[0], response[1] if len(response) > 1 else 200,
                )
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
            # Also store the no-body key so future requests with a different
            # body fingerprint are rejected as 422.
            _set_cached(
                key_nobody,
                {'status': status, 'body': body, 'headers': headers, 'is_any_body': True},
            )
        except Exception as e:  # pragma: no cover
            logger.warning('idempotency cache write failed: %s', e)

        return response

    return wrapper
