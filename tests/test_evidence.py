"""
Tests for evidence.py — Evidence Engine

Tests trust signals: each check is explicit and explainable.

Run: python -m pytest tests/test_evidence.py -v
"""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.evidence import FAIL, PASS, WARN, EvidenceReport, Signal, collect_evidence

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _make_employee(
    emp_id, name, employee_id_str=None, bank='1000123456789', tin='1234567890', phone='0911234567', is_deleted=False
):
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = employee_id_str or f'EMP-{emp_id:03d}'
    emp.name = name
    emp.company_id = 1
    emp.bank_or_telebirr = bank
    emp.tin = tin
    emp.phone = phone
    emp.is_deleted = is_deleted
    return emp


def _make_payslip(emp_id, gross=10000, tax=1500, pension_emp=700, net=None):
    ps = MagicMock()
    ps.employee_id = emp_id
    ps.gross_salary = Decimal(str(gross))
    ps.tax = Decimal(str(tax))
    ps.employee_pension = Decimal(str(pension_emp))
    ps.net_pay = Decimal(str(net if net is not None else gross - tax - pension_emp))
    return ps


def _make_run(run_id=1, period='2018-10', company_id=1):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.status = 'completed'
    return run


def _setup(employees, payslips, run, duplicate_count=0):
    """Set up mocks for collect_evidence."""
    mock_db = MagicMock()
    mock_models = MagicMock()

    emp_map = {e.id: e for e in employees}

    def session_get(model, id):
        return emp_map.get(id, run)

    mock_db.session.get.side_effect = session_get

    # Current payslips
    mock_models.Payslip.query.filter_by.return_value.all.return_value = payslips

    # All active employees
    mock_models.Employee.query.filter_by.return_value.all.return_value = [e for e in employees if not e.is_deleted]

    # Duplicate run count
    mock_models.PayrollRun.query.filter.return_value.count.return_value = duplicate_count

    return mock_db, mock_models


# ─────────────────────────────────────────────
# Tests: All checks pass
# ─────────────────────────────────────────────


