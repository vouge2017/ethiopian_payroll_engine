"""
Tests for exceptions.py — Exception Intelligence

Tests issue classification by severity: Critical/High/Medium/Low.

Run: python -m pytest tests/test_exceptions.py -v
"""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.change_summary import ChangeSummary, EmployeeChange
from payroll_engine.exceptions import (
    CRITICAL,
    HIGH,
    LOW,
    MEDIUM,
    ExceptionReport,
    Issue,
    classify_exceptions,
)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _make_employee(emp_id, name, employee_id_str=None, bank='1000123456789', tin='1234567890', phone='0911234567'):
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = employee_id_str or f'EMP-{emp_id:03d}'
    emp.name = name
    emp.company_id = 1
    emp.bank_or_telebirr = bank
    emp.tin = tin
    emp.phone = phone
    return emp


def _make_payslip(emp_id, gross=10000, tax=1500, pension_emp=700, net=None, payslip_type='regular'):
    ps = MagicMock()
    ps.employee_id = emp_id
    ps.gross_salary = Decimal(str(gross))
    ps.tax = Decimal(str(tax))
    ps.employee_pension = Decimal(str(pension_emp))
    ps.net_pay = Decimal(str(net if net is not None else gross - tax - pension_emp))
    ps.payslip_type = payslip_type
    return ps


def _make_run(run_id=1, period='2018-10', company_id=1):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.status = 'completed'
    return run


def _setup_db(current_run, payslips, employees, previous_payslip_count=1):
    """Set up mocks for classify_exceptions."""
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Employee lookup map
    emp_map = {e.id: e for e in employees}

    # Current run
    def session_get(model, id):
        # Return employee if id matches, otherwise return the run
        return emp_map.get(id, current_run)

    mock_db.session.get.side_effect = session_get

    # Payslips
    mock_models.Payslip.query.filter_by.return_value.all.return_value = payslips
    mock_models.PayrollRun = MagicMock()

    # Previous payslip count (for new employee detection)
    mock_models.Payslip.query.join.return_value.filter.return_value.count.return_value = previous_payslip_count

    return mock_db, mock_models


def _make_change_summary(has_unusual_variance=False, variance_notes=None, salary_changes=None):
    return ChangeSummary(
        current_period='2018-10',
        previous_period='2018-09',
        current_employee_count=10,
        previous_employee_count=10,
        headcount_change=0,
        current_total_gross=Decimal('100000'),
        previous_total_gross=Decimal('100000'),
        current_total_net=Decimal('80000'),
        previous_total_net=Decimal('80000'),
        current_total_tax=Decimal('15000'),
        previous_total_tax=Decimal('15000'),
        gross_delta=Decimal('0'),
        gross_delta_pct=0,
        net_delta=Decimal('0'),
        net_delta_pct=0,
        changes=[],
        new_hires=[],
        departures=[],
        salary_changes=salary_changes or [],
        overtime_entries=[],
        adjustments=[],
        has_unusual_variance=has_unusual_variance,
        variance_notes=variance_notes or [],
    )


# ─────────────────────────────────────────────
# Tests: No issues (clean payroll)
# ─────────────────────────────────────────────


class TestCleanPayroll:
    def test_no_issues_clean_payroll(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=10000, tax=1500, pension_emp=700, net=7800)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert report.total == 0
        assert report.can_approve is True
        assert 'No issues' in report.summary


# ─────────────────────────────────────────────
# Tests: Critical issues
# ─────────────────────────────────────────────


class TestCriticalIssues:
    def test_negative_net_pay(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=10000, tax=12000, net=-2000)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert report.has_critical is True
        assert report.has_blocking is True
        assert report.can_approve is False
        assert any(i.code == 'NEGATIVE_NET_PAY' for i in report.issues)
        negative = next(i for i in report.issues if i.code == 'NEGATIVE_NET_PAY')
        assert negative.blocking is True
        assert negative.employee_name == 'Dawit'

    def test_net_exceeds_gross(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=10000, net=15000)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert report.has_critical is True
        assert any(i.code == 'NET_EXCEEDS_GROSS' for i in report.issues)

    def test_no_payslips(self):
        run = _make_run()

        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = run
        mock_models.Payslip.query.filter_by.return_value.all.return_value = []

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert report.has_critical is True
        assert report.has_blocking is True
        assert any(i.code == 'NO_PAYSLIPS' for i in report.issues)


# ─────────────────────────────────────────────
# Tests: High issues
# ─────────────────────────────────────────────


