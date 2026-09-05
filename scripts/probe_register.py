"""Probe register endpoint to see actual error."""
import urllib.request
import urllib.error
import re

data = 'phone=960879872&email=e2e.test%40ethiopayroll-test.com&password=TestPass1%21Secure&password2=TestPass1%21Secure'
req = urllib.request.Request(
    'https://ethiopian-payroll-engine.onrender.com/auth/register',
    data=data.encode(),
    method='POST',
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
)
try:
    r = urllib.request.urlopen(req, timeout=30)
    print(f'Status: {r.status}')
    body = r.read().decode('utf-8-sig', errors='ignore')
    # Find flash message
    for m in re.finditer(r'class="alert alert-(\w+)[^>]*>([^<]+)', body):
        print(f'Flash: [{m.group(1)}] {m.group(2)[:200]}')
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code}')
    body = e.read().decode('utf-8-sig', errors='ignore')
    for m in re.finditer(r'class="alert alert-(\w+)[^>]*>([^<]+)', body):
        print(f'Flash: [{m.group(1)}] {m.group(2)[:200]}')
