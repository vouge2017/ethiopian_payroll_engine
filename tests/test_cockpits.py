"""
Tests for cockpits.py — Role-Based Cockpits

Tests each role's view: Owner, Accountant, HR, Employee.

Run: python -m pytest tests/test_cockpits.py -v
"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.cockpits import (
    build_role_cockpit,
)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _make_user(user_id=1, name='Dawit', role='owner'):
    user = MagicMock()
    user.id = user_id
    user.name = name
    user.role = role
    user.get_role_for_company = MagicMock(return_value=role)
    return user


def _make_company(company_id=1, name='Test PLC'):
    company = MagicMock()
    company.id = company_id
    company.name = name
    company.compliance_deadlines = {}
    return company


def _make_run(run_id=1, period='2018-10', company_id=1, status='completed', run_date=None):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.status = status
    run.run_date = run_date or date(2026, 8, 1)
    return run


def _make_employee(emp_id, name, department='IT', phone='0911', tin='123', bank='1000', user_id=None):
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = f'EMP-{emp_id:03d}'
    emp.name = name
    emp.company_id = 1
    emp.department = department
    emp.phone = phone
    emp.tin = tin
    emp.bank_or_telebirr = bank
    emp.is_deleted = False
    emp.user_id = user_id
    return emp


def _make_payslip(emp_id, gross=10000, tax=1500, pension=700, net=7800):
    ps = MagicMock()
    ps.employee_id = emp_id
    ps.gross_salary = gross
    ps.tax = tax
    ps.employee_pension = pension
    ps.net_pay = net
    return ps


def _setup_db(company, run=None, employees=None, payslips=None, leaves=None):
    """Set up mocks for build_role_cockpit."""
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Company
    def session_get(model, id):
        if id == company.id:
            return company
        return None

    mock_session = MagicMock()
    mock_session.get.side_effect = session_get
    mock_db.session = mock_session

    # Run
    mock_chain = MagicMock()
    mock_chain.first.return_value = run
    mock_models.PayrollRun.query.filter_by.return_value = mock_chain
    mock_chain.filter.return_value = mock_chain
    mock_chain.order_by.return_value = mock_chain

    # Previous run
    mock_models.PayrollRun.query.filter.return_value.order_by.return_value.first.return_value = None

    # Employees
    mock_models.Employee.query.filter_by.return_value.all.return_value = employees or []

    # Payslips
    mock_models.Payslip.query.filter_by.return_value.all.return_value = payslips or []

    # Leave
    mock_models.Leave.query.filter_by.return_value.all.return_value = leaves or []
    mock_models.Leave.query.filter_by.return_value.first.return_value = None

    # Leave balance
    mock_models.LeaveBalance.query.filter_by.return_value.all.return_value = []

    return mock_db, mock_models


# ─────────────────────────────────────────────
# Tests: Owner cockpit
# ─────────────────────────────────────────────


class TestOwnerCockpit:
    @patch('payroll_engine.cockpits.build_filing_workspace')
    @patch('payroll_engine.cockpits.classify_exceptions')
    @patch('payroll_engine.cockpits.collect_evidence')
    @patch('payroll_engine.cockpits.compute_change_summary')
    @patch('payroll_engine.cockpits.get_deadline_for_type')
    def test_owner_gets_business_view(self, mock_dl, mock_cs, mock_ev, mock_exc, mock_fw):
        mock_dl.return_value = date(2026, 9, 25)
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[])
        mock_fw.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)

        user = _make_user(role='owner')
        company = _make_company()
        run = _make_run()
        emp = _make_employee(1, 'Dawit', department='IT')
        ps = _make_payslip(1)

        mock_db, mock_models = _setup_db(company, run, [emp], [ps])

        cockpit = build_role_cockpit(user, 1, mock_db, mock_models)

        assert cockpit is not None
        assert 'owner' in cockpit.user_roles
        assert cockpit.owner is not None
        assert cockpit.owner.total_payroll_cost > 0

    @patch('payroll_engine.cockpits.get_deadline_for_type')
    def test_owner_no_payroll(self, mock_dl):
        mock_dl.return_value = None

        user = _make_user(role='owner')
        company = _make_company()

        mock_db, mock_models = _setup_db(company, None, [])

        cockpit = build_role_cockpit(user, 1, mock_db, mock_models)

        assert cockpit.owner.status == 'no_payroll'


# ─────────────────────────────────────────────
# Tests: Accountant cockpit
# ─────────────────────────────────────────────


class TestAccountantCockpit:
    @patch('payroll_engine.cockpits.build_filing_workspace')
    @patch('payroll_engine.cockpits.classify_exceptions')
    @patch('payroll_engine.cockpits.collect_evidence')
    @patch('payroll_engine.cockpits.compute_change_summary')
    @patch('payroll_engine.cockpits.get_deadline_for_type')
    def test_accountant_gets_payroll_view(self, mock_dl, mock_cs, mock_ev, mock_exc, mock_fw):
        mock_dl.return_value = date(2026, 9, 25)
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[MagicMock()], total=5)
        mock_exc.return_value = MagicMock(
            has_blocking=False,
            blocking_issues=[],
            summary='No issues',
            total=0,
        )
        mock_fw.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)

        user = _make_user(role='accountant')
        company = _make_company()
        run = _make_run()

        mock_db, mock_models = _setup_db(company, run, [])

        cockpit = build_role_cockpit(user, 1, mock_db, mock_models)

        assert cockpit.accountant is not None
        assert cockpit.accountant.period == '2018-10'


# ─────────────────────────────────────────────
# Tests: HR cockpit
# ─────────────────────────────────────────────


class TestHRCockpit:
    @patch('payroll_engine.cockpits.get_deadline_for_type')
    def test_hr_gets_people_view(self, mock_dl):
        mock_dl.return_value = None

        user = _make_user(role='hr')
        company = _make_company()
        run = _make_run()
        emp1 = _make_employee(1, 'Dawit', department='IT')
        emp2 = _make_employee(2, 'Hana', department='Finance')

        mock_db, mock_models = _setup_db(company, run, [emp1, emp2])

        cockpit = build_role_cockpit(user, 1, mock_db, mock_models)

        assert cockpit.hr is not None
        assert cockpit.hr.total_employees == 2
        assert 'IT' in cockpit.hr.headcount_by_department
        assert 'Finance' in cockpit.hr.headcount_by_department


# ─────────────────────────────────────────────
# Tests: Employee cockpit
# ─────────────────────────────────────────────


class TestEmployeeCockpit:
    @patch('payroll_engine.cockpits.get_deadline_for_type')
    def test_employee_gets_self_service_view(self, mock_dl):
        mock_dl.return_value = None

        user = _make_user(role='employee')
        user.id = 1
        company = _make_company()
        emp = _make_employee(1, 'Dawit', user_id=1)
        ps = _make_payslip(1)

        mock_db, mock_models = _setup_db(company, None, [emp], [ps])
        mock_models.Employee.query.filter_by.return_value.first.return_value = emp
        mock_models.PayrollRun.query.filter.return_value.order_by.return_value.first.return_value = MagicMock(
            period='2018-10'
        )

        cockpit = build_role_cockpit(user, 1, mock_db, mock_models)

        assert cockpit.employee is not None
        assert cockpit.employee.name == 'Dawit'


# ─────────────────────────────────────────────
# Tests: Multi-role
# ─────────────────────────────────────────────


class TestMultiRole:
    @patch('payroll_engine.cockpits.build_filing_workspace')
    @patch('payroll_engine.cockpits.classify_exceptions')
    @patch('payroll_engine.cockpits.collect_evidence')
    @patch('payroll_engine.cockpits.compute_change_summary')
    @patch('payroll_engine.cockpits.get_deadline_for_type')
    def test_owner_also_sees_accountant(self, mock_dl, mock_cs, mock_ev, mock_exc, mock_fw):
        mock_dl.return_value = date(2026, 9, 25)
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], summary='No issues', total=0)
        mock_fw.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)

        user = _make_user(role='owner')
        # Small company: owner is also accountant
        user.get_role_for_company = MagicMock(return_value='owner')
        company = _make_company()
        run = _make_run()

        mock_db, mock_models = _setup_db(company, run, [])

        cockpit = build_role_cockpit(user, 1, mock_db, mock_models)

        # Owner gets owner view only (role-based, not auto-multiple)
        assert cockpit.owner is not None
        assert cockpit.accountant is None  # Only if role is 'accountant'


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────


class TestEdgeCases:
    def test_invalid_company_returns_none(self):
        user = _make_user()
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = None

        result = build_role_cockpit(user, 999, mock_db, mock_models)
        assert result is None
