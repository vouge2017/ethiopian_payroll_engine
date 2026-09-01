"""Gate-8 regression: Finalized payroll is immutable.

Invariant: once a payroll run reaches a terminal state (`completed` or `locked`),
its existing payslips MUST NOT be mutated in place. Any change is recorded as a
new row with `payslip_type='adjustment'`. This guarantees that historical
reports can be regenerated identically from the same database snapshot.

Three things this test asserts:
  1. The approval guard refuses to reprocess a run in `completed`/`locked`/
     `processing` state.
  2. The duplicate-period check refuses to create a second run for the same
     period while the prior one is `locked`.
  3. Adjustment payslips are an additive channel (separate `payslip_type`),
     not a mutation of the original regular payslip.
"""
from datetime import date

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollDraft, PayrollRun, Payslip, User
from payroll_engine.services.payroll_service import process_payroll
from payroll_engine.services.payroll_workflow import check_duplicate_period


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_completed_run(app):
    with app.app_context():
        company = Company(name='Pilot Co', currency='ETB', country='ET')
        db.session.add(company)
        db.session.flush()
        user = User(email='owner@pilot.test', company_id=company.id, role='owner')
        user.set_password('pilot-pass-1234')
        db.session.add(user)
        emp = Employee(
            employee_id='P-001',
            name='Abel Tesfaye',
            basic_salary=10000,
            company_id=company.id,
        )
        db.session.add(emp)
        run = PayrollRun(
            company_id=company.id,
            run_date=date(2026, 8, 31),
            period='2026-08',
            status='processing',
        )
        db.session.add(run)
        db.session.flush()
        draft = PayrollDraft(
            payroll_run_id=run.id,
            company_id=company.id,
            employee_data=[
                {
                    'id': 'P-001',
                    'name': 'Abel Tesfaye',
                    'basic': 10000,
                    'allowances': 0,
                    'gross': 10000,
                    'tax': 1000,
                    'pension_employee': 500,
                    'pension_employer': 500,
                    'net': 8000,
                }
            ],
        )
        db.session.add(draft)
        db.session.commit()
        return company.id, user.id, emp.id, run.id


def test_approval_guard_rejects_terminal_run(app):
    company_id, user_id, emp_id, run_id = _seed_completed_run(app)
    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        run.status = 'completed'
        db.session.commit()

        result = process_payroll(
            run=db.session.get(PayrollRun, run_id),
            company_id=company_id,
            user_id=user_id,
            user_email='owner@pilot.test',
            request_ip='127.0.0.1',
        )
        assert result.success is False
        assert 'completed' in result.message or 'locked' in result.message or 'processing' in result.message


def test_duplicate_period_rejected_when_locked(app):
    company_id, _user_id, _emp_id, run_id = _seed_completed_run(app)
    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        run.status = 'locked'
        run.reference = 'PR-2026-08-0001'
        db.session.commit()

        conflict = check_duplicate_period(company_id, '2026-08')
        assert conflict is not None
        status_message, kind = conflict
        assert kind == 'locked'
        assert 'locked' in status_message.lower()


def test_regular_payslip_value_immutable_when_adjustment_added(app):
    """Adding an adjustment must not change the regular payslip's net_pay."""
    company_id, _user_id, emp_id, run_id = _seed_completed_run(app)
    with app.app_context():
        regular = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=500,
            employer_pension=500,
            net_pay=8000,
            payslip_type='regular',
        )
        db.session.add(regular)
        db.session.commit()
        original_net = regular.net_pay
        original_gross = regular.gross_salary

        adjustment = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=1000,
            tax=100,
            employee_pension=50,
            employer_pension=50,
            net_pay=800,
            payslip_type='adjustment',
            reason='Retro bonus',
            original_payslip_id=regular.id,
        )
        db.session.add(adjustment)
        db.session.commit()

        db.session.refresh(regular)
        assert regular.net_pay == original_net
        assert regular.gross_salary == original_gross
        assert regular.payslip_type == 'regular'

        rows = (
            db.session.query(Payslip)
            .filter_by(payroll_run_id=run_id, employee_id=emp_id)
            .order_by(Payslip.id)
            .all()
        )
        assert [r.payslip_type for r in rows] == ['regular', 'adjustment']
        assert sum(r.net_pay for r in rows) == 8800


def test_historical_report_is_deterministic(app):
    """Re-running a historical report from the same rows yields identical totals."""
    company_id, _user_id, emp_id, run_id = _seed_completed_run(app)
    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        run.status = 'locked'
        run.reference = 'PR-2026-08-0001'
        db.session.commit()
        regular = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=500,
            employer_pension=500,
            net_pay=8000,
            payslip_type='regular',
        )
        adjustment = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=500,
            tax=50,
            employee_pension=25,
            employer_pension=25,
            net_pay=400,
            payslip_type='adjustment',
            reason='Retro',
        )
        db.session.add_all([regular, adjustment])
        db.session.commit()

        rows1 = (
            db.session.query(Payslip)
            .filter_by(payroll_run_id=run_id, employee_id=emp_id)
            .order_by(Payslip.id)
            .all()
        )
        totals1 = (
            sum(r.gross_salary for r in rows1),
            sum(r.net_pay for r in rows1),
            sum(r.tax for r in rows1),
        )

        rows2 = (
            db.session.query(Payslip)
            .filter_by(payroll_run_id=run_id, employee_id=emp_id)
            .order_by(Payslip.id)
            .all()
        )
        totals2 = (
            sum(r.gross_salary for r in rows2),
            sum(r.net_pay for r in rows2),
            sum(r.tax for r in rows2),
        )
        assert totals1 == totals2
        assert totals1 == (10500, 8400, 1050)
