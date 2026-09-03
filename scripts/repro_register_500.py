"""Reproduce the /auth/register 500 error."""
import os
import re
import sys

os.environ['DB_ENCRYPTION_KEY'] = 'a-real-encryption-key-32-chars-minimum-here'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app
app = create_app()

with app.test_client() as c:
    r = c.get('/auth/register', follow_redirects=True)
    print('GET status:', r.status_code)
    print('Final URL:', r.request.path)
    html = r.get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m:
        print('No CSRF token found')
        print('First 500 chars of body:', html[:500])
        sys.exit(1)
    csrf = m.group(1)
    print('CSRF found')

    r = c.post('/auth/register', data={
        'csrf_token': csrf,
        'first_name': 'Test',
        'middle_name': '',
        'last_name': 'User',
        'phone': '911234567',
        'email': '',
        'password': 'Strong1!Pass',
        'password2': 'Strong1!Pass',
        'company_name': 'TestCo',
    }, follow_redirects=True)
    print('POST status:', r.status_code)
    print('Final URL:', r.request.path)
    if r.status_code >= 400:
        body = r.get_data(as_text=True)
        print('Body (first 5000 chars):', body[:5000])
