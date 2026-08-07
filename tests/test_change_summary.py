"""
Tests for change_summary.py — Trust Pattern #1: Change Summary

Tests the payroll period comparison logic: new hires, departures,
salary changes, overtime detection, variance flags.

Run: python -m pytest tests/test_change_summary.py -v
"""
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.change_summary import _build_summary

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_employee(emp_id, name, employee_id_str=None):
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = employee_id_str or f'EMP-{emp_id:03d}'
    emp.name = name
    emp.company_id = 1
    return emp


def _make_payslip(emp_id, gross, tax=0, pension_emp=0, pension_empr=0, net=None,
                   payslip_type='regular', reason=None):
    ps = MagicMock()
    ps.employee_id = emp_id
    ps.gross_salary = Decimal(str(gross))
    ps.tax = Decimal(str(tax))
    ps.employee_pension = Decimal(str(pension_emp))
    ps.employer_pension = Decimal(str(pension_empr))
    ps.net_pay = Decimal(str(net if net is not None else gross - tax - pension_emp))
    ps.payslip_type = payslip_type
    ps.reason = reason
    return ps


def _make_run(run_id, period, company_id=1):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.run_date = None
    run.status = 'completed'
    return run


class MockDB:
    """Mock SQLAlchemy session that returns employees by ID."""
    def __init__(self, employees):
        self._employees = {e.id: e for e in employees}

    class session:
        @staticmethod
        def get(model, id):
            return MockDB._employees.get(id) if hasattr(model, '__name__') else None

    def __init_subclass__(cls, **kwargs):
        pass


def _setup_mocks(current_run, previous_run, current_payslips, previous_payslips,
                  employees, current_run_id=2, company_id=1):
    """Set up all the mocks for compute_change_summary."""
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Current run
    mock_db.session.get.return_value = current_run

    # Current payslips
    mock_models.Payslip.query.filter_by.return_value.all.return_value = current_payslips

    # Previous payslips (called when previous_run exists)
    if previous_run:
        def payslip_filter_by(**kwargs):
            mock = MagicMock()
            if kwargs.get('payroll_run_id') == previous_run.id:
                mock.all.return_value = previous_payslips
            else:
                mock.all.return_value = current_payslips
            return mock
        mock_models.Payslip.query.filter_by.side_effect = payslip_filter_by

    # Employee lookup
    emp_map = {e.id: e for e in employees}
    def session_get(model, id):
        return emp_map.get(id)
    mock_db.session.get.side_effect = session_get

    return mock_db, mock_models, previous_run


# ─────────────────────────────────────────────
# Tests: No previous run (first payroll)
# ─────────────────────────────────────────────

