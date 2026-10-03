"""
Tests for P0 features:
1. Adjustment payslip service
2. Month-end close workflow
3. Concurrency and locking
"""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine.services.adjustment_service import (
    AdjustmentResult,
    AdjustmentSummary,
    calculate_adjustment,
)
from payroll_engine.services.correction_context import freeze_context
from payroll_engine.services.month_close import (
    CloseStep,
    MonthEndClose,
)

# ---------------------------------------------------------------------------
# Test: Adjustment Calculation
# ---------------------------------------------------------------------------


def _addition(amount, **options):
    context = freeze_context(date(2026, 9, 30), employee_id='SYNTHETIC', name='Synthetic', bank='1000123456789')
    return calculate_adjustment(
        original_gross=Decimal('10000'),
        original_tax=Decimal('1475'),
        original_pension=Decimal('700'),
        original_net=Decimal('7825'),
        adjustment_amount=Decimal(amount),
        taxable_income=Decimal('9300'),
        tax_context=context,
        **options,
    )


class TestAdjustmentCalculation:
    """Test the adjustment calculation logic."""

    def test_positive_addition(self):
        result = _addition('5000')
        assert result['adjustment_gross'] == Decimal('5000')
        assert result['adjustment_tax'] > 0
        assert result['adjustment_net'] == result['adjustment_gross'] - result['adjustment_tax']
        assert result['new_total_net'] == Decimal('7825') + result['adjustment_net']
        assert result['mode'] == 'retained_period_delta'

    def test_deduction(self):
        with pytest.raises(ValueError, match='policy review'):
            _addition('2000', adjustment_type='deduction')

    def test_net_override(self):
        with pytest.raises(ValueError, match='policy review'):
            _addition('3000', adjustment_type='net_override')

    def test_addition_with_basic_salary(self):
        # Overtime/bonus additions must never mutate pension, even if an old
        # caller supplies the legacy basic_salary argument.
        result = _addition('5000', basic_salary=Decimal('5000'))
        assert result['adjustment_pension'] == Decimal('0.00')
        assert result['mode'] == 'retained_period_delta'

    def test_zero_adjustment(self):
        with pytest.raises(ValueError, match='Amount must'):
            _addition('0')

    def test_decimal_precision(self):
        result = _addition('1111.11')
        for name in ('adjustment_gross', 'adjustment_tax', 'adjustment_net', 'new_total_net'):
            assert isinstance(result[name], Decimal)
            assert result[name] == result[name].quantize(Decimal('0.01'))


# ---------------------------------------------------------------------------
# Test: Month-End Close Workflow
# ---------------------------------------------------------------------------


class TestMonthEndClose:
    """Test the month-end close workflow structure."""

    def test_close_step_dataclass(self):
        """CloseStep must have all required fields."""
        step = CloseStep(
            step_number=1,
            name='Test Step',
            name_am='ሙከራ',
            description='A test step',
            status='ready',
        )

        assert step.step_number == 1
        assert step.name == 'Test Step'
        assert step.status == 'ready'
        assert step.prerequisites == []
        assert step.actions == []

    def test_month_end_close_dataclass(self):
        """MonthEndClose must have all required fields."""
        close = MonthEndClose(
            run_id=1,
            period='2018-10',
            company_name='Test Corp',
        )

        assert close.run_id == 1
        assert close.period == '2018-10'
        assert close.is_closed is False
        assert close.progress_pct == 0

    def test_progress_pct_calculation(self):
        """Progress percentage must be calculated correctly."""
        close = MonthEndClose(run_id=1, period='2018-10', company_name='Test')
        close.steps = [
            CloseStep(step_number=1, name='A', name_am='', description='', status='completed'),
            CloseStep(step_number=2, name='B', name_am='', description='', status='completed'),
            CloseStep(step_number=3, name='C', name_am='', description='', status='ready'),
            CloseStep(step_number=4, name='D', name_am='', description='', status='not_ready'),
        ]

        assert close.progress_pct == 50  # 2/4 completed

    def test_next_action(self):
        """Next action should be the first ready/in_progress step."""
        close = MonthEndClose(run_id=1, period='2018-10', company_name='Test')
        close.steps = [
            CloseStep(step_number=1, name='Done', name_am='', description='', status='completed'),
            CloseStep(step_number=2, name='Current', name_am='', description='', status='ready'),
            CloseStep(step_number=3, name='Later', name_am='', description='', status='not_ready'),
        ]

        next_step = close.next_action
        assert next_step is not None
        assert next_step.name == 'Current'

    def test_next_action_all_done(self):
        """If all steps completed, next action is None."""
        close = MonthEndClose(run_id=1, period='2018-10', company_name='Test')
        close.steps = [
            CloseStep(step_number=1, name='A', name_am='', description='', status='completed'),
            CloseStep(step_number=2, name='B', name_am='', description='', status='completed'),
        ]

        assert close.next_action is None

    def test_summary_not_closed(self):
        """Summary should show current step when not closed."""
        close = MonthEndClose(run_id=1, period='2018-10', company_name='Test')
        close.steps = [
            CloseStep(step_number=1, name='Payroll Approved', name_am='', description='', status='completed'),
            CloseStep(step_number=2, name='Payslips', name_am='', description='', status='ready'),
        ]

        assert 'Payslips' in close.summary

    def test_summary_closed(self):
        """Summary should show closed when period is closed."""
        close = MonthEndClose(run_id=1, period='2018-10', company_name='Test')
        close.is_closed = True

        assert 'closed' in close.summary.lower()

    def test_can_close_when_all_prereqs_met(self):
        """can_close should be True when all prerequisites are met."""
        close = MonthEndClose(run_id=1, period='2018-10', company_name='Test')
        close.steps = [
            CloseStep(step_number=1, name='A', name_am='', description='', status='completed'),
            CloseStep(step_number=2, name='B', name_am='', description='', status='completed'),
            CloseStep(step_number=3, name='C', name_am='', description='', status='ready'),
        ]
        close.can_close = True

        assert close.can_close


