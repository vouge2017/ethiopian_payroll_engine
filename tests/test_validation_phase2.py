"""
Tests for Phase 2 validation checks:
1. Payroll variance (>20% change from last month)
2. Salary change 30% detection
3. Pending unpaid leave impact
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date, timedelta

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, Leave,
)
from payroll_engine.validation import (
    validate_payroll_data, get_summary,
    _check_salary_change_significant,
    _check_payroll_variance,
    _check_pending_leave_impact,
    ValidationResult,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _setup_company(app):
    with app.app_context():
        company = Company(name='ValidTestCo')
        db.session.add(company)
        db.session.flush()

        user = User(phone='0910000000', role='owner', company_id=company.id)
        user.set_password('TestPass1!')
        db.session.add(user)
        db.session.commit()

        return company.id, user.id


def _create_employee(app, company_id, emp_id='EMP001', name='Abebe', salary=10000, allowances=2000):
    with app.app_context():
        emp = Employee(
            employee_id=emp_id, name=name,
            basic_salary=salary, allowances=allowances,
            company_id=company_id,
        )
        db.session.add(emp)
        db.session.commit()
        return emp.id, emp.employee_id


def _create_completed_run(app, company_id, employees_data):
    """Create a completed payroll run with payslips."""
    with app.app_context():
        run = PayrollRun(
            company_id=company_id,
            run_date=date.today() - timedelta(days=30),
            status='completed',
        )
        run.generate_period()
        db.session.add(run)
        db.session.flush()
        run.generate_reference()

        for emp_data in employees_data:
            emp_obj = Employee.query.filter_by(
                employee_id=emp_data['id'], company_id=company_id
            ).first()
            if emp_obj:
                payslip = Payslip(
                    payroll_run_id=run.id,
                    employee_id=emp_obj.id,
                    gross_salary=emp_data.get('gross', 12000),
                    tax=emp_data.get('tax', 1500),
                    employee_pension=emp_data.get('pension', 700),
                    employer_pension=emp_data.get('pension_employer', 1100),
                    net_pay=emp_data.get('net', 9800),
                )
                db.session.add(payslip)

        db.session.commit()
        return run.id


# ─── Salary Change 30% ───


class TestSalaryChange30Percent:
    """Test _check_salary_change_significant."""

    def test_no_flag_when_change_under_30pct(self, app):
        _setup_company(app)
        previous = {'EMP001': {'basic': 10000, 'allowances': 2000}}
        data = [{'id': 'EMP001', 'name': 'Abebe', 'basic': 12000, 'allowances': 2000}]
        results = []
        _check_salary_change_significant(data, previous, results)
        assert len(results) == 0

    def test_flag_when_change_over_30pct(self, app):
        _setup_company(app)
        previous = {'EMP001': {'basic': 10000, 'allowances': 2000}}
        data = [{'id': 'EMP001', 'name': 'Abebe', 'basic': 15000, 'allowances': 2000}]
        results = []
        _check_salary_change_significant(data, previous, results)
        assert len(results) == 1
        assert results[0].rule_code == 'SALARY_CHANGE_30PCT'
        assert '42%' in results[0].message
        assert results[0].severity == 'FLAG'

    def test_flag_when_salary_decreased_30pct(self, app):
        _setup_company(app)
        previous = {'EMP001': {'basic': 10000, 'allowances': 2000}}
        data = [{'id': 'EMP001', 'name': 'Abebe', 'basic': 5000, 'allowances': 2000}]
        results = []
        _check_salary_change_significant(data, previous, results)
        assert len(results) == 1
        assert 'decreased' in results[0].message

    def test_no_flag_for_new_employee(self, app):
        _setup_company(app)
        previous = {'EMP001': {'basic': 10000, 'allowances': 2000}}
        data = [{'id': 'EMP002', 'name': 'New Person', 'basic': 8000, 'allowances': 1000}]
        results = []
        _check_salary_change_significant(data, previous, results)
        assert len(results) == 0

    def test_no_flag_when_no_previous(self, app):
        _setup_company(app)
        data = [{'id': 'EMP001', 'name': 'Abebe', 'basic': 15000, 'allowances': 2000}]
        results = []
        _check_salary_change_significant(data, None, results)
        assert len(results) == 0

    def test_no_flag_when_previous_zero(self, app):
        _setup_company(app)
        previous = {'EMP001': {'basic': 0, 'allowances': 0}}
        data = [{'id': 'EMP001', 'name': 'Abebe', 'basic': 10000, 'allowances': 2000}]
        results = []
        _check_salary_change_significant(data, previous, results)
        assert len(results) == 0

    def test_exactly_30pct_not_flagged(self, app):
        """30% is the threshold — exactly 30% should NOT be flagged."""
        _setup_company(app)
        previous = {'EMP001': {'basic': 10000, 'allowances': 0}}
        data = [{'id': 'EMP001', 'name': 'Abebe', 'basic': 13000, 'allowances': 0}]
        results = []
        _check_salary_change_significant(data, previous, results)
        assert len(results) == 0


# ─── Payroll Variance ───


class TestPayrollVariance:
    """Test _check_payroll_variance."""

    def test_no_flag_when_no_previous_run(self, app):
        cid, uid = _setup_company(app)
        data = [{'id': 'EMP001', 'name': 'Abebe', 'net': 10000}]
        results = []
        _check_payroll_variance(data, cid, results)
        assert len(results) == 0

    def test_no_flag_when_change_under_20pct(self, app):
        cid, uid = _setup_company(app)
        _create_employee(app, cid, 'EMP001', 'Abebe', 10000, 2000)
        _create_completed_run(app, cid, [{'id': 'EMP001', 'net': 10000}])

        data = [{'id': 'EMP001', 'name': 'Abebe', 'net': 11000}]
        results = []
        _check_payroll_variance(data, cid, results)
        assert len(results) == 0

    def test_flag_when_increase_over_20pct(self, app):
        cid, uid = _setup_company(app)
        _create_employee(app, cid, 'EMP001', 'Abebe', 10000, 2000)
        _create_completed_run(app, cid, [{'id': 'EMP001', 'net': 10000}])

        data = [{'id': 'EMP001', 'name': 'Abebe', 'net': 13000}]
        results = []
        _check_payroll_variance(data, cid, results)
        assert len(results) == 1
        assert results[0].rule_code == 'PAYROLL_VARIANCE'
        assert 'increased' in results[0].message
        assert '30%' in results[0].message

    def test_flag_when_decrease_over_20pct(self, app):
        cid, uid = _setup_company(app)
        _create_employee(app, cid, 'EMP001', 'Abebe', 10000, 2000)
        _create_completed_run(app, cid, [{'id': 'EMP001', 'net': 10000}])

        data = [{'id': 'EMP001', 'name': 'Abebe', 'net': 7000}]
        results = []
        _check_payroll_variance(data, cid, results)
        assert len(results) == 1
        assert 'decreased' in results[0].message

    def test_no_flag_when_company_id_none(self, app):
        _setup_company(app)
        data = [{'id': 'EMP001', 'name': 'Abebe', 'net': 10000}]
        results = []
        _check_payroll_variance(data, None, results)
        assert len(results) == 0


# ─── Pending Unpaid Leave ───


class TestPendingUnpaidLeave:
    """Test _check_pending_leave_impact."""

    def test_no_flag_when_no_unpaid_leave(self, app):
        cid, uid = _setup_company(app)
        emp_id, emp_eid = _create_employee(app, cid)
        data = [{'id': emp_eid, 'name': 'Abebe', 'basic': 10000}]
        results = []
        _check_pending_leave_impact(data, cid, results)
        assert len(results) == 0

    def test_flag_when_unpaid_leave_this_month(self, app):
        cid, uid = _setup_company(app)
        emp_id, emp_eid = _create_employee(app, cid)

        today = date.today()
        with app.app_context():
            leave = Leave(
                company_id=cid, employee_id=emp_id,
                leave_type='unpaid', status='approved',
                start_date=today.replace(day=5),
                end_date=today.replace(day=10),
                days_requested=6,
            )
            db.session.add(leave)
            db.session.commit()

        data = [{'id': emp_eid, 'name': 'Abebe', 'basic': 10000}]
        results = []
        _check_pending_leave_impact(data, cid, results)
        assert len(results) == 1
        assert results[0].rule_code == 'PENDING_UNPAID_LEAVE'
        assert '6 days' in results[0].message
        assert results[0].severity == 'FLAG'

    def test_no_flag_when_leave_is_paid_type(self, app):
        cid, uid = _setup_company(app)
        emp_id, emp_eid = _create_employee(app, cid)

        today = date.today()
        with app.app_context():
            leave = Leave(
                company_id=cid, employee_id=emp_id,
                leave_type='annual', status='approved',
                start_date=today.replace(day=5),
                end_date=today.replace(day=10),
                days_requested=6,
            )
            db.session.add(leave)
            db.session.commit()

        data = [{'id': emp_eid, 'name': 'Abebe', 'basic': 10000}]
        results = []
        _check_pending_leave_impact(data, cid, results)
        assert len(results) == 0

    def test_no_flag_when_leave_is_pending(self, app):
        cid, uid = _setup_company(app)
        emp_id, emp_eid = _create_employee(app, cid)

        today = date.today()
        with app.app_context():
            leave = Leave(
                company_id=cid, employee_id=emp_id,
                leave_type='unpaid', status='pending',
                start_date=today.replace(day=5),
                end_date=today.replace(day=10),
                days_requested=6,
            )
            db.session.add(leave)
            db.session.commit()

        data = [{'id': emp_eid, 'name': 'Abebe', 'basic': 10000}]
        results = []
        _check_pending_leave_impact(data, cid, results)
        assert len(results) == 0

    def test_no_flag_when_leave_last_month(self, app):
        cid, uid = _setup_company(app)
        emp_id, emp_eid = _create_employee(app, cid)

        today = date.today()
        last_month = (today.replace(day=1) - timedelta(days=1))
        with app.app_context():
            leave = Leave(
                company_id=cid, employee_id=emp_id,
                leave_type='unpaid', status='approved',
                start_date=last_month.replace(day=1),
                end_date=last_month.replace(day=5),
                days_requested=5,
            )
            db.session.add(leave)
            db.session.commit()

        data = [{'id': emp_eid, 'name': 'Abebe', 'basic': 10000}]
        results = []
        _check_pending_leave_impact(data, cid, results)
        assert len(results) == 0


# ─── Integration with validate_payroll_data ───


class TestValidationIntegration:
    """Test that new checks are wired into validate_payroll_data."""

    def test_salary_change_appears_in_full_validation(self, app):
        cid, uid = _setup_company(app)
        _create_employee(app, cid, 'EMP001', 'Abebe', 10000, 2000)
        _create_completed_run(app, cid, [{'id': 'EMP001', 'net': 10000}])

        from payroll_engine.services.payroll_workflow import get_previous_payslips
        previous = get_previous_payslips(cid)

        data = [{
            'id': 'EMP001', 'name': 'Abebe', 'basic': 15000, 'allowances': 2000,
            'gross': 17000, 'tax': 2500, 'pension_employee': 1050, 'net': 13450,
            'bank': 'cbe:1000123456789', 'tin': '1234567890',
        }]
        results = validate_payroll_data(data, company_id=cid, previous_payslips=previous)

        rule_codes = [r.rule_code for r in results]
        assert 'SALARY_CHANGE_30PCT' in rule_codes

    def test_payroll_variance_appears_in_full_validation(self, app):
        cid, uid = _setup_company(app)
        _create_employee(app, cid, 'EMP001', 'Abebe', 10000, 2000)
        _create_completed_run(app, cid, [{'id': 'EMP001', 'net': 10000}])

        data = [{
            'id': 'EMP001', 'name': 'Abebe', 'basic': 10000, 'allowances': 2000,
            'gross': 12000, 'tax': 1500, 'pension_employee': 700, 'net': 13000,
            'bank': 'cbe:1000123456789', 'tin': '1234567890',
        }]
        results = validate_payroll_data(data, company_id=cid)

        rule_codes = [r.rule_code for r in results]
        assert 'PAYROLL_VARIANCE' in rule_codes