class TestHighIssues:
    def test_missing_bank_account(self):
        emp = _make_employee(1, 'Dawit', bank='')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert any(i.code == 'MISSING_BANK_ACCOUNT' for i in report.issues)
        issue = next(i for i in report.issues if i.code == 'MISSING_BANK_ACCOUNT')
        assert issue.severity == HIGH
        assert issue.blocking is False

    def test_zero_salary(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=0, tax=0, pension_emp=0, net=0)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert any(i.code == 'ZERO_SALARY' for i in report.issues)

    def test_unusual_variance(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        summary = _make_change_summary(
            has_unusual_variance=True,
            variance_notes=['Dawit Mekonnen: 38% salary change — review recommended'],
        )

        report = classify_exceptions(1, 1, mock_db, mock_models, change_summary=summary)

        assert any(i.code == 'UNUSUAL_VARIANCE' for i in report.issues)


# ─────────────────────────────────────────────
# Tests: Medium issues
# ─────────────────────────────────────────────


class TestMediumIssues:
    def test_missing_tin(self):
        emp = _make_employee(1, 'Dawit', tin='')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert any(i.code == 'MISSING_TIN' for i in report.issues)
        issue = next(i for i in report.issues if i.code == 'MISSING_TIN')
        assert issue.severity == MEDIUM

    def test_missing_phone(self):
        emp = _make_employee(1, 'Dawit', phone='')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert any(i.code == 'MISSING_PHONE' for i in report.issues)

    def test_cash_limit_exceeded(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=80000, tax=20000, pension_emp=5600, net=54400)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert any(i.code == 'CASH_LIMIT_EXCEEDED' for i in report.issues)

    def test_large_salary_change(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        summary = _make_change_summary(
            salary_changes=[
                EmployeeChange(
                    'EMP-001',
                    'Dawit',
                    'salary_change',
                    'raise',
                    old_value=Decimal('10000'),
                    new_value=Decimal('15000'),
                    delta=Decimal('5000'),
                    delta_pct=50.0,
                ),
            ]
        )

        report = classify_exceptions(1, 1, mock_db, mock_models, change_summary=summary)

        assert any(i.code == 'LARGE_SALARY_CHANGE' for i in report.issues)


# ─────────────────────────────────────────────
# Tests: Low issues
# ─────────────────────────────────────────────


class TestLowIssues:
    @patch('payroll_engine.exceptions._is_first_payroll', return_value=True)
    def test_new_employee_first_payroll(self, mock_first):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert any(i.code == 'NEW_EMPLOYEE_FIRST_PAYROLL' for i in report.issues)
        issue = next(i for i in report.issues if i.code == 'NEW_EMPLOYEE_FIRST_PAYROLL')
        assert issue.severity == LOW


# ─────────────────────────────────────────────
# Tests: Multiple issues
# ─────────────────────────────────────────────


class TestMultipleIssues:
    def test_multiple_employees_multiple_issues(self):
        emp1 = _make_employee(1, 'Dawit', tin='')  # Missing TIN
        emp2 = _make_employee(2, 'Hana', bank='')  # Missing bank
        emp3 = _make_employee(3, 'Kebede')  # Clean

        ps1 = _make_payslip(1)
        ps2 = _make_payslip(2)
        ps3 = _make_payslip(3)

        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps1, ps2, ps3], [emp1, emp2, emp3])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert report.total >= 2
        assert any(i.employee_name == 'Dawit' and i.code == 'MISSING_TIN' for i in report.issues)
        assert any(i.employee_name == 'Hana' and i.code == 'MISSING_BANK_ACCOUNT' for i in report.issues)

    def test_mixed_severity_ordering(self):
        emp = _make_employee(1, 'Dawit', bank='')
        ps = _make_payslip(1, gross=10000, tax=12000, net=-2000)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        sorted_issues = report.sorted_issues()
        # Critical should come first
        assert sorted_issues[0].severity == CRITICAL


# ─────────────────────────────────────────────
# Tests: Report summary
# ─────────────────────────────────────────────


