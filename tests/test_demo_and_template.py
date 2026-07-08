"""
Tests for Demo Mode and CSV Template Download.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import csv
import io
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip,
    OvertimeEntry, TenantQuery
)
from payroll_engine.demo import create_demo_data


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(PayrollRun)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ================================================================
# DEMO MODE TESTS
# ================================================================

def test_demo_creates_company(ctx):
    """Demo creates a company marked as is_demo."""
    company, user, employees, run = create_demo_data()
    assert company is not None
    assert company.name == 'Sample Trading PLC'
    assert company.is_demo is True


def test_demo_creates_5_employees(ctx):
    """Demo creates exactly 5 employees."""
    company, user, employees, run = create_demo_data()
    assert len(employees) == 5
    emps = Employee.query.filter_by(company_id=company.id).all()
    assert len(emps) == 5


def test_demo_creates_user(ctx):
    """Demo creates an owner user with demo credentials."""
    company, user, employees, run = create_demo_data()
    assert user.phone == '0900000000'
    assert user.role == 'owner'
    assert user.check_password('demo123')


def test_demo_creates_payroll_run(ctx):
    """Demo creates a completed payroll run with payslips."""
    company, user, employees, run = create_demo_data()
    assert run.status == 'completed'
    assert run.company_id == company.id
    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    assert len(payslips) == 5


def test_demo_payslips_have_correct_amounts(ctx):
    """Demo payslips have non-zero amounts."""
    company, user, employees, run = create_demo_data()
    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    for ps in payslips:
        assert ps.gross_salary > 0
        assert ps.tax >= 0
        assert ps.employee_pension > 0
        assert ps.net_pay > 0
        assert ps.net_pay < ps.gross_salary  # Net should be less than gross


def test_demo_overtime_entry(ctx):
    """Demo includes overtime for Dawit."""
    company, user, employees, run = create_demo_data()
    dawit = Employee.query.filter_by(employee_id='EMP001', company_id=company.id).first()
    ot = OvertimeEntry.query.filter_by(employee_id=dawit.id, company_id=company.id).first()
    assert ot is not None
    assert ot.hours == 4
    assert ot.overtime_type == 'day'


def test_demo_user_can_login(client, ctx):
    """Demo user can log in via /demo route."""
    resp = client.get('/demo', follow_redirects=True)
    assert resp.status_code == 200
    # Should see the demo banner
    assert b'DEMO MODE' in resp.data or b'demo' in resp.data.lower()


def test_demo_dashboard_shows_data(client, ctx):
    """After demo, dashboard shows employee count and payroll data."""
    client.get('/demo', follow_redirects=True)
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'5' in resp.data  # 5 employees


# ================================================================
# CSV TEMPLATE TESTS
# ================================================================

def test_csv_template_download(ctx, client):
    """CSV template download returns a valid CSV file."""
    # Register and login first
    client.post('/auth/register', data={
        'company_name': 'TestCo', 'phone': '0911123456',
        'password': 'TestPass123!', 'password2': 'TestPass123!',
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'login_id': '0911123456', 'password': 'TestPass123!',
    }, follow_redirects=True)

    resp = client.get('/payroll/template')
    assert resp.status_code == 200
    assert resp.content_type.startswith('text/csv')
    assert 'payroll_template.csv' in resp.headers.get('Content-Disposition', '')


def test_csv_template_has_headers(ctx, client):
    """CSV template contains correct headers."""
    client.post('/auth/register', data={
        'company_name': 'TestCo', 'phone': '0911123456',
        'password': 'TestPass123!', 'password2': 'TestPass123!',
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'login_id': '0911123456', 'password': 'TestPass123!',
    }, follow_redirects=True)

    resp = client.get('/payroll/template')
    content = resp.data.decode('utf-8-sig')  # Handle BOM
    assert 'employee_id' in content
    assert 'name' in content
    assert 'basic_salary' in content
    assert 'allowances' in content


def test_csv_template_has_example_data(ctx, client):
    """CSV template contains example employee data."""
    client.post('/auth/register', data={
        'company_name': 'TestCo', 'phone': '0911123456',
        'password': 'TestPass123!', 'password2': 'TestPass123!',
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'login_id': '0911123456', 'password': 'TestPass123!',
    }, follow_redirects=True)

    resp = client.get('/payroll/template')
    content = resp.data.decode('utf-8-sig')
    assert 'Dawit Mekonnen' in content
    assert 'Hana Tesfaye' in content
    assert 'Kebede Alemu' in content


def test_csv_template_is_parseable(ctx, client):
    """CSV template can be parsed as valid CSV."""
    client.post('/auth/register', data={
        'company_name': 'TestCo', 'phone': '0911123456',
        'password': 'TestPass123!', 'password2': 'TestPass123!',
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'login_id': '0911123456', 'password': 'TestPass123!',
    }, follow_redirects=True)

    resp = client.get('/payroll/template')
    content = resp.data.decode('utf-8-sig')
    # Skip comment lines
    lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
    reader = csv.reader(io.StringIO('\n'.join(lines)))
    rows = list(reader)
    assert len(rows) >= 4  # header + 3 example rows


def test_csv_template_has_utf8_bom(ctx, client):
    """CSV template starts with UTF-8 BOM for Excel compatibility."""
    client.post('/auth/register', data={
        'company_name': 'TestCo', 'phone': '0911123456',
        'password': 'TestPass123!', 'password2': 'TestPass123!',
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'login_id': '0911123456', 'password': 'TestPass123!',
    }, follow_redirects=True)

    resp = client.get('/payroll/template')
    assert resp.data[:3] == b'\xef\xbb\xbf'  # UTF-8 BOM
