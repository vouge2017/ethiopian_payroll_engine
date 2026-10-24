"""Role-guard regression tests: API data-leak bug fix.

Locks in:
- GET employee/payroll-run endpoints are owner/accountant only
- download_payslip: non-staff users may only fetch their own payslip (404 otherwise)
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import date

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    OvertimeEntry,
    PayrollRun,
    Payslip,
    TenantQuery,
    User,
    UserCompany,
)


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
        co = Company(name='TestCo')
        db.session.add(co)
        db.session.flush()

        owner = User(phone='0911111111', company_id=co.id, role='owner')
        owner.set_password('Test1234!')

        accountant = User(phone='0914444444', company_id=co.id, role='accountant')
        accountant.set_password('Test1234!')

        employee_user = User(phone='0922222222', company_id=co.id, role='employee')
        employee_user.set_password('Test1234!')
        db.session.add_all([owner, accountant, employee_user])
        db.session.commit()

        for u, role in [(owner, 'owner'), (accountant, 'accountant'), (employee_user, 'employee')]:
            db.session.add(UserCompany(user_id=u.id, company_id=co.id, role=role))
        db.session.commit()

        linked_emp = Employee(
            employee_id='EMP001',
            name='Self Service',
            basic_salary=10000,
            company_id=co.id,
            user_id=employee_user.id,
        )
        other_emp = Employee(
            employee_id='EMP002',
            name='Other Worker',
            basic_salary=9000,
            company_id=co.id,
        )
        db.session.add_all([linked_emp, other_emp])
        db.session.commit()

        run = PayrollRun(company_id=co.id, run_date=date(2026, 7, 1), status='completed')
        db.session.add(run)
        db.session.commit()

        payslip = Payslip(
            payroll_run_id=run.id,
            employee_id=linked_emp.id,
            company_id=co.id,
            gross_salary=12000,
            tax=2000,
            employee_pension=700,
            employer_pension=1100,
            net_pay=9300,
        )
        db.session.add(payslip)
        db.session.commit()

        pdf_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(pdf_dir, 'payslip.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4 test')
        payslip.pdf_file_path = pdf_path
        db.session.commit()

        yield {
            'co': co,
            'owner': owner,
            'accountant': accountant,
            'employee_user': employee_user,
            'linked_emp': linked_emp,
            'other_emp': other_emp,
            'run': run,
            'payslip': payslip,
        }


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, phone, password):
    return client.post('/auth/login', data={'login_id': phone, 'password': password}, follow_redirects=True)


def _as_employee(client):
    _login(client, '0922222222', 'Test1234!')


def _as_owner(client):
    _login(client, '0911111111', 'Test1234!')


def _as_accountant(client):
    _login(client, '0914444444', 'Test1234!')


# --- Employee / payroll-run listing requires owner or accountant ---


@pytest.mark.parametrize(
    'path',
    ['/api/v1/employees', '/api/v1/employees/1', '/api/v1/payroll-runs', '/api/v1/payroll-runs/1'],
)
def test_staff_only_endpoints_forbidden_for_employee_role(client, ctx, path):
    _as_employee(client)
    resp = client.get(path)
    assert resp.status_code == 403


@pytest.mark.parametrize(
    'path',
    ['/api/v1/employees', '/api/v1/payroll-runs'],
)
def test_staff_only_endpoints_open_to_owner(client, ctx, path):
    _as_owner(client)
    resp = client.get(path)
    assert resp.status_code == 200


def test_staff_only_endpoints_open_to_accountant(client, ctx):
    _as_accountant(client)
    resp = client.get('/api/v1/employees')
    assert resp.status_code == 200


# --- Payslip download authorization ---


def test_employee_downloads_own_payslip(client, ctx):
    _as_employee(client)
    resp = client.get(f'/api/v1/payslips/{ctx["payslip"].id}/download')
    assert resp.status_code == 200
    assert resp.data.startswith(b'%PDF')


def test_employee_blocked_from_other_payslip_404(client, ctx):
    _as_employee(client)
    # Make the payslip belong to another (unlinked) employee
    ctx['payslip'].employee_id = ctx['other_emp'].id
    db.session.commit()
    resp = client.get(f'/api/v1/payslips/{ctx["payslip"].id}/download')
    assert resp.status_code == 404


def test_owner_downloads_any_payslip(client, ctx):
    _as_owner(client)
    ctx['payslip'].employee_id = ctx['other_emp'].id
    db.session.commit()
    resp = client.get(f'/api/v1/payslips/{ctx["payslip"].id}/download')
    assert resp.status_code == 200


def test_accountant_downloads_any_payslip(client, ctx):
    _as_accountant(client)
    ctx['payslip'].employee_id = ctx['other_emp'].id
    db.session.commit()
    resp = client.get(f'/api/v1/payslips/{ctx["payslip"].id}/download')
    assert resp.status_code == 200
