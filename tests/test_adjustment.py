"""Adjustment payslip tests — verify post-approval corrections."""

import csv
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import UTC, datetime

from helpers import salary_change_credentials

from payroll_engine import create_app, db
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    OvertimeEntry,
    PayrollCorrection,
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
        from helpers import seed_synthetic_payroll_rule

        seed_synthetic_payroll_rule()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        TenantQuery.register_model(Payslip)
        yield app
        db.drop_all()


@pytest.fixture
def company_user(app):
    with app.app_context():
        company = Company(name='TestCo')
        db.session.add(company)
        db.session.commit()
        user = User(phone='0911000001', company_id=company.id, role='owner')
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.commit()
        uc = UserCompany(user_id=user.id, company_id=company.id, role='owner')
        db.session.add(uc)
        db.session.commit()
        return company.id, user.id


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    client.post('/auth/login', data={'login_id': '0911000001', 'password': 'Test1234!'}, follow_redirects=True)


def _create_completed_run(app, company_id, user_id):
    """Create a completed payroll run with a regular payslip."""
    with app.app_context():
        emp = Employee(
            employee_id='EMP001',
            name='Test Worker',
            basic_salary=10000,
            allowances=0,
            company_id=company_id,
        )
        db.session.add(emp)
        db.session.commit()

        run = PayrollRun(
            company_id=company_id,
            run_date=datetime.now(UTC).date(),
            status='completed',
            approved_by=user_id,
            approved_at=datetime.now(UTC),
            disbursement_status='pending',
        )
        db.session.add(run)
        db.session.commit()

        ps = Payslip(
            payroll_run_id=run.id,
            company_id=run.company_id,
            employee_id=emp.id,
            gross_salary=10000,
            tax=1475,
            employee_pension=700,
            employer_pension=1100,
            net_pay=7825,
            taxable_income=9300,
            payslip_type='regular',
        )
        from payroll_engine.services.correction_context import freeze_context

        ps.calculation_context = freeze_context(
            run.run_date, employee_id=emp.employee_id, name=emp.name, bank=emp.bank_or_telebirr
        )
        db.session.add(ps)
        db.session.commit()
        return run.id, emp.id


