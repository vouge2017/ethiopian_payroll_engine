"""
Tests for dashboard_api.py — Dashboard API with trends and drill-down.

Run: python -m pytest tests/test_dashboard_api.py -v
"""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.dashboard_api import (
    get_dashboard_data, DashboardResponse, Metric, Widget,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_user(user_id=1, role='owner'):
    user = MagicMock()
    user.id = user_id
    user.role = role
    user.get_role_for_company = MagicMock(return_value=role)
    return user


def _make_company(company_id=1, name='Test PLC'):
    company = MagicMock()
    company.id = company_id
    company.name = name
    return company


def _make_run(run_id=1, period='2018-10', status='completed'):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.status = status
    run.run_date = date(2026, 8, 1)
    return run


def _make_payslip(emp_id, gross=10000, tax=1500, pension=700, net=7800):
    ps = MagicMock()
    ps.employee_id = emp_id
    ps.gross_salary = gross
    ps.tax = tax
    ps.employee_pension = pension
    ps.employer_pension = pension
    ps.net_pay = net
    return ps


def _make_employee(emp_id, name, dept='IT', phone='091', tin='123', bank='1000'):
    emp = MagicMock()
    emp.id = emp_id
    emp.name = name
    emp.department = dept
    emp.phone = phone
    emp.tin = tin
    emp.bank_or_telebirr = bank
    emp.is_deleted = False
    return emp


def _setup(company, run=None, prev_run=None, employees=None, payslips=None):
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Company
    mock_session = MagicMock()
    mock_session.get.return_value = company
    mock_db.session = mock_session

    # Runs
    runs = [r for r in [run, prev_run] if r is not None]
    mock_models.PayrollRun.query.filter_by.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = runs
    mock_models.PayrollRun.query.filter_by.return_value.filter.return_value.order_by.return_value.first.return_value = run

    # Employees
    mock_models.Employee.query.filter_by.return_value.all.return_value = employees or []
    mock_models.Employee.query.filter_by.return_value.first.return_value = None

    # Payslips
    mock_models.Payslip.query.filter_by.return_value.all.return_value = payslips or []

    # Leave
    mock_models.Leave.query.filter_by.return_value.count.return_value = 0

    return mock_db, mock_models


# ─────────────────────────────────────────────
# Tests: Owner metrics
# ─────────────────────────────────────────────

class TestOwnerMetrics:

    @patch('payroll_engine.dashboard_api.classify_exceptions')
    @patch('payroll_engine.dashboard_api.collect_evidence')
    @patch('payroll_engine.dashboard_api.compute_change_summary')
    def test_owner_gets_cost_metrics(self, mock_cs, mock_ev, mock_exc):
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], total=0, summary='')

        user = _make_user(role='owner')
        company = _make_company()
        run = _make_run()
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)

        mock_db, mock_models = _setup(company, run, employees=[emp], payslips=[ps])

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        assert 'metrics' in result
        metric_names = [m['name'] for m in result['metrics']]
        assert 'Total Payroll Cost' in metric_names
        assert 'Employees' in metric_names

    @patch('payroll_engine.dashboard_api.classify_exceptions')
    @patch('payroll_engine.dashboard_api.collect_evidence')
    @patch('payroll_engine.dashboard_api.compute_change_summary')
    def test_owner_cost_has_display(self, mock_cs, mock_ev, mock_exc):
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], total=0, summary='')

        user = _make_user(role='owner')
        company = _make_company()
        run = _make_run()
        ps = _make_payslip(1, gross=25000)

        mock_db, mock_models = _setup(company, run, payslips=[ps])

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        cost_metric = [m for m in result['metrics'] if m['name'] == 'Total Payroll Cost'][0]
        assert 'ETB' in cost_metric['display']
        assert '25,000' in cost_metric['display']


# ─────────────────────────────────────────────
# Tests: Accountant metrics
# ─────────────────────────────────────────────

