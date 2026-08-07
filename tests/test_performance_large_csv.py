"""Performance benchmark: 10,000-row payroll CSV processing."""

import csv
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, OvertimeEntry, TenantQuery, User

TARGET_THRESHOLD_SEC = 30.0
ROW_COUNT = 10000


def _generate_large_csv(rows: int) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['employee_id', 'name', 'basic_salary', 'allowances', 'bank_or_telebirr', 'tin'])
    for i in range(rows):
        writer.writerow([f'EMP{i:06d}', f'Employee {i}', '5000', '1000', '', ''])
    return output.getvalue().encode('utf-8')


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def company_user(app):
    with app.app_context():
        company = Company(name='PerfTestCo')
        db.session.add(company)
        db.session.commit()
        user = User(phone='0911000099', company_id=company.id, role='owner')
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.commit()
        return company, user


def _login(client):
    client.post('/auth/login', data={'login_id': '0911000099', 'password': 'Test1234!'}, follow_redirects=True)


@pytest.mark.benchmark
def test_large_csv_upload_performance(app, client, company_user):
    _login(client)
    csv_data = _generate_large_csv(ROW_COUNT)

    start = time.perf_counter()
    resp = client.post(
        '/payroll',
        data={'file': (io.BytesIO(csv_data), 'large_payroll.csv')},
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200, f'Upload failed with status {resp.status_code}'
    assert elapsed < TARGET_THRESHOLD_SEC, (
        f'Processing {ROW_COUNT} rows took {elapsed:.2f}s, exceeding threshold of {TARGET_THRESHOLD_SEC}s'
    )
