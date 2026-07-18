"""
API delete employee tests.

Tests:
- Delete employee without history → 200 + AuditLog
- Delete employee with payroll history → 409 (IntegrityError)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Employee, Company, User, PayrollRun, Payslip,
    AuditLog, TenantQuery, OvertimeEntry
)
from datetime import date, datetime


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def company_user_employee(ctx):
    """Create company, user, and employee."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()
    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    emp = Employee(
        employee_id='EMP001', name='Dawit Mekonnen',
        basic_salary=10000, allowances=2000,
        company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, phone, password):
    return client.post('/auth/login', data={
        'login_id': phone, 'password': password
    }, follow_redirects=True)


def test_delete_employee_without_history(ctx, client, company_user_employee):
    """Delete employee without payroll history → 200 + AuditLog."""
    company, user, emp = company_user_employee
    login(client, '0911000001', 'Test1234!')

    resp = client.delete(f'/api/v1/employees/{emp.id}')
    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'Deleted'

    # Verify employee is gone
    assert db.session.get(Employee, emp.id) is None

    # Verify audit log
    log = AuditLog.query.filter_by(
        company_id=company.id, action='employee_deleted_api'
    ).first()
    assert log is not None
    assert log.details['employee_name'] == 'Dawit Mekonnen'


def test_delete_employee_with_history_returns_409(ctx, client, company_user_employee):
    """Delete employee with payroll history → 409 (IntegrityError)."""
    company, user, emp = company_user_employee
    login(client, '0911000001', 'Test1234!')

    # Create payroll history
    run = PayrollRun(company_id=company.id, run_date=date.today(), status='completed')
    db.session.add(run)
    db.session.commit()

    payslip = Payslip(
        payroll_run_id=run.id, employee_id=emp.id,
        gross_salary=12000, tax=500, employee_pension=700,
        employer_pension=1100, net_pay=10800
    )
    db.session.add(payslip)
    db.session.commit()

    # Try to delete — should fail with 409
    resp = client.delete(f'/api/v1/employees/{emp.id}')
    assert resp.status_code == 409
    assert 'payroll history' in resp.get_json()['error'].lower()

    # Employee should still exist
    assert db.session.get(Employee, emp.id) is not None
