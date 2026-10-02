"""Probe register with full response analysis."""
import urllib.request
import urllib.error
import re
import json

# Use a fresh phone
import random
phone = "9" + "".join(random.choices("0123456789", k=8))
email = f"e2e.probe{random.randint(1000,9999)}@ethiopayroll-test.com"

data = f'phone={phone}&email={email}&password=TestPass1%21Secure&password2=TestPass1%21Secure'
print(f"Testing with phone={phone}, email={email}")

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
    # Find flash messages
    flashes = re.findall(r'class="alert alert-(\w+)[^>]*>([^<]+)', body)
    if flashes:
        for cat, msg in flashes[:5]:
            print(f'  [{cat}] {msg.strip()[:200]}')
    else:
        # Check for errors in body
        if 'Account creation' in body or 'notnull' in body or 'failed' in body:
            idx = body.find('Account')
            if idx == -1:
                idx = body.find('notnull')
            if idx >= 0:
                print(f'Found error: {body[max(0,idx-50):idx+200]}')
        else:
            print('No flash and no error text found')
            # Check if form was re-rendered (with value)
            if f'value="{phone}"' in body:
                print('Form re-rendered with phone value preserved')
            else:
                print(f'Body length: {len(body)}')
                print(f'Body first 500: {body[:500]}')
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code}')
    body = e.read().decode('utf-8-sig', errors='ignore')
    flashes = re.findall(r'class="alert alert-(\w+)[^>]*>([^<]+)', body)
    for cat, msg in flashes[:5]:
        print(f'  [{cat}] {msg.strip()[:200]}')
