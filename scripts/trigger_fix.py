"""Trigger the fix route with CSRF token."""
import urllib.request
import urllib.error
import re
import json
import http.cookiejar

BASE = 'https://ethiopian-payroll-engine.onrender.com'

# Use cookie jar
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# GET first to get CSRF token
r = opener.open(f'{BASE}/admin/fix-user-columns', timeout=30)
body = r.read().decode('utf-8-sig', errors='ignore')
m = re.search(r'name="csrf-token" content="([^"]+)"', body)
if not m:
    print('No CSRF token found')
    print(body[:2000])
    exit(1)
csrf = m.group(1)
print(f'CSRF: {csrf[:30]}...')

# POST with CSRF
data = f'csrf_token={csrf}'.encode()
req = urllib.request.Request(
    f'{BASE}/admin/fix-user-columns',
    data=data,
    method='POST',
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrf,
        'Referer': f'{BASE}/admin/fix-user-columns',
    },
)
try:
    r = opener.open(req, timeout=60)
    body = r.read().decode('utf-8-sig', errors='ignore')
    print(f'POST status: {r.status}')
    print(f'Response: {body[:1000]}')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8-sig', errors='ignore')
    print(f'POST error: {e.code}')
    print(f'Response: {body[:1000]}')