class TestFirstPayroll:

    def test_first_run_returns_summary(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')
        ps1 = _make_payslip(1, gross=10000, tax=1500, pension_emp=700)
        ps2 = _make_payslip(2, gross=15000, tax=2500, pension_emp=1050)

        current_run = _make_run(1, '2018-10')
        employees = [emp1, emp2]

        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_models.Payslip.query.filter_by.return_value.all.return_value = [ps1, ps2]

        emp_map = {1: emp1, 2: emp2}
        mock_db.session.get.side_effect = lambda model, id: emp_map.get(id)

        result = _build_summary(current_run, None, [ps1, ps2], 1, mock_db, mock_models)

        assert result is not None
        assert result.current_employee_count == 2
        assert result.previous_employee_count == 0
        assert result.previous_period is None
        assert result.current_total_gross == Decimal('25000')

    def test_first_run_no_changes_detected(self):
        emp1 = _make_employee(1, 'Dawit')
        ps1 = _make_payslip(1, gross=10000)

        current_run = _make_run(1, '2018-10')

        mock_db = MagicMock()
        mock_models = MagicMock()

        emp_map = {1: emp1}
        mock_db.session.get.side_effect = lambda model, id: emp_map.get(id)

        result = _build_summary(current_run, None, [ps1], 1, mock_db, mock_models)

        # First run: all employees treated as new (no previous to compare)
        assert len(result.new_hires) == 1
        assert result.new_hires[0].employee_name == 'Dawit'


# ─────────────────────────────────────────────
# Tests: New hires
# ─────────────────────────────────────────────

class TestNewHires:

    def test_detects_new_employee(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')  # New this month
        emp3 = _make_employee(3, 'Kebede')

        prev_payslips = [_make_payslip(1, gross=10000), _make_payslip(3, gross=20000)]
        curr_payslips = [_make_payslip(1, gross=10000), _make_payslip(2, gross=12000),
                         _make_payslip(3, gross=20000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')
        employees = [emp1, emp2, emp3]

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, employees
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result is not None
        assert len(result.new_hires) == 1
        assert result.new_hires[0].employee_name == 'Hana'
        assert result.new_hires[0].change_type == 'new_hire'

    def test_headcount_increases(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')

        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=10000), _make_payslip(2, gross=12000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1, emp2]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.headcount_change == 1
        assert result.current_employee_count == 2
        assert result.previous_employee_count == 1


# ─────────────────────────────────────────────
# Tests: Departures
# ─────────────────────────────────────────────

class TestDepartures:

    def test_detects_departed_employee(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Abebe')  # Left this month

        prev_payslips = [_make_payslip(1, gross=10000), _make_payslip(2, gross=8000)]
        curr_payslips = [_make_payslip(1, gross=10000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1, emp2]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert len(result.departures) == 1
        assert result.departures[0].employee_name == 'Abebe'
        assert result.departures[0].change_type == 'departure'
        assert result.departures[0].old_value == Decimal('8000')

    def test_headcount_decreases(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Abebe')

        prev_payslips = [_make_payslip(1, gross=10000), _make_payslip(2, gross=8000)]
        curr_payslips = [_make_payslip(1, gross=10000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1, emp2]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.headcount_change == -1


# ─────────────────────────────────────────────
# Tests: Salary changes
# ─────────────────────────────────────────────

class TestSalaryChanges:

    def test_detects_salary_increase(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000, tax=1500)]
        curr_payslips = [_make_payslip(1, gross=12000, tax=1900)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert len(result.salary_changes) == 1
        assert result.salary_changes[0].delta == Decimal('2000')
        assert result.salary_changes[0].delta_pct == 20.0
        assert 'salary_change' in result.salary_changes[0].change_type

    def test_detects_salary_decrease(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=12000)]
        curr_payslips = [_make_payslip(1, gross=10000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert len(result.salary_changes) == 1
        assert result.salary_changes[0].delta == Decimal('-2000')

    def test_no_change_means_no_salary_change(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=10000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert len(result.salary_changes) == 0

    def test_large_change_flagged_as_review(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=15000)]  # 50% increase

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.salary_changes[0].severity == 'review'
        assert result.has_unusual_variance is True


# ─────────────────────────────────────────────
# Tests: Variance detection
# ─────────────────────────────────────────────

class TestVarianceDetection:

    def test_20_percent_variance_flagged(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=13000)]  # 30% increase

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.has_unusual_variance is True
        assert result.status == 'review'
        assert len(result.variance_notes) > 0

    def test_10_percent_is_attention(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=11200)]  # 12% increase

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.has_unusual_variance is False
        assert result.status == 'attention'

    def test_small_change_is_normal(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=10200)]  # 2% increase

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.has_unusual_variance is False
        assert result.status == 'normal'


# ─────────────────────────────────────────────
# Tests: Summary text
# ─────────────────────────────────────────────

class TestSummaryText:

    def test_no_changes_text(self):
        emp1 = _make_employee(1, 'Dawit')
        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=10000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert 'No changes' in result.summary_text

    def test_changes_text_includes_counts(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')
        emp3 = _make_employee(3, 'New Guy')

        prev_payslips = [_make_payslip(1, gross=10000), _make_payslip(2, gross=12000)]
        curr_payslips = [_make_payslip(1, gross=11000), _make_payslip(2, gross=12000),
                         _make_payslip(3, gross=8000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1, emp2, emp3]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert '1 new hire' in result.summary_text
        assert '1 salary change' in result.summary_text


# ─────────────────────────────────────────────
# Tests: Totals
# ─────────────────────────────────────────────

class TestTotals:

    def test_totals_calculated_correctly(self):
        emp1 = _make_employee(1, 'Dawit')
        emp2 = _make_employee(2, 'Hana')

        prev_payslips = [_make_payslip(1, gross=10000, tax=1500, pension_emp=700),
                         _make_payslip(2, gross=15000, tax=2500, pension_emp=1050)]
        curr_payslips = [_make_payslip(1, gross=10000, tax=1500, pension_emp=700),
                         _make_payslip(2, gross=15000, tax=2500, pension_emp=1050)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1, emp2]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.current_total_gross == Decimal('25000')
        assert result.previous_total_gross == Decimal('25000')
        assert result.gross_delta == Decimal('0')
        assert result.gross_delta_pct == 0.0

    def test_delta_calculated_correctly(self):
        emp1 = _make_employee(1, 'Dawit')

        prev_payslips = [_make_payslip(1, gross=10000)]
        curr_payslips = [_make_payslip(1, gross=12000)]

        current_run = _make_run(2, '2018-10')
        previous_run = _make_run(1, '2018-09')

        mock_db, mock_models, prev_run = _setup_mocks(
            current_run, previous_run, curr_payslips, prev_payslips, [emp1]
        )

        result = _build_summary(_make_run(2, "2018-10"), prev_run, mock_models.Payslip.query.filter_by.return_value.all.return_value, 1, mock_db, mock_models)

        assert result.gross_delta == Decimal('2000')
        assert result.gross_delta_pct == 20.0


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_no_previous_run_first_payroll(self):
        """_build_summary with None previous_run should work (first payroll)."""
        emp1 = _make_employee(1, 'Dawit')
        ps1 = _make_payslip(1, gross=10000)

        mock_db = MagicMock()
        mock_models = MagicMock()

        emp_map = {1: emp1}
        mock_db.session.get.side_effect = lambda model, id: emp_map.get(id)

        result = _build_summary(_make_run(1, '2018-10'), None, [ps1], 1, mock_db, mock_models)

        assert result is not None
        assert result.previous_period is None
        assert result.previous_employee_count == 0
        # First payroll: all current employees are treated as new hires
        assert len(result.new_hires) == 1

    def test_empty_current_payslips(self):
        """_build_summary with empty current payslips should return None."""
        mock_db = MagicMock()
        mock_models = MagicMock()

        result = _build_summary(_make_run(1, '2018-10'), None, [], 1, mock_db, mock_models)

        assert result is not None
        assert result.current_employee_count == 0

    def test_mixed_changes(self):
        """Multiple types of changes in one run."""
        emp1 = _make_employee(1, 'Dawit')   # Salary change
        emp2 = _make_employee(2, 'Abebe')   # Departure
        emp3 = _make_employee(3, 'New Guy') # New hire

        prev_payslips = [_make_payslip(1, gross=10000), _make_payslip(2, gross=8000)]
        curr_payslips = [_make_payslip(1, gross=12000), _make_payslip(3, gross=9000)]

        mock_db = MagicMock()
        mock_models = MagicMock()

        # Previous payslips query returns different results based on payroll_run_id
        def payslip_filter_by(**kwargs):
            mock = MagicMock()
            if kwargs.get('payroll_run_id') == 1:  # previous run
                mock.all.return_value = prev_payslips
            else:
                mock.all.return_value = curr_payslips
            return mock
        mock_models.Payslip.query.filter_by.side_effect = payslip_filter_by

        emp_map = {1: emp1, 2: emp2, 3: emp3}
        mock_db.session.get.side_effect = lambda model, id: emp_map.get(id)

        result = _build_summary(
            _make_run(2, '2018-10'), _make_run(1, '2018-09'),
            curr_payslips, 1, mock_db, mock_models
        )

        assert len(result.new_hires) == 1  # New Guy
        assert len(result.departures) == 1  # Abebe
        assert len(result.salary_changes) == 1  # Dawit 10k→12k
        assert result.headcount_change == 0  # +1 new, -1 departure
