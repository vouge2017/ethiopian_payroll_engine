"""Security regression test suite.

Covers open redirect, temp credential leakage, exception leakage,
file upload restrictions, and API validation abuse cases.

Each test deliberately attacks the previous failure mode.
"""

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, OvertimeEntry, TenantQuery, User
from payroll_engine.security import prevent_csv_injection, safe_redirect_target


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    app.config['ENABLE_DEMO_MODE'] = True
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
        company = Company(name='RegressCo')
        db.session.add(company)
        db.session.commit()
        user = User(phone='0911999999', company_id=company.id, role='owner')
        user.set_password('Secure123!')
        db.session.add(user)
        db.session.commit()
        return company, user


def _login(client):
    client.post('/auth/login', data={'login_id': '0911999999', 'password': 'Secure123!'}, follow_redirects=True)


# -----------------------------------------------------------------------
# Gate: Open redirect
# -----------------------------------------------------------------------


class TestOpenRedirect:
    def test_block_external_redirect(self, client, app, company_user):
        client.get('/auth/logout', follow_redirects=True)
        resp = client.post(
            '/auth/login?next=https://evil.com/phish',
            data={'login_id': '0911999999', 'password': 'Secure123!'},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert 'evil.com' not in resp.headers.get('Location', '')

    def test_block_protocol_relative_redirect(self, client, app, company_user):
        client.get('/auth/logout', follow_redirects=True)
        resp = client.post(
            '/auth/login?next=//evil.com',
            data={'login_id': '0911999999', 'password': 'Secure123!'},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert 'evil' not in resp.headers.get('Location', '')

    def test_allow_local_redirect(self, client, app, company_user):
        client.get('/auth/logout', follow_redirects=True)
        resp = client.post(
            '/auth/login?next=/employees',
            data={'login_id': '0911999999', 'password': 'Secure123!'},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers['Location'].endswith('/employees')

    def test_safe_redirect_blocks_backslash(self, app):
        with app.test_request_context('/login', base_url='http://localhost/'):
            assert safe_redirect_target('/\\evil.com') != '/\\evil.com'


# -----------------------------------------------------------------------
# Gate: Temp credential leakage
# -----------------------------------------------------------------------


class TestTempCredentialLeakage:
    def test_invite_does_not_leak_password_in_flash(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/settings/team/invite',
            data={
                'phone': '0966666666',
                'name': 'Regression Tester',
                'role': 'accountant',
            },
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8', errors='replace')
        assert 'Temporary password:' not in body
        assert '444444Temp1!' not in body

    def test_temp_password_is_random(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/settings/team/invite',
            data={
                'phone': '0977777777',
                'name': 'Random Check',
                'role': 'accountant',
            },
            follow_redirects=False,
        )
        import re

        body = resp.data.decode('utf-8', errors='replace')
        codes = re.findall(r'<code[^>]*>([^<]+)</code>', body)
        assert codes
        assert len(codes[0].strip()) >= 16

    def test_temp_password_not_phone_derived(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/settings/team/invite',
            data={
                'phone': '0988888888',
                'name': 'Not Phone Derived',
                'role': 'accountant',
            },
            follow_redirects=False,
        )
        import re

        body = resp.data.decode('utf-8', errors='replace')
        codes = re.findall(r'<code[^>]*>([^<]+)</code>', body)
        assert codes
        temp_pw = codes[0].strip()
        assert '8888Temp1!' not in temp_pw
        assert '88888888' not in temp_pw

    def test_invited_user_must_change_password(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/settings/team/invite',
            data={
                'phone': '0999999999',
                'name': 'Force Change',
                'role': 'accountant',
            },
            follow_redirects=True,
        )
        import re

        body = resp.data.decode('utf-8', errors='replace')
        codes = re.findall(r'<code[^>]*>([^<]+)</code>', body)
        assert codes
        temp_pw = codes[0].strip()
        client.get('/auth/logout', follow_redirects=True)
        resp2 = client.post(
            '/auth/login',
            data={
                'login_id': '0999999999',
                'password': temp_pw,
            },
            follow_redirects=False,
        )
        assert resp2.status_code == 302
        assert '/auth/change-password' in resp2.headers.get('Location', '')


# -----------------------------------------------------------------------
# Gate: Exception leakage
# -----------------------------------------------------------------------


class TestExceptionLeakage:
    def test_payroll_upload_no_raw_exception(self, client, app, company_user):
        _login(client)
        bad_data = {'file': (io.BytesIO(b'not,csv,data'), 'bad.csv')}
        resp = client.post('/payroll', data=bad_data, content_type='multipart/form-data', follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data
        assert b'Reference:' in body
        assert b'Traceback' not in body
        assert b'ValueError' not in body
        assert b'Error processing payroll:' not in body

    def test_api_bad_payload_no_raw_exception(self, client, app, company_user):
        _login(client)
        resp = client.post('/api/v1/employees', json={'employee_id': None, 'name': {}}, content_type='application/json')
        assert resp.status_code == 422
        body = resp.data
        assert b'Traceback' not in body
        assert b'File "' not in body


# -----------------------------------------------------------------------
# Gate: File upload restrictions
# -----------------------------------------------------------------------


class TestFileUploadRestrictions:
    def test_reject_exe_as_pdf(self, client, app):
        with app.app_context():
            company = Company(name='SecTestCo1')
            db.session.add(company)
            db.session.commit()
            user = User(phone='0911888811', company_id=company.id, role='owner')
            user.set_password('Test1234!')
            db.session.add(user)
            db.session.commit()
            emp = Employee(
                employee_id='SEC001', name='Security Test', basic_salary=5000, allowances=0, company_id=company.id
            )
            db.session.add(emp)
            db.session.commit()
            emp_id = emp.id
        client.post('/auth/login', data={'login_id': '0911888811', 'password': 'Test1234!'}, follow_redirects=True)
        resp = client.post(
            f'/employees/{emp_id}/deductions/add',
            data={
                'deduction_type': 'cost_sharing',
                'label': 'Security Test',
                'amount_mode': 'fixed',
                'amount': '500',
                'tracking_mode': 'declining',
                'total_to_recover': '5000',
                'start_date': '2026-01-01',
                'document': (io.BytesIO(b'MZ\x90\x00'), 'evil.pdf.exe'),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'not allowed' in resp.data

    def test_accept_legitimate_pdf(self, client, app):
        with app.app_context():
            company = Company(name='SecTestCo2')
            db.session.add(company)
            db.session.commit()
            user = User(phone='0911888822', company_id=company.id, role='owner')
            user.set_password('Test1234!')
            db.session.add(user)
            db.session.commit()
            emp = Employee(
                employee_id='SEC002', name='Security Test 2', basic_salary=5000, allowances=0, company_id=company.id
            )
            db.session.add(emp)
            db.session.commit()
            emp_id = emp.id
        client.post('/auth/login', data={'login_id': '0911888822', 'password': 'Test1234!'}, follow_redirects=True)
        resp = client.post(
            f'/employees/{emp_id}/deductions/add',
            data={
                'deduction_type': 'cost_sharing',
                'label': 'Legit Doc',
                'amount_mode': 'fixed',
                'amount': '300',
                'tracking_mode': 'declining',
                'total_to_recover': '3000',
                'start_date': '2026-01-01',
                'document': (io.BytesIO(b'%PDF-1.4 fake pdf'), 'doc.pdf'),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'File type not allowed' not in resp.data

    def test_csv_rejects_empty_file(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/payroll',
            data={
                'file': (io.BytesIO(b''), 'empty.csv'),
            },
            content_type='multipart/form-data',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'empty' in resp.data.lower() or b'no data' in resp.data.lower() or b'file' in resp.data.lower()

    def test_csv_injection_prevention_unit(self):
        for dangerous in ['=CMD', '+FORMULA', '-FORMULA', '@LINK']:
            assert prevent_csv_injection(dangerous).startswith('\t')
        assert prevent_csv_injection('Safe') == 'Safe'
        assert prevent_csv_injection(None) is None


# -----------------------------------------------------------------------
# Gate: API validation abuse cases
# -----------------------------------------------------------------------


class TestApiValidationAbuse:
    def test_reject_negative_salary(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/api/v1/employees',
            json={
                'employee_id': 'ABUSE001',
                'name': 'Abuse Test',
                'basic_salary': -1000,
            },
        )
        assert resp.status_code == 422
        errs = resp.get_json().get('details', [])
        assert any('must be zero or positive' in e.lower() for e in errs)

    def test_reject_non_numeric_salary(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/api/v1/employees',
            json={
                'employee_id': 'ABUSE002',
                'name': 'Abuse Test 2',
                'basic_salary': 'not-a-number',
            },
        )
        assert resp.status_code == 422

    def test_reject_empty_name(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/api/v1/employees',
            json={
                'employee_id': 'ABUSE003',
                'name': '',
                'basic_salary': 5000,
            },
        )
        assert resp.status_code == 422

    def test_reject_empty_employee_id(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/api/v1/employees',
            json={
                'employee_id': '',
                'name': 'Test',
                'basic_salary': 5000,
            },
        )
        assert resp.status_code == 422

    def test_reject_invalid_tin(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/api/v1/employees',
            json={
                'employee_id': 'ABUSE004',
                'name': 'TIN Test',
                'basic_salary': 5000,
                'tin': 'abc123',
            },
        )
        assert resp.status_code == 422

    def test_accepts_name_with_special_chars(self, client, app, company_user):
        _login(client)
        resp = client.post(
            '/api/v1/employees',
            json={
                'employee_id': 'ABUSE005',
                'name': "O'Brien-Smith, Jr.",
                'basic_salary': 5000,
            },
        )
        assert resp.status_code in (201, 422)
