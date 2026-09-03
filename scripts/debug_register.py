"""Test what happens when phone is missing/empty."""
import os
import re
import sys

os.environ['DB_ENCRYPTION_KEY'] = 'a-real-encryption-key-32-chars-minimum-here'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Disable rate limiting
os.environ['TESTING'] = '1'
os.environ['RATELIMIT_ENABLED'] = '0'

from payroll_engine import create_app
app = create_app()
app.config['TESTING'] = True
# Disable rate limiter
try:
    app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
    from payroll_engine.extensions import limiter
    limiter.enabled = False
except Exception:
    pass

def get_csrf(client):
    r = client.get('/auth/register', follow_redirects=True)
    html = r.get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None

def post_register(client, csrf, **data):
    r = client.post('/auth/register', data={
        'csrf_token': csrf,
        'first_name': data.get('first_name', 'Test'),
        'last_name': data.get('last_name', 'User'),
        'phone': data.get('phone', ''),
        'email': data.get('email', ''),
        'password': data.get('password', 'Strong1!Pass'),
        'password2': data.get('password2', 'Strong1!Pass'),
        'company_name': data.get('company_name', ''),
    }, follow_redirects=True)
    return r

with app.test_client() as c:
    print('=== Test 1: empty phone ===')
    csrf = get_csrf(c)
    r = post_register(c, csrf, phone='')
    print('Final URL:', r.request.path)
    body = r.get_data(as_text=True)
    # Look for the flash bar
    if 'onboarding-flash-bar' in body:
        idx = body.find('onboarding-flash-bar')
        # Find next 800 chars
        end = body.find('</main>', idx)
        print('FLASH AREA:', body[idx:end][:800])
    else:
        print('No flash bar')
        # Look for any alert div
        for m in re.finditer(r'class="alert[^"]*"[^>]*>([^<]*)', body):
            print('Alert:', m.group(1))

    print()
    print('=== Test 2: phone with spaces "91 123 4567" ===')
    csrf = get_csrf(c)
    r = post_register(c, csrf, phone='91 123 4567')
    print('Final URL:', r.request.path)
    body = r.get_data(as_text=True)
    if 'onboarding-flash-bar' in body:
        idx = body.find('onboarding-flash-bar')
        end = body.find('</main>', idx)
        print('FLASH AREA:', body[idx:end][:800])
    else:
        print('No flash bar')

    print()
    print('=== Test 3: phone with leading 0 "0911234567" ===')
    csrf = get_csrf(c)
    r = post_register(c, csrf, phone='0911234567')
    print('Final URL:', r.request.path)
    body = r.get_data(as_text=True)
    if 'onboarding-flash-bar' in body:
        idx = body.find('onboarding-flash-bar')
        end = body.find('</main>', idx)
        # Get the actual flash text
        flash_text = body[idx:end]
        # Strip HTML tags
        import re as re2
        text_only = re2.sub(r'<[^>]+>', ' ', flash_text)
        text_only = re2.sub(r'\s+', ' ', text_only).strip()
        print('FLASH TEXT:', text_only[:500])
    else:
        print('No flash bar')

    # Get fresh CSRF
    csrf = get_csrf(c)
    if not csrf:
        print('Cannot get CSRF, stopping')
        sys.exit(0)

    print()
    print('=== Test 3b: phone with leading 0 (fresh) ===')
    r = post_register(c, csrf, phone='0911234567')
    print('Final URL:', r.request.path)
    body = r.get_data(as_text=True)
    if 'onboarding-flash-bar' in body:
        idx = body.find('onboarding-flash-bar')
        end = body.find('</main>', idx)
        flash_text = body[idx:end]
        import re as re2
        text_only = re2.sub(r'<[^>]+>', ' ', flash_text)
        text_only = re2.sub(r'\s+', ' ', text_only).strip()
        print('FLASH TEXT:', text_only[:500])
    else:
        print('No flash bar')

    print()
    print('=== Test 4: valid 9-digit "911234567" ===')
    csrf = get_csrf(c)
    r = post_register(c, csrf, phone='911234567')
    print('Final URL:', r.request.path)
    body = r.get_data(as_text=True)
    if 'onboarding-flash-bar' in body:
        idx = body.find('onboarding-flash-bar')
        end = body.find('</main>', idx)
        print('FLASH AREA:', body[idx:end][:800])
    else:
        print('No flash bar - this means user was created (flash was success)')

