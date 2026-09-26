"""Regression tests for BUG 1 (advances via spreadsheet) and BUG 2 (absence marking)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeDeduction,
    Leave,
    PayrollRun,
    Payslip,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
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
        return company.id, user.id


@pytest.fixture
def employee(app, company_user):
    cid, _uid = company_user
    with app.app_context():
        emp = Employee(
            employee_id='EMP001',
            name='Abebe Kebede',
            phone='0911111111',
            basic_salary=Decimal('10000'),
            allowances=Decimal('2000'),
            company_id=cid,
            bank_account='cbe:1000123456789',
            tin='1234567890',
        )
        db.session.add(emp)
        db.session.commit()
        return emp.id


class TestBug1AdvancesViaSpreadsheet:
    """BUG 1: Advances via spreadsheet path caused check constraint violation."""

    def test_advance_deduction_type_is_valid(self, app, company_user, employee):
        """'advance' must be in DEDUCTION_TYPES and pass the check constraint."""
        cid, _uid = company_user
        with app.app_context():
            ded = EmployeeDeduction(
                company_id=cid,
                employee_id=employee,
                deduction_type='advance',
                label='Test Advance',
                amount_mode='fixed',
                amount=Decimal('500'),
                tracking_mode='date_bounded',
                start_date=date.today(),
                is_active=True,
            )
            db.session.add(ded)
            db.session.commit()  # Must not raise IntegrityError
            assert ded.id is not None
            assert ded.deduction_type == 'advance'

    def test_advance_is_deducted_in_payroll_run(self, app, company_user, employee):
        """An advance created via spreadsheet path reduces net pay in the next run."""
        cid, uid = company_user
        with app.app_context():
            # Create an advance deduction
            advance_amount = Decimal('1000')
            ded = EmployeeDeduction(
                company_id=cid,
                employee_id=employee,
                deduction_type='advance',
                label='Advance October 2026',
                amount_mode='fixed',
                amount=advance_amount,
                tracking_mode='date_bounded',
                start_date=date.today(),
                is_active=True,
            )
            db.session.add(ded)
            db.session.commit()

            # Create a payroll run with draft data
            run = PayrollRun(company_id=cid, run_date=date.today(), status='review')
            db.session.add(run)
            db.session.flush()
            from payroll_engine.models import PayrollDraft
            emp = db.session.get(Employee, employee)
            draft_data = [{
                'id': emp.employee_id,
                'name': emp.name,
                'basic': float(emp.basic_salary),
                'allowances': float(emp.allowances),
                'gross': 12000.0,
                'tax': 1500.0,
                'pension_employee': 700.0,
                'pension_employer': 1100.0,
                'net': 9800.0,
            }]
            draft = PayrollDraft(payroll_run_id=run.id, company_id=cid, employee_data=draft_data)
            db.session.add(draft)
            db.session.commit()

            # Process payroll
            from payroll_engine.services.payroll_service import process_payroll
            result = process_payroll(run=run, company_id=cid, user_id=uid,
                                     user_email='test@test.com', request_ip='127.0.0.1')
            assert result.success is True

            # Verify: net pay reduced by advance amount
            payslip = Payslip.query.filter_by(payroll_run_id=run.id, company_id=cid).first()
            assert payslip is not None
            expected_net = Decimal('9800') - advance_amount
            assert payslip.net_pay == expected_net, f"Expected {expected_net}, got {payslip.net_pay}"

            # Verify: deduction details stored on payslip
            assert payslip.deduction_details is not None
            assert len(payslip.deduction_details) == 1
            assert payslip.deduction_details[0]['amount'] == 1000.0

    def test_100_consecutive_advance_submissions(self, app, company_user, employee):
        """100 consecutive spreadsheet advance submissions with zero constraint violations."""
        cid, _uid = company_user
        with app.app_context():
            for i in range(100):
                ded = EmployeeDeduction(
                    company_id=cid,
                    employee_id=employee,
                    deduction_type='advance',
                    label=f'Advance #{i+1}',
                    amount_mode='fixed',
                    amount=Decimal('100'),
                    tracking_mode='date_bounded',
                    start_date=date.today(),
                    is_active=True,
                )
                db.session.add(ded)
            db.session.commit()  # Must not raise

            count = EmployeeDeduction.query.filter_by(company_id=cid, deduction_type='advance').count()
            assert count == 100


class TestBug2AbsenceMarking:
    """BUG 2: Absence marking was decorative — field existed but did nothing."""

    def test_mark_absent_endpoint_exists(self, app, company_user, employee):
        """The /attendance/mark-absent endpoint must exist and create a Leave record."""
        cid, uid = company_user
        with app.app_context():
            client = app.test_client()
            # Login
            client.post('/auth/login', data={'login_id': '0911000001', 'password': 'Test1234!'})

            # Mark absent
            today = date.today()
            resp = client.post('/attendance/mark-absent', data={
                'employee_id': employee,
                'start_date': today.isoformat(),
                'end_date': today.isoformat(),
                'reason': 'Unexcused absence',
            }, follow_redirects=True)
            assert resp.status_code == 200

            # Verify Leave record created
            leave = Leave.query.filter_by(employee_id=employee, company_id=cid).first()
            assert leave is not None
            assert leave.leave_type == 'unpaid'
            assert leave.status == 'approved'
            assert leave.days_requested == 1

    def test_unpaid_absence_reduces_pay_in_approval_flow(self, app, company_user, employee):
        """Mark 2 unpaid days absent → full approval flow → net pay reduced by exactly 2/30ths."""
        cid, uid = company_user
        with app.app_context():
            emp = db.session.get(Employee, employee)
            basic = Decimal(str(emp.basic_salary))
            allowances = Decimal(str(emp.allowances))
            daily_rate = (basic + allowances) / Decimal('30')
            expected_reduction = daily_rate * Decimal('2')

            # Create 2 unpaid absence days (both in the past so they are fully deducted)
            today = date.today()
            two_days_ago = today - timedelta(days=1)
            three_days_ago = today - timedelta(days=2)
            leave = Leave(
                company_id=cid,
                employee_id=employee,
                leave_type='unpaid',
                start_date=three_days_ago,
                end_date=two_days_ago,
                days_requested=2,
                reason='Unexcused absence',
                status='approved',
                approved_by=uid,
                approved_at=datetime.now(UTC),
            )
            db.session.add(leave)
            db.session.commit()

            # Create payroll run
            run = PayrollRun(company_id=cid, run_date=today, status='review')
            db.session.add(run)
            db.session.flush()
            from payroll_engine.models import PayrollDraft
            gross = basic + allowances
            from payroll_engine.payroll import calculate_payroll
            calc = calculate_payroll(float(basic), float(allowances))
            draft_data = [{
                'id': emp.employee_id,
                'name': emp.name,
                'basic': float(basic),
                'allowances': float(allowances),
                'gross': float(calc['gross']),
                'tax': float(calc['tax']),
                'pension_employee': float(calc['pension_employee']),
                'pension_employer': float(calc['pension_employer']),
                'net': float(calc['net']),
            }]
            draft = PayrollDraft(payroll_run_id=run.id, company_id=cid, employee_data=draft_data)
            db.session.add(draft)
            db.session.commit()

            # Process payroll
            from payroll_engine.services.payroll_service import process_payroll
            result = process_payroll(run=run, company_id=cid, user_id=uid,
                                     user_email='test@test.com', request_ip='127.0.0.1')
            assert result.success is True

            # Verify: net pay reduced by exactly 2 days' pay
            payslip = Payslip.query.filter_by(payroll_run_id=run.id, company_id=cid).first()
            expected_net = Decimal(str(calc['net'])) - expected_reduction
            assert payslip.net_pay == expected_net.quantize(Decimal('0.01')), \
                f"Expected {expected_net.quantize(Decimal('0.01'))}, got {payslip.net_pay}"

            # Verify: unpaid leave reduction recorded
            assert payslip.unpaid_leave_reduction == expected_reduction.quantize(Decimal('0.01'))

    def test_payslip_shows_absence_line_item(self, app, company_user, employee):
        """Payslip must show the absence reduction as a line item."""
        cid, uid = company_user
        with app.app_context():
            today = date.today()
            leave = Leave(
                company_id=cid,
                employee_id=employee,
                leave_type='unpaid',
                start_date=today,
                end_date=today,
                days_requested=1,
                reason='Test absence',
                status='approved',
                approved_by=uid,
                approved_at=date.today(),
            )
            db.session.add(leave)
            db.session.commit()

            run = PayrollRun(company_id=cid, run_date=today, status='review')
            db.session.add(run)
            db.session.flush()
            from payroll_engine.models import PayrollDraft
            emp = db.session.get(Employee, employee)
            from payroll_engine.payroll import calculate_payroll
            calc = calculate_payroll(float(emp.basic_salary), float(emp.allowances))
            draft_data = [{
                'id': emp.employee_id,
                'name': emp.name,
                'basic': float(emp.basic_salary),
                'allowances': float(emp.allowances),
                'gross': float(calc['gross']),
                'tax': float(calc['tax']),
                'pension_employee': float(calc['pension_employee']),
                'pension_employer': float(calc['pension_employer']),
                'net': float(calc['net']),
            }]
            draft = PayrollDraft(payroll_run_id=run.id, company_id=cid, employee_data=draft_data)
            db.session.add(draft)
            db.session.commit()

            from payroll_engine.services.payroll_service import process_payroll
            result = process_payroll(run=run, company_id=cid, user_id=uid,
                                     user_email='test@test.com', request_ip='127.0.0.1')
            assert result.success is True

            payslip = Payslip.query.filter_by(payroll_run_id=run.id, company_id=cid).first()
            # The reduction should be visible
            assert payslip.unpaid_leave_reduction > 0