class TestAccountantMetrics:

    @patch('payroll_engine.dashboard_api.classify_exceptions')
    @patch('payroll_engine.dashboard_api.collect_evidence')
    @patch('payroll_engine.dashboard_api.compute_change_summary')
    def test_accountant_gets_trust_metrics(self, mock_cs, mock_ev, mock_exc):
        mock_cs.return_value = MagicMock(gross_delta_pct=1.3, has_unusual_variance=False)
        mock_ev.return_value = MagicMock(passed=[MagicMock()], total=5, pass_rate=20.0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], total=2, summary='2 issue(s)')

        user = _make_user(role='accountant')
        company = _make_company()
        run = _make_run()

        mock_db, mock_models = _setup(company, run)

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        metric_names = [m['name'] for m in result['metrics']]
        assert 'Trust Evidence' in metric_names
        assert 'Blocking Issues' in metric_names


# ─────────────────────────────────────────────
# Tests: HR metrics
# ─────────────────────────────────────────────

class TestHRMetrics:

    @patch('payroll_engine.dashboard_api.classify_exceptions')
    @patch('payroll_engine.dashboard_api.collect_evidence')
    @patch('payroll_engine.dashboard_api.compute_change_summary')
    def test_hr_gets_people_metrics(self, mock_cs, mock_ev, mock_exc):
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], total=0, summary='')

        user = _make_user(role='hr')
        company = _make_company()
        run = _make_run()
        emp1 = _make_employee(1, 'Dawit', dept='IT')
        emp2 = _make_employee(2, 'Hana', dept='Finance')

        mock_db, mock_models = _setup(company, run, employees=[emp1, emp2])

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        metric_names = [m['name'] for m in result['metrics']]
        assert 'Total Employees' in metric_names
        assert 'Pending Leave' in metric_names


# ─────────────────────────────────────────────
# Tests: Trends
# ─────────────────────────────────────────────

class TestTrends:

    @patch('payroll_engine.dashboard_api.classify_exceptions')
    @patch('payroll_engine.dashboard_api.collect_evidence')
    @patch('payroll_engine.dashboard_api.compute_change_summary')
    def test_trends_populated(self, mock_cs, mock_ev, mock_exc):
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], total=0, summary='')

        user = _make_user(role='owner')
        company = _make_company()
        run1 = _make_run(1, '2018-10')
        run2 = _make_run(2, '2018-09')
        ps = _make_payslip(1)

        mock_db, mock_models = _setup(company, run1, run2, payslips=[ps])

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        assert 'trends' in result
        assert 'payroll_cost' in result['trends']


# ─────────────────────────────────────────────
# Tests: Widgets
# ─────────────────────────────────────────────

class TestWidgets:

    @patch('payroll_engine.dashboard_api.classify_exceptions')
    @patch('payroll_engine.dashboard_api.collect_evidence')
    @patch('payroll_engine.dashboard_api.compute_change_summary')
    def test_owner_gets_cost_widget(self, mock_cs, mock_ev, mock_exc):
        mock_cs.return_value = None
        mock_ev.return_value = MagicMock(passed=[], total=0)
        mock_exc.return_value = MagicMock(has_blocking=False, blocking_issues=[], total=0, summary='')

        user = _make_user(role='owner')
        company = _make_company()
        run = _make_run()
        emp = _make_employee(1, 'Dawit', dept='IT')
        ps = _make_payslip(1)

        mock_db, mock_models = _setup(company, run, employees=[emp], payslips=[ps])

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        assert 'widgets' in result
        widget_ids = [w['widget_id'] for w in result['widgets']]
        assert 'cost_breakdown' in widget_ids


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_invalid_company(self):
        user = _make_user()
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = None

        result = get_dashboard_data(user, 999, mock_db, mock_models)
        assert 'error' in result

    def test_no_runs(self):
        user = _make_user()
        company = _make_company()

        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = company
        mock_db.session = mock_session

        mock_models.PayrollRun.query.filter_by.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = get_dashboard_data(user, 1, mock_db, mock_models)

        assert any('No payroll' in item['title'] for item in result.get('attention_items', []))
