"""
Tests for narrative.py — Trust Pattern #6: Payroll Narrative

Tests the plain-English paragraph generation from Change Summary data.

Run: python -m pytest tests/test_narrative.py -v
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.change_summary import ChangeSummary, EmployeeChange
from payroll_engine.narrative import generate_narrative

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_summary(
    current_period='2018-10',
    previous_period='2018-09',
    current_employees=128,
    previous_employees=126,
    headcount_change=2,
    gross_delta_pct=1.3,
    new_hires=None,
    departures=None,
    salary_changes=None,
    overtime_entries=None,
    adjustments=None,
    has_unusual_variance=False,
    variance_notes=None,
):
    return ChangeSummary(
        current_period=current_period,
        previous_period=previous_period,
        current_employee_count=current_employees,
        previous_employee_count=previous_employees,
        headcount_change=headcount_change,
        current_total_gross=Decimal('2847210'),
        previous_total_gross=Decimal('2810000'),
        current_total_net=Decimal('2300000'),
        previous_total_net=Decimal('2270000'),
        current_total_tax=Decimal('400000'),
        previous_total_tax=Decimal('390000'),
        gross_delta=Decimal('37210'),
        gross_delta_pct=gross_delta_pct,
        net_delta=Decimal('30000'),
        net_delta_pct=1.3,
        changes=[],
        new_hires=new_hires or [],
        departures=departures or [],
        salary_changes=salary_changes or [],
        overtime_entries=overtime_entries or [],
        adjustments=adjustments or [],
        has_unusual_variance=has_unusual_variance,
        variance_notes=variance_notes or [],
    )


def _make_change(name, change_type='salary_change'):
    return EmployeeChange(
        employee_id='EMP-001',
        employee_name=name,
        change_type=change_type,
        description='test',
    )


# ─────────────────────────────────────────────
# Tests: Employee count
# ─────────────────────────────────────────────

class TestEmployeeCount:

    def test_basic_employee_count(self):
        summary = _make_summary(current_employees=128)
        text = generate_narrative(summary)
        assert '128 employees' in text

    def test_singular_employee(self):
        summary = _make_summary(current_employees=1, headcount_change=0)
        text = generate_narrative(summary)
        assert '1 employee' in text
        assert 'employees' not in text

    def test_headcount_increase(self):
        summary = _make_summary(headcount_change=2)
        text = generate_narrative(summary)
        assert '+2' in text

    def test_headcount_decrease(self):
        summary = _make_summary(headcount_change=-1, current_employees=125,
                                previous_employees=126)
        text = generate_narrative(summary)
        assert '-1' in text

    def test_no_headcount_change(self):
        summary = _make_summary(headcount_change=0, current_employees=126,
                                previous_employees=126)
        text = generate_narrative(summary)
        assert '126 employees' in text
        assert '+' not in text.split('.')[0]  # No +/- in first sentence


# ─────────────────────────────────────────────
# Tests: First payroll (no previous)
# ─────────────────────────────────────────────

class TestFirstPayroll:

    def test_first_payroll_uses_period_name(self):
        summary = _make_summary(previous_period=None, headcount_change=0,
                                gross_delta_pct=0)
        text = generate_narrative(summary)
        assert '2018-10' in text
        assert 'includes' in text

    def test_first_payroll_no_delta_text(self):
        summary = _make_summary(previous_period=None, headcount_change=0,
                                gross_delta_pct=0)
        text = generate_narrative(summary)
        assert 'increased' not in text
        assert 'decreased' not in text


# ─────────────────────────────────────────────
# Tests: Event descriptions
# ─────────────────────────────────────────────

class TestEventDescriptions:

    def test_single_new_hire(self):
        summary = _make_summary(new_hires=[_make_change('Dawit', 'new_hire')])
        text = generate_narrative(summary)
        assert '1 new hire' in text
        assert '1 new hire' in text

    def test_multiple_new_hires(self):
        summary = _make_summary(new_hires=[
            _make_change('Dawit', 'new_hire'),
            _make_change('Hana', 'new_hire'),
        ])
        text = generate_narrative(summary)
        assert '2 new hires' in text

    def test_resignation_mentioned(self):
        summary = _make_summary(departures=[_make_change('Abebe', 'departure')])
        text = generate_narrative(summary)
        assert '1 resignation' in text

    def test_salary_changes_mentioned(self):
        summary = _make_summary(salary_changes=[_make_change('Dawit')])
        text = generate_narrative(summary)
        assert '1 salary change' in text

    def test_overtime_mentioned(self):
        summary = _make_summary(overtime_entries=[
            _make_change(f'Emp{i}', 'overtime') for i in range(12)
        ])
        text = generate_narrative(summary)
        assert '12 overtime claims' in text

    def test_adjustments_mentioned(self):
        summary = _make_summary(adjustments=[_make_change('Dawit', 'adjustment')])
        text = generate_narrative(summary)
        assert '1 adjustment' in text

    def test_multiple_event_types(self):
        summary = _make_summary(
            new_hires=[_make_change('A', 'new_hire')],
            departures=[_make_change('B', 'departure')],
            salary_changes=[_make_change('C')],
        )
        text = generate_narrative(summary)
        assert 'new hire' in text
        assert 'resignation' in text
        assert 'salary change' in text

    def test_no_changes(self):
        summary = _make_summary(
            new_hires=[], departures=[], salary_changes=[],
            overtime_entries=[], adjustments=[],
        )
        text = generate_narrative(summary)
        assert 'No changes from last period' in text


# ─────────────────────────────────────────────
# Tests: Delta explanation
# ─────────────────────────────────────────────

class TestDeltaExplanation:

    def test_increased(self):
        summary = _make_summary(gross_delta_pct=1.3)
        text = generate_narrative(summary)
        assert 'increased' in text
        assert '1.3%' in text

    def test_decreased(self):
        summary = _make_summary(gross_delta_pct=-2.5)
        text = generate_narrative(summary)
        assert 'decreased' in text
        assert '2.5%' in text

    def test_essentially_unchanged(self):
        summary = _make_summary(gross_delta_pct=0.05)
        text = generate_narrative(summary)
        assert 'essentially unchanged' in text

    def test_primary_reason_new_hires(self):
        summary = _make_summary(
            gross_delta_pct=3.0,
            new_hires=[_make_change('A', 'new_hire')],
        )
        text = generate_narrative(summary)
        assert 'new hire' in text
        assert 'primarily' in text

    def test_multiple_reasons(self):
        summary = _make_summary(
            gross_delta_pct=5.0,
            new_hires=[_make_change('A', 'new_hire')],
            overtime_entries=[_make_change('B', 'overtime')],
            salary_changes=[_make_change('C')],
        )
        text = generate_narrative(summary)
        assert 'primarily because of' in text


# ─────────────────────────────────────────────
# Tests: Variance verdict
# ─────────────────────────────────────────────

class TestVarianceVerdict:

    def test_no_unusual_variance(self):
        summary = _make_summary(has_unusual_variance=False)
        text = generate_narrative(summary)
        assert 'No unusual variances detected' in text

    def test_unusual_variance_with_note(self):
        summary = _make_summary(
            has_unusual_variance=True,
            variance_notes=['Dawit Mekonnen: 38% salary change — review recommended'],
        )
        text = generate_narrative(summary)
        assert '⚠' in text
        assert 'Dawit Mekonnen' in text

    def test_unusual_variance_no_note(self):
        summary = _make_summary(has_unusual_variance=True, variance_notes=[])
        text = generate_narrative(summary)
        assert '⚠' in text
        assert 'review recommended' in text


# ─────────────────────────────────────────────
# Tests: Full narrative examples
# ─────────────────────────────────────────────

class TestFullNarrative:

    def test_typical_month(self):
        summary = _make_summary(
            current_employees=128,
            headcount_change=2,
            gross_delta_pct=1.3,
            new_hires=[_make_change('A', 'new_hire'), _make_change('B', 'new_hire')],
            departures=[_make_change('C', 'departure')],
            salary_changes=[_make_change('D'), _make_change('E'), _make_change('F')],
            overtime_entries=[_make_change(f'G{i}', 'overtime') for i in range(12)],
        )
        text = generate_narrative(summary)

        assert '128 employees' in text
        assert '2 new hires' in text
        assert '1 resignation' in text
        assert '3 salary changes' in text
        assert '12 overtime claims' in text
        assert '1.3%' in text
        assert 'No unusual variances' in text

    def test_quiet_month(self):
        summary = _make_summary(
            current_employees=126,
            headcount_change=0,
            gross_delta_pct=0.05,
            new_hires=[], departures=[], salary_changes=[],
            overtime_entries=[], adjustments=[],
        )
        text = generate_narrative(summary)

        assert '126 employees' in text
        assert 'No changes' in text
        assert 'essentially unchanged' in text
        assert 'No unusual variances' in text

    def test_first_payroll_ever(self):
        summary = _make_summary(
            previous_period=None,
            current_employees=50,
            headcount_change=0,
            gross_delta_pct=0,
            new_hires=[], departures=[], salary_changes=[],
            overtime_entries=[], adjustments=[],
        )
        text = generate_narrative(summary)

        assert '50 employees' in text
        assert '2018-10' in text
        # No delta or variance text for first payroll
        assert 'increased' not in text
        assert 'decreased' not in text

    def test_problematic_month(self):
        summary = _make_summary(
            current_employees=130,
            headcount_change=5,
            gross_delta_pct=25.0,
            new_hires=[_make_change(f'N{i}', 'new_hire') for i in range(5)],
            salary_changes=[_make_change('BigRaise')],
            has_unusual_variance=True,
            variance_notes=['Total gross +25.0% — exceeds 20% threshold'],
        )
        text = generate_narrative(summary)

        assert '130 employees' in text
        assert '5 new hires' in text
        assert '25.0%' in text
        assert '⚠' in text


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_none_summary(self):
        text = generate_narrative(None)
        assert 'not available' in text

    def test_zero_employees(self):
        summary = _make_summary(current_employees=0, headcount_change=0)
        text = generate_narrative(summary)
        assert '0 employees' in text

    def test_large_numbers(self):
        summary = _make_summary(
            current_employees=5000,
            headcount_change=100,
            gross_delta_pct=8.5,
        )
        text = generate_narrative(summary)
        assert '5000 employees' in text
        assert '+100' in text
