"""
Audit log tests — verifies employee changes are logged.

Tests:
- Employee creation is logged
- Salary changes are logged
- Bank account changes are logged
- Audit log is append-only (no edit/delete routes)
- Audit log page renders
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from payroll_engine import create_app, db
from payroll_engine.models import User, Company, Employee, AuditLog, TenantQuery


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(AuditLog)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def owner_and_company(app):
    """Create a company and owner user."""
    with app.app_context():
        company = Company(name='Test PLC')
        db.session.add(company)
        db.session.flush()
        user = User(phone='0911000000', role='owner', company_id=company.id)
        user.set_password('test123')
        db.session.add(user)
        db.session.commit()
        return user.id, company.id


def _login(client, phone='0911000000', password='test123'):
    return client.post('/auth/login', data={
        'login_id': phone,
        'password': password,
    }, follow_redirects=True)


def test_employee_creation_logged(app, client, owner_and_company):
    """Adding an employee creates an AuditLog entry."""
    uid, cid = owner_and_company
    _login(client)

    client.post('/employees/add', data={
        'name': 'Dawit Mekonnen',
        'phone': '0911223344',
        'basic_salary': 15000,
        'allowances': 3000,
    }, follow_redirects=True)

    with app.app_context():
        logs = AuditLog.query.filter_by(
            company_id=cid, action='employee_added'
        ).all()
        assert len(logs) == 1
        assert logs[0].details['name'] == 'Dawit Mekonnen'


def test_salary_change_logged(app, client, owner_and_company):
    """Changing salary logs 'salary_changed' to audit trail."""
    uid, cid = owner_and_company
    _login(client)

    # Create employee
    client.post('/employees/add', data={
        'name': 'Tigist Alemu',
        'basic_salary': 10000,
        'allowances': 2000,
    }, follow_redirects=True)

    with app.app_context():
        emp = Employee.query.filter_by(company_id=cid).first()
        emp_id = emp.id

    # Edit salary
    client.post(f'/employees/{emp_id}/edit', data={
        'name': 'Tigist Alemu',
        'basic_salary': 15000,
        'allowances': 2000,
    }, follow_redirects=True)

    with app.app_context():
        logs = AuditLog.query.filter_by(
            company_id=cid, action='salary_changed'
        ).all()
        assert len(logs) == 1
        assert logs[0].details['old_basic'] == 10000
        assert logs[0].details['new_basic'] == 15000
        assert logs[0].details['employee_name'] == 'Tigist Alemu'


def test_bank_account_change_logged(app, client, owner_and_company):
    """Changing bank account logs 'bank_account_changed' to audit trail."""
    uid, cid = owner_and_company
    _login(client)

    # Create employee with bank
    client.post('/employees/add', data={
        'name': 'Abebe Kebede',
        'basic_salary': 12000,
        'bank_account': 'cbe:1000123456789',
    }, follow_redirects=True)

    with app.app_context():
        emp = Employee.query.filter_by(company_id=cid).first()
        emp_id = emp.id

    # Change bank
    client.post(f'/employees/{emp_id}/edit', data={
        'name': 'Abebe Kebede',
        'basic_salary': 12000,
        'bank_account': 'telebirr:0911234567',
    }, follow_redirects=True)

    with app.app_context():
        logs = AuditLog.query.filter_by(
            company_id=cid, action='bank_account_changed'
        ).all()
        assert len(logs) == 1
        assert 'cbe:1000123456789' in logs[0].details['old']
        assert 'telebirr:0911234567' in logs[0].details['new']


def test_no_change_no_log(app, client, owner_and_company):
    """Editing without actual changes does not create audit entries."""
    uid, cid = owner_and_company
    _login(client)

    client.post('/employees/add', data={
        'name': 'Hana Tesfaye',
        'basic_salary': 8000,
    }, follow_redirects=True)

    with app.app_context():
        emp = Employee.query.filter_by(company_id=cid).first()
        emp_id = emp.id
        # Clear the employee_added log
        AuditLog.query.filter_by(company_id=cid).delete()
        db.session.commit()

    # Edit with same data
    client.post(f'/employees/{emp_id}/edit', data={
        'name': 'Hana Tesfaye',
        'basic_salary': 8000,
    }, follow_redirects=True)

    with app.app_context():
        logs = AuditLog.query.filter_by(company_id=cid).all()
        assert len(logs) == 0


def test_audit_log_page_renders(app, client, owner_and_company):
    """Audit log page renders and shows entries."""
    uid, cid = owner_and_company
    _login(client)

    # Create an employee to generate a log entry
    client.post('/employees/add', data={
        'name': 'Test User',
        'basic_salary': 5000,
    }, follow_redirects=True)

    resp = client.get('/audit-log')
    assert resp.status_code == 200
    assert b'Audit Log' in resp.data
    # Template replaces underscores with spaces
    assert b'employee added' in resp.data


def test_audit_log_no_edit_delete_routes(app):
    """There should be no routes to edit or delete audit log entries."""
    with app.app_context():
        url_rules = [rule.rule for rule in app.url_map.iter_rules()]
        audit_edit_routes = [r for r in url_rules if 'audit' in r and ('edit' in r or 'delete' in r or 'remove' in r)]
        assert len(audit_edit_routes) == 0, f'Found audit edit/delete routes: {audit_edit_routes}'
