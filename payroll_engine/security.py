"""Security helpers for auth redirects and safe error handling.

These helpers exist so every route that handles untrusted input uses the same
deliberate rules — not one-off string checks that drift over time.
"""

from __future__ import annotations

import uuid
from urllib.parse import urljoin, urlparse

from flask import current_app, flash, request, url_for


def safe_redirect_target(target: str | None, default_endpoint: str = 'main.index') -> str:
    """Return a same-host relative path safe for redirects, or the default route.

    Accepts relative paths (``/employees``) and absolute same-host URLs
    (e.g. ``request.referrer``). Always returns path + query + fragment only.

    Blocks open redirects including:
    - absolute off-host URLs (https://evil.example/...)
    - protocol-relative URLs (//evil.example/...)
    - backslash tricks (/\\evil.example)
    - scheme-smuggling and off-host urljoin results
    """
    default = url_for(default_endpoint)
    if not target:
        return default

    target = target.strip()
    if not target or '\\' in target:
        return default

    # Protocol-relative URLs are never safe as redirect targets.
    if target.startswith('//'):
        return default

    ref_url = urlparse(request.host_url)

    if target.startswith('/'):
        test_url = urlparse(urljoin(request.host_url, target))
    else:
        # Absolute URL (common for Referer headers)
        test_url = urlparse(target)
        if test_url.scheme not in ('http', 'https'):
            return default

    if test_url.scheme not in ('http', 'https'):
        return default
    if ref_url.netloc != test_url.netloc:
        return default
    if not test_url.path.startswith('/'):
        return default

    # Never return a full absolute URL — only path + query + fragment.
    safe = test_url.path or '/'
    if test_url.query:
        safe = f'{safe}?{test_url.query}'
    if test_url.fragment:
        safe = f'{safe}#{test_url.fragment}'
    return safe


def prevent_csv_injection(value: str) -> str:
    """Prefix dangerous leading characters that spreadsheet software would interpret as formulas.

    Prefixes with a tab character so the cell renders as text instead of
    executing =CMD(...), +FORMULA, -FORMULA, @LINK, or leading tab.
    """
    if not value:
        return value
    leading = value[:1]
    if leading in ('=', '+', '-', '@', '\t'):
        return '\t' + value
    return value


def log_and_flash_error(
    user_message: str,
    exc: BaseException,
    *,
    category: str = 'danger',
) -> str:
    """Log full exception server-side; flash a generic message with a reference ID.

    Users get a supportable reference. Operators get the real traceback in logs.
    Never interpolates exception text into the flash message.
    """
    error_id = uuid.uuid4().hex[:8]
    current_app.logger.exception(
        '%s (error_id=%s)',
        user_message,
        error_id,
        exc_info=exc,
    )
    flash(f'{user_message} Reference: {error_id}', category)
    return error_id
