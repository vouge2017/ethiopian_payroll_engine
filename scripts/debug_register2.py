"""Debug register flow."""
import os
import logging
logging.basicConfig(level=logging.DEBUG)
for noisy in ('sqlalchemy.engine', 'alembic'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

os.environ['DB_ENCRYPTION_KEY'] = 'a-real-encryption-key-32-chars-minimum-here'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
import sys
sys.path.insert(0, '.')

from payroll_engine import create_app, db
from payroll_engine.models import Company, User

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    db.create_all()
    print('Schema created')

client = app.test_client()
r = client.post('/auth/register', data={
    'phone': '911234567',
    'email': 'alice@test.com',
    'password': 'SecurePass123!',
    'password2': 'SecurePass123!',
    'company_name': 'New Company',
}, follow_redirects=False)
loc = r.headers.get('Location')
print(f'Status: {r.status_code}, Location: {loc}')

# Check response body for errors
body = r.get_data(as_text=True)
print(f'Body has session-expired: {"session expired" in body.lower()}')
print(f'Body has csrf: {"csrf" in body.lower()}')
print(f'Body length: {len(body)}')
# Print all error-like substrings
import re
for m in re.finditer(r'(?i)(error|invalid|expired|required|csrf|denied|forbidden|redirect|login)', body):
    start = max(0, m.start() - 30)
    end = min(len(body), m.end() + 50)
    print(f'  {m.group(0)}: ...{body[start:end]}...')

with app.app_context():
    user = User.query.filter_by(phone='911234567').first()
    print(f'User: {user}')
    if user:
        print(f'  company_id: {user.company_id}')
    company = Company.query.filter_by(name='New Company').first()
    print(f'Company: {company}')