class TestCleanPayroll:
    @patch('payroll_engine.evidence.classify_exceptions')
    def test_all_signals_pass(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        assert report.has_failures is False
        assert report.ready_for_approval is True
        assert 'All' in report.summary() and 'passed' in report.summary()

    @patch('payroll_engine.evidence.classify_exceptions')
    def test_signal_count(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        # Should have: employees processed, validation errors, payroll balanced,
        # tax rules, pension rules, no duplicate, mandatory data, no critical exceptions
        assert report.total >= 7


# ─────────────────────────────────────────────
# Tests: Employee processing
# ─────────────────────────────────────────────


class TestEmployeeProcessing:
    @patch('payroll_engine.evidence.classify_exceptions')
    def test_all_employees_processed(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')
        ps1 = _make_payslip(1)
        ps2 = _make_payslip(2)
        run = _make_run()

        mock_db, mock_models = _setup([emp1, emp2], [ps1, ps2], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'All employees processed')
        assert signal.status == PASS
        assert '2/2' in signal.detail

    @patch('payroll_engine.evidence.classify_exceptions')
    def test_missing_employee_detected(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')  # Not in payslips
        ps1 = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp1, emp2], [ps1], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'All employees processed')
        assert signal.status == FAIL
        assert signal.blocking is True
        assert '1' in signal.detail


# ─────────────────────────────────────────────
# Tests: Validation
# ─────────────────────────────────────────────


class TestValidation:
    @patch('payroll_engine.evidence.classify_exceptions')
    def test_negative_net_pay_fails(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1, gross=10000, tax=12000, net=-2000)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'No validation errors')
        assert signal.status == FAIL
        assert signal.blocking is True

    @patch('payroll_engine.evidence.classify_exceptions')
    def test_balanced_payroll(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit')
        # gross=10000, tax=1500, pension=700, net=7800 → balanced
        ps = _make_payslip(1, gross=10000, tax=1500, pension_emp=700, net=7800)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'Payroll balanced')
        assert signal.status == PASS


# ─────────────────────────────────────────────
# Tests: Compliance
# ─────────────────────────────────────────────


class TestCompliance:
    @patch('payroll_engine.evidence.classify_exceptions')
    def test_tax_rules_verified(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        tax_signal = next(s for s in report.signals if s.name == 'Tax rules verified')
        assert tax_signal.status == PASS
        assert '1395/2025' in tax_signal.source

    @patch('payroll_engine.evidence.classify_exceptions')
    def test_pension_rules_verified(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        pension_signal = next(s for s in report.signals if s.name == 'Pension rules verified')
        assert pension_signal.status == PASS
        assert '1268/2022' in pension_signal.source


# ─────────────────────────────────────────────
# Tests: Data quality
# ─────────────────────────────────────────────


class TestDataQuality:
    @patch('payroll_engine.evidence.classify_exceptions')
    def test_complete_data(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit', tin='123', bank='1000123', phone='0911')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'All mandatory data present')
        assert signal.status == PASS

    @patch('payroll_engine.evidence.classify_exceptions')
    def test_missing_tin_warns(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])

        emp = _make_employee(1, 'Dawit', tin='')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'All mandatory data present')
        assert signal.status == WARN
        assert 'TIN' in signal.detail


# ─────────────────────────────────────────────
# Tests: Exceptions integration
# ─────────────────────────────────────────────


class TestExceptionIntegration:
    @patch('payroll_engine.evidence.classify_exceptions')
    def test_critical_exception_fails(self, mock_exceptions):
        mock_exceptions.return_value = MagicMock(
            has_critical=True, total=1, high=[], medium=[], low=[], critical=[MagicMock(title='Negative net pay')]
        )

        emp = _make_employee(1, 'Dawit')
        ps = _make_payslip(1)
        run = _make_run()

        mock_db, mock_models = _setup([emp], [ps], run)

        report = collect_evidence(1, 1, mock_db, mock_models)

        signal = next(s for s in report.signals if s.name == 'No critical exceptions')
        assert signal.status == FAIL
        assert signal.blocking is True


# ─────────────────────────────────────────────
# Tests: Report structure
# ─────────────────────────────────────────────


class TestReportStructure:
    def test_by_category(self):
        report = EvidenceReport(
            signals=[
                Signal('A', PASS, 'validation', 'test'),
                Signal('B', PASS, 'compliance', 'test'),
                Signal('C', WARN, 'data_quality', 'test'),
            ]
        )

        assert len(report.by_category('validation')) == 1
        assert len(report.by_category('compliance')) == 1
        assert len(report.by_category('data_quality')) == 1
        assert len(report.by_category('integrity')) == 0

    def test_pass_rate(self):
        report = EvidenceReport(
            signals=[
                Signal('A', PASS, 'validation', 'test'),
                Signal('B', PASS, 'compliance', 'test'),
                Signal('C', FAIL, 'data_quality', 'test'),
            ]
        )

        assert abs(report.pass_rate - 66.67) < 0.1

    def test_ready_for_approval(self):
        report = EvidenceReport(
            signals=[
                Signal('A', PASS, 'validation', 'test'),
            ]
        )
        assert report.ready_for_approval is True

    def test_not_ready_with_blocking(self):
        report = EvidenceReport(
            signals=[
                Signal('A', FAIL, 'validation', 'test', blocking=True),
            ]
        )
        assert report.ready_for_approval is False

    def test_summary_all_pass(self):
        report = EvidenceReport(
            signals=[
                Signal('A', PASS, 'validation', 'test'),
                Signal('B', PASS, 'compliance', 'test'),
            ]
        )
        assert 'All 2 checks passed' in report.summary()

    def test_summary_with_failures(self):
        report = EvidenceReport(
            signals=[
                Signal('A', PASS, 'validation', 'test'),
                Signal('B', FAIL, 'compliance', 'test'),
                Signal('C', WARN, 'data_quality', 'test'),
            ]
        )
        assert '1 failed' in report.summary()
        assert '1 warnings' in report.summary()


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────


class TestEdgeCases:
    def test_invalid_run_returns_empty(self):
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = None

        report = collect_evidence(999, 1, mock_db, mock_models)

        assert report.total == 0

    def test_empty_payslips(self):
        emp = _make_employee(1, 'Dawit')
        run = _make_run()

        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = run
        mock_models.Payslip.query.filter_by.return_value.all.return_value = []
        mock_models.Employee.query.filter_by.return_value.all.return_value = [emp]
        mock_models.PayrollRun.query.filter.return_value.count.return_value = 0

        with patch('payroll_engine.evidence.classify_exceptions') as mock_exc:
            mock_exc.return_value = MagicMock(has_critical=False, total=0, high=[], medium=[], low=[])
            report = collect_evidence(1, 1, mock_db, mock_models)

        # Should still have compliance and data quality checks
        assert report.total > 0
        employee_signal = next(s for s in report.signals if s.name == 'All employees processed')
        assert employee_signal.status == FAIL  # Dawit is active but not in payslips