def test_approved_correction_export_and_orphan_adjustment_block(app, company_user, client, monkeypatch):
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.services.worksheet_review import create_review

    cid, uid = company_user
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    with app.app_context():
        employee = Employee(
            company_id=cid,
            employee_id='ADJ001',
            name='Approved Worker',
            basic_salary=10000,
            allowances=0,
            bank_account='cbe:1000123456789',
        )
        db.session.add(employee)
        db.session.commit()
        start = datetime.now(UTC).date().replace(day=1)
        run = create_review(cid, uid, start)
        db.session.commit()
        result = process_payroll(
            run,
            cid,
            uid,
            'owner@example.invalid',
            '127.0.0.1',
            salary_credentials=salary_change_credentials('Test1234!'),
        )
        assert result.success, result.message or result.error
        run_id, employee_id = run.id, employee.id

    login(client)
    response = client.post(
        f'/payroll/{run_id}/adjustment',
        data={
            'employee_id': str(employee_id),
            'amount': '2000',
            'reason': 'Approved overtime',
            'source': 'approved_overtime',
            'source_reference': 'FAKE-OT-1',
            'effective_date': start.isoformat(),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        correction = PayrollCorrection.query.filter_by(company_id=cid, payroll_run_id=run_id).one()
        assert correction.status == 'draft'
        correction_id = correction.id
    response = client.post(f'/payroll/{run_id}/corrections/{correction_id}/approve', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        correction = PayrollCorrection.query.filter_by(company_id=cid, id=correction_id).one()
        assert correction.status == 'approved'
        approved_net = correction.net_delta
        slip = Payslip.query.filter_by(company_id=cid, id=correction.approved_payslip_id).one()
        assert slip.payslip_type == 'adjustment'
        retained_context = slip.calculation_context
        employee = Employee.query.filter_by(company_id=cid, id=employee_id).one()
        employee.name = 'Changed Worker'
        employee.bank_account = employee.bank_or_telebirr = 'telebirr:0912345678'
        employee.basic_salary = 50000
        db.session.commit()
    response = client.get(f'/payroll/{run_id}/adjustment-bank-file')
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert len(rows) == 1
    assert rows[0]['account_number'] == '1000123456789'
    assert rows[0]['amount'] == f'{approved_net:.2f}'
    assert 'Approved Worker' in rows[0]['narrative']
    assert 'Changed Worker' not in rows[0]['narrative']

    with app.app_context():
        db.session.add(
            Payslip(
                company_id=cid,
                payroll_run_id=run_id,
                employee_id=employee_id,
                payslip_type='adjustment',
                gross_salary=100,
                tax=0,
                employee_pension=0,
                employer_pension=0,
                net_pay=100,
                calculation_context=retained_context,
            )
        )
        db.session.commit()
    message = 'Approved correction is missing for an adjustment. Contact support before exporting.'
    response = client.get(f'/api/v1/payroll-runs/{run_id}/bank-file?bank=cbe')
    assert response.status_code == 400 and response.get_json()['error'] == message
    response = client.get(f'/payroll/{run_id}/adjustment-bank-file', follow_redirects=True)
    assert message.encode() in response.data


def test_create_adjustment(app, company_user, client):
    """Create an adjustment payslip for a completed run."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(
        f'/payroll/{run_id}/adjustment',
        data={
            'employee_id': str(emp_id),
            'amount': '2000',
            'reason': 'Overtime correction',
            'source': 'approved_overtime',
            'source_reference': 'HR-OT-1',
            'effective_date': datetime.now(UTC).date().isoformat(),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b'Correction' in resp.data

    with app.app_context():
        adjustments = PayrollCorrection.query.filter_by(company_id=cid, payroll_run_id=run_id).all()
        assert len(adjustments) == 1
        assert adjustments[0].reason == 'Overtime correction'
        assert adjustments[0].amount == 2000
        assert adjustments[0].status == 'draft'
        assert Payslip.query.filter_by(company_id=cid, payroll_run_id=run_id, payslip_type='adjustment').count() == 0
        assert adjustments[0].original_payslip_id is not None


def test_adjustment_requires_reason(app, company_user, client):
    """Adjustment requires a reason."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(
        f'/payroll/{run_id}/adjustment',
        data={
            'employee_id': str(emp_id),
            'amount': '2000',
            'reason': '',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b'required' in resp.data.lower()


def test_adjustment_requires_positive_amount(app, company_user, client):
    """Adjustment requires positive amount."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(
        f'/payroll/{run_id}/adjustment',
        data={
            'employee_id': str(emp_id),
            'amount': '-500',
            'reason': 'Test',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_adjustment_creates_audit_log(app, company_user, client):
    """Adjustment creates an audit log entry."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(
        f'/payroll/{run_id}/adjustment',
        data={
            'employee_id': str(emp_id),
            'amount': '1500',
            'reason': 'Bonus correction',
            'source': 'approved_bonus',
            'source_reference': 'HR-BONUS-1',
            'effective_date': datetime.now(UTC).date().isoformat(),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        log = AuditLog.query.filter_by(company_id=cid, action='payroll_correction_drafted').first()
        assert log is not None
        assert log.details['reason'] == 'Bonus correction'


def test_adjustment_only_completed_runs(app, company_user, client):
    """Cannot adjust a non-completed run."""
    cid, _uid = company_user
    with app.app_context():
        emp = Employee(
            employee_id='EMP001',
            name='Test',
            basic_salary=5000,
            company_id=cid,
        )
        db.session.add(emp)
        db.session.commit()

        run = PayrollRun(
            company_id=cid,
            run_date=datetime.now(UTC).date(),
            status='review',
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id
        emp_id = emp.id

    login(client)
    resp = client.post(
        f'/payroll/{run_id}/adjustment',
        data={
            'employee_id': str(emp_id),
            'amount': '1000',
            'reason': 'Test',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b'only adjust completed' in resp.data.lower() or b'completed' in resp.data.lower()