class TestReportSummary:
    def test_summary_with_mixed_issues(self):
        report = ExceptionReport(
            issues=[
                Issue(CRITICAL, 'NEGATIVE_NET_PAY', 'Negative net', 'desc'),
                Issue(HIGH, 'MISSING_BANK', 'Missing bank', 'desc'),
                Issue(MEDIUM, 'MISSING_TIN', 'Missing TIN', 'desc'),
                Issue(LOW, 'NEW_EMP', 'New emp', 'desc'),
            ]
        )

        assert '4 issue' in report.summary
        assert '1 critical' in report.summary
        assert '1 high' in report.summary
        assert '1 medium' in report.summary
        assert '1 low' in report.summary

    def test_can_approve_with_no_critical(self):
        report = ExceptionReport(
            issues=[
                Issue(HIGH, 'MISSING_BANK', 'Missing bank', 'desc'),
                Issue(MEDIUM, 'MISSING_TIN', 'Missing TIN', 'desc'),
            ]
        )

        assert report.can_approve is True

    def test_cannot_approve_with_critical(self):
        report = ExceptionReport(
            issues=[
                Issue(CRITICAL, 'NEGATIVE_NET_PAY', 'Negative net', 'desc', blocking=True),
            ]
        )

        assert report.can_approve is False


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────


class TestEdgeCases:
    def test_invalid_run_returns_empty(self):
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = None

        report = classify_exceptions(999, 1, mock_db, mock_models)

        assert report.total == 0

    def test_wrong_company_returns_empty(self):
        run = _make_run(company_id=2)
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = run

        report = classify_exceptions(1, 1, mock_db, mock_models)

        assert report.total == 0

    def test_no_change_summary(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        report = classify_exceptions(1, 1, mock_db, mock_models)

        # Should work without change summary
        assert isinstance(report, ExceptionReport)


# ─────────────────────────────────────────────
# Tests: Resolution Intelligence
# ─────────────────────────────────────────────


class TestResolutionIntelligence:
    def test_negative_net_pay_has_resolution(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=10000, tax=12000, net=-2000)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])
        report = classify_exceptions(1, 1, mock_db, mock_models)

        issue = next(i for i in report.issues if i.code == 'NEGATIVE_NET_PAY')
        assert issue.impact is not None
        assert issue.cause is not None
        assert issue.recommendation is not None
        assert issue.action_url is not None
        assert issue.estimated_time is not None
        assert 'deduction' in issue.cause.lower()
        assert '/employees/' in issue.action_url

    def test_missing_bank_has_resolution(self):
        emp = _make_employee(1, 'Dawit', bank='')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])
        report = classify_exceptions(1, 1, mock_db, mock_models)

        issue = next(i for i in report.issues if i.code == 'MISSING_BANK_ACCOUNT')
        assert issue.impact is not None
        assert 'bank transfer' in issue.impact.lower()
        assert issue.cause is not None
        assert issue.recommendation is not None
        assert issue.action_url is not None
        assert 'edit' in issue.action_url

    def test_missing_tin_has_resolution(self):
        emp = _make_employee(1, 'Dawit', tin='')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])
        report = classify_exceptions(1, 1, mock_db, mock_models)

        issue = next(i for i in report.issues if i.code == 'MISSING_TIN')
        assert issue.impact is not None
        assert 'erca' in issue.impact.lower()
        assert issue.recommendation is not None
        assert 'erca' in issue.recommendation.lower()

    def test_new_employee_has_resolution(self):
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        with patch('payroll_engine.exceptions._is_first_payroll', return_value=True):
            report = classify_exceptions(1, 1, mock_db, mock_models)

        issue = next(i for i in report.issues if i.code == 'NEW_EMPLOYEE_FIRST_PAYROLL')
        assert issue.impact is not None
        assert issue.estimated_time is not None

    def test_all_issues_have_resolution_fields(self):
        """Every issue should have all resolution fields populated."""
        emp = _make_employee(1, 'Dawit', bank='', tin='', phone='')
        ps = _make_payslip(1, gross=0, tax=0, net=0)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])

        with patch('payroll_engine.exceptions._is_first_payroll', return_value=True):
            report = classify_exceptions(1, 1, mock_db, mock_models)

        for issue in report.issues:
            assert issue.impact is not None, f'{issue.code}: missing impact'
            assert issue.cause is not None, f'{issue.code}: missing cause'
            assert issue.recommendation is not None, f'{issue.code}: missing recommendation'
            assert issue.action_url is not None, f'{issue.code}: missing action_url'
            assert issue.estimated_time is not None, f'{issue.code}: missing estimated_time'

    def test_resolution_fields_are_human_readable(self):
        """Resolution text should be sentences, not codes."""
        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=10000, tax=12000, net=-2000)
        run = _make_run()

        mock_db, mock_models = _setup_db(run, [ps], [emp])
        report = classify_exceptions(1, 1, mock_db, mock_models)

        issue = report.issues[0]
        # Impact should be a sentence
        assert issue.impact[0].isupper()
        assert issue.impact.endswith('.')
        # Recommendation should be actionable
        assert len(issue.recommendation) > 20
        # Estimated time should mention minutes
        assert 'minute' in issue.estimated_time