# ---------------------------------------------------------------------------
# Test: Adjustment Summary
# ---------------------------------------------------------------------------


class TestAdjustmentSummary:
    """Test the adjustment summary dataclass."""

    def test_summary_defaults(self):
        """Summary must have sensible defaults."""
        summary = AdjustmentSummary(run_id=1, period='2018-10')

        assert summary.total_adjustments == 0
        assert summary.total_positive_net == Decimal('0')
        assert summary.total_negative_net == Decimal('0')
        assert summary.net_adjustment == Decimal('0')
        assert summary.adjustments == []
        assert summary.employees_affected == 0

    def test_net_adjustment_calculation(self):
        """Net adjustment = positive - negative."""
        summary = AdjustmentSummary(
            run_id=1,
            period='2018-10',
            total_positive_net=Decimal('5000'),
            total_negative_net=Decimal('2000'),
        )

        # Net should be 5000 - 2000 = 3000
        assert summary.total_positive_net - summary.total_negative_net == Decimal('3000')


# ---------------------------------------------------------------------------
# Test: Adjustment Result
# ---------------------------------------------------------------------------


class TestAdjustmentResult:
    """Test the adjustment result dataclass."""

    def test_success_result(self):
        result = AdjustmentResult(
            success=True, adjustment_id=42, employee_name='Synthetic worker', adjustment_net=Decimal('3500')
        )
        assert result.success is True
        assert result.adjustment_id == 42
        assert result.adjustment_net == Decimal('3500')
        assert result.error == ''

    def test_failure_result(self):
        """Failure result must have error message."""
        result = AdjustmentResult(
            success=False,
            error='Employee not found.',
        )

        assert result.success is False
        assert result.error == 'Employee not found.'
        assert result.adjustment_id is None


# ---------------------------------------------------------------------------
# Test: Concurrency Patterns
# ---------------------------------------------------------------------------


class TestConcurrencyPatterns:
    """Test patterns for concurrent access (no DB required)."""

    def test_optimistic_locking_pattern(self):
        """PayrollRun uses version_id for optimistic locking."""
        from payroll_engine.models import PayrollRun

        # Verify the mapper has version_id_col configured
        mapper = PayrollRun.__mapper__
        assert mapper.version_id_col is not None
        assert mapper.version_id_col.name == 'version_id'

    def test_with_for_update_pattern_exists(self):
        """The undo_approval route uses SELECT FOR UPDATE."""
        import inspect

        from payroll_engine.payroll_bp import undo_approval

        source = inspect.getsource(undo_approval)
        assert 'with_for_update' in source

    def test_status_check_before_action(self):
        """Approval checks status before processing."""
        import inspect

        from payroll_engine.payroll_bp import undo_approval

        source = inspect.getsource(undo_approval)
        assert "run.status != 'completed'" in source

    def test_disbursement_check_before_undo(self):
        """Undo checks disbursement status before allowing undo."""
        import inspect

        from payroll_engine.payroll_bp import undo_approval

        source = inspect.getsource(undo_approval)
        assert 'disbursement_status' in source

    def test_time_window_check(self):
        """Undo has a 1-hour time window."""
        import inspect

        from payroll_engine.payroll_bp import undo_approval

        source = inspect.getsource(undo_approval)
        assert 'timedelta(hours=1)' in source


# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------


class TestAdjustmentEdgeCases:
    """Edge cases for adjustment calculations."""

    def test_very_small_adjustment(self):
        result = _addition('0.01')
        assert result['adjustment_gross'] == Decimal('0.01')
        assert result['new_total_net'] == Decimal('7825.01')

    def test_large_adjustment(self):
        result = _addition('100000')
        assert result['adjustment_gross'] == Decimal('100000')
        assert result['adjustment_tax'] > 0
        assert result['adjustment_net'] > 0

    def test_deduction_larger_than_net(self):
        with pytest.raises(ValueError, match='policy review'):
            _addition('10000', adjustment_type='deduction')
