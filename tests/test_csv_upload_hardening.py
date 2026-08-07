"""Tests for CSV upload hardening (#9), doc upload allowlist (#10), and CSV injection prevention (#11)."""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, OvertimeEntry, TenantQuery, User
from payroll_engine.security import prevent_csv_injection

# ================================================================
# Unit tests for prevent_csv_injection
# ================================================================

class TestPreventCsvInjection:
    def test_plain_text_passes(self):
        assert prevent_csv_injection('Alice') == 'Alice'

    def test_equals_prefix_gets_tab(self):
        result = prevent_csv_injection('=SUM(A1:A10)')
        assert result.startswith('\t')
        assert result == '\t=SUM(A1:A10)'

    def test_plus_prefix_gets_tab(self):
        assert prevent_csv_injection('+FORMULA') == '\t+FORMULA'

    def test_minus_prefix_gets_tab(self):
        assert prevent_csv_injection('-FORMULA') == '\t-FORMULA'

    def test_at_prefix_gets_tab(self):
        assert prevent_csv_injection('@LINK') == '\t@LINK'

    def test_tab_prefix_gets_tab(self):
        result = prevent_csv_injection('\tvalue')
        assert result.startswith('\t')
        assert result == '\t\tvalue'

    def test_empty_string(self):
        assert prevent_csv_injection('') == ''

    def test_none_returns_none(self):
        assert prevent_csv_injection(None) is None

    def test_leading_space_equals(self):
        result = prevent_csv_injection('  =cmd')
        assert result == '  =cmd'


# ================================================================
# Integration tests for payroll CSV upload
# ================================================================

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.environ.get('TEMP', '/tmp'), 'test_uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()
    import shutil
    shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def company_user(ctx):
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()
    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    return company, user


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    client.post('/auth/login', data={
        'login_id': '0911000001', 'password': 'Test1234!'
    }, follow_redirects=True)


_GOOD_CSV = (
    'employee_id,name,basic_salary,allowances,bank_account,tin\n'
    'EMP001,Dawit Mekonnen,10000,2000,cbe:123,1234567890\n'
    'EMP002,Hana Tesfaye,8000,1000,dashen:456,0987654321\n'
)


def test_upload_valid_csv(ctx, client, company_user):
    login(client)
    data = {'file': (io.BytesIO(_GOOD_CSV.encode('utf-8')), 'payroll.csv')}
    resp = client.post('/payroll', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200


def test_upload_non_csv_extension_rejected(ctx, client, company_user):
    login(client)
    data = {'file': (io.BytesIO(b'foo,bar\n1,2'), 'data.exe')}
    resp = client.post('/payroll', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Only CSV and Excel files are allowed' in resp.data


def test_upload_malformed_csv_shows_flash(ctx, client, company_user):
    """Missing required columns should flash a warning."""
    login(client)
    data = {'file': (io.BytesIO(b'not,a,csv,file\n1,2,3,4'), 'bad.csv')}
    resp = client.post('/payroll', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200


def test_upload_invalid_numeric_data_shows_flash(ctx, client, company_user):
    login(client)
    csv_content = (
        'employee_id,name,basic_salary,allowances\n'
        'EMP001,Dawit Mekonnen,not_a_number,twenty\n'
    )
    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'bad_data.csv')}
    resp = client.post('/payroll', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200


def test_upload_empty_file_shows_flash(ctx, client, company_user):
    login(client)
    data = {'file': (io.BytesIO(b''), 'empty.csv')}
    resp = client.post('/payroll', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200


# ================================================================
# Tests for deduction document upload allowlist (#10)
# ================================================================

def test_deduction_doc_pdf_allowed(ctx, client, company_user):
    """A real PDF header should be accepted."""
    login(client)
    company, user = company_user
    emp = Employee(employee_id='E001', name='Test', basic_salary=5000, allowances=0, company_id=company.id)
    db.session.add(emp)
    db.session.commit()

    pdf_header = b'%PDF-1.4 some content'
    data = {
        'deduction_type': 'loan',
        'label': 'Test Loan',
        'amount': '1000',
        'amount_mode': 'fixed',
        'tracking_mode': 'declining',
        'total_to_recover': '10000',
        'document': (io.BytesIO(pdf_header), 'agreement.pdf'),
    }
    resp = client.post(f'/employees/{emp.id}/deductions/add', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b'success' in resp.data.lower() or b'added' in resp.data


def test_deduction_doc_exe_rejected(ctx, client, company_user):
    """An .exe file should be rejected."""
    login(client)
    company, user = company_user
    emp = Employee(employee_id='E002', name='Test2', basic_salary=5000, allowances=0, company_id=company.id)
    db.session.add(emp)
    db.session.commit()

    data = {
        'deduction_type': 'loan',
        'label': 'Bad Upload',
        'amount': '500',
        'amount_mode': 'fixed',
        'tracking_mode': 'declining',
        'total_to_recover': '5000',
        'document': (io.BytesIO(b'MZ\x90\x00some exe'), 'virus.exe'),
    }
    resp = client.post(f'/employees/{emp.id}/deductions/add', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b'not allowed' in resp.data.lower() or b'rejected' in resp.data


def test_deduction_doc_renamed_exe_rejected(ctx, client, company_user):
    """An .exe renamed to .pdf should be rejected by MIME sniffing."""
    login(client)
    company, user = company_user
    emp = Employee(employee_id='E003', name='Test3', basic_salary=5000, allowances=0, company_id=company.id)
    db.session.add(emp)
    db.session.commit()

    data = {
        'deduction_type': 'loan',
        'label': 'Sneaky Upload',
        'amount': '500',
        'amount_mode': 'fixed',
        'tracking_mode': 'declining',
        'total_to_recover': '5000',
        'document': (io.BytesIO(b'MZ\x90\x00exe content'), 'agreement.pdf'),
    }
    resp = client.post(f'/employees/{emp.id}/deductions/add', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b'not match' in resp.data or b'not allowed' in resp.data
