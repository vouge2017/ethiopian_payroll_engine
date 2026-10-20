"""Strict loopback readiness probe; never follows redirects or uses a proxy."""

import json
import os
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def main():
    try:
        port = int(os.environ.get('PORT', '5000'))
        # Render terminates TLS before Gunicorn. This private loopback request
        # supplies the same scheme header without weakening public HTTPS policy.
        request = urllib.request.Request(f'http://127.0.0.1:{port}/readyz', headers={'X-Forwarded-Proto': 'https'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=5) as response:
            payload = json.load(response)
            checks = payload.get('checks', {})
            ready = response.status == 200 and payload.get('status') == 'ready'
            ready = ready and all(
                checks.get(name) == value
                for name, value in {'database': 'up', 'migrations': 'current', 'schema': 'current'}.items()
            )
        return 0 if ready else 1
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f'Container readiness check failed ({type(error).__name__})')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
