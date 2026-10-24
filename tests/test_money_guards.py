"""Non-finite guards and boundary behaviour for the core payroll calculator.

Derived from the launch-readiness review (money math section):
the app must never produce a negative net or NaN from any input, and
absurd salaries must stay sane.
"""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine.overtime import calculate_overtime_pay, calculate_total_overtime
from payroll_engine.payroll import (
    calculate_daily_worker_payroll,
    calculate_payroll,
    calculate_prorated_salary,
)
from payroll_engine.pension import employee_pension
from payroll_engine.severance import TerminationReason, calculate_severance
from payroll_engine.tax import calculate_tax

NAN = float('nan')
INF = float('inf')


# --- Non-finite guards: NaN and Infinity must raise, never corrupt math ---


def test_payroll_rejects_nan_basic():
    with pytest.raises(ValueError, match='finite'):
        calculate_payroll(NAN)


def test_payroll_rejects_infinite_basic():
    with pytest.raises(ValueError, match='finite'):
        calculate_payroll(INF)


def test_payroll_rejects_nan_allowances():
    with pytest.raises(ValueError, match='finite'):
        calculate_payroll(10000, NAN)


def test_payroll_rejects_nan_sick_reduction():
    with pytest.raises(ValueError, match='finite'):
        calculate_payroll(10000, sick_leave_reduction=NAN)


def test_daily_worker_rejects_nan_rate():
    with pytest.raises(ValueError, match='finite'):
        calculate_daily_worker_payroll(NAN, 10)


def test_daily_worker_rejects_infinite_days():
    with pytest.raises(ValueError, match='finite'):
        calculate_daily_worker_payroll(500, INF)


def test_tax_rejects_non_finite():
    with pytest.raises(ValueError, match='finite'):
        calculate_tax(NAN)
    with pytest.raises(ValueError, match='finite'):
        calculate_tax(INF)


def test_pension_rejects_non_finite():
    with pytest.raises(ValueError, match='finite'):
        employee_pension(NAN)
    with pytest.raises(ValueError, match='finite'):
        employee_pension(INF)


def test_overtime_rejects_non_finite_hours():
    with pytest.raises(ValueError, match='finite'):
        calculate_overtime_pay(10000, NAN, 'day')
    with pytest.raises(ValueError, match='finite'):
        calculate_overtime_pay(10000, INF, 'day')


def test_overtime_total_rejects_non_finite_hours():
    with pytest.raises(ValueError, match='finite'):
        calculate_total_overtime(10000, [{'hours': NAN, 'type': 'day'}])


def test_severance_rejects_non_finite_salary():
    with pytest.raises(ValueError, match='finite'):
        calculate_severance(NAN, date(2020, 1, 1), date(2026, 1, 1), TerminationReason.REDUNDANCY)


def test_prorated_rejects_non_finite():
    with pytest.raises(ValueError, match='finite'):
        calculate_prorated_salary(NAN, date(2026, 7, 16))
    with pytest.raises(ValueError, match='finite'):
        calculate_prorated_salary(INF, date(2026, 7, 16))


def test_payroll_accepts_numeric_string():
    """Strings ('15000') stay valid inputs."""
    result = calculate_payroll('15000')
    assert result['gross'] == Decimal('15000.00')
    assert result['net'] > 0


# --- Absurd inputs: never negative, never crash ---


def test_zero_salary_payroll():
    result = calculate_payroll(0)
    assert result['gross'] == Decimal('0.00')
    assert result['tax'] == Decimal('0')
    assert result['net'] == Decimal('0.00')
    assert result['net'] >= 0


def test_low_salary_500():
    result = calculate_payroll(500)
    assert result['pension_employee'] == Decimal('35.00')
    assert result['tax'] == Decimal('0')  # taxable 465 → 0% bracket
    assert result['net'] == Decimal('465.00')
    assert result['net'] >= 0


def test_high_salary_500k():
    result = calculate_payroll(500000)
    assert result['gross'] == Decimal('500000.00')
    assert result['tax'] > 0
    assert result['pension_employee'] == Decimal('35000.00')
    assert result['net'] >= 0
    # Taxable = 465000 → progressive: 300 + 600 + 750 + 1200 + 451000×35%.
    assert result['taxable'] == Decimal('465000.00')
    assert result['tax'] == Decimal('300') + Decimal('600') + Decimal('750') + Decimal('1200') + Decimal(
        '451000'
    ) * Decimal('0.35')


def test_net_never_negative_across_salaries():
    for salary in (0, 500, 2000, 2001, 4000, 4001, 7000, 7001, 10000, 10001, 14000, 14001, 500000):
        result = calculate_payroll(salary)
        assert result['net'] >= 0, f'negative net at salary {salary}: {result["net"]}'
        assert result['tax'] >= 0
        assert result['net'] <= result['gross']


def test_daily_worker_zero_and_negative_days():
    result = calculate_daily_worker_payroll(300, 0)
    assert result['net'] == Decimal('0.00')

    result = calculate_daily_worker_payroll(300, -5)
    assert result['net'] == Decimal('0.00')  # clamped, not negative


def test_daily_worker_no_pension():
    result = calculate_daily_worker_payroll(800, 26)
    assert result['pension_employee'] == Decimal('0')
    assert result['pension_employer'] == Decimal('0')
    assert result['tax'] == calculate_tax(Decimal('20800'))
    assert result['net'] == Decimal('20800') - result['tax']


# --- Determinism: same inputs must always produce identical results ---


def test_calculate_payroll_deterministic():
    entries = [{'hours': 4, 'type': 'day'}, {'hours': 2, 'type': 'night'}]
    first = calculate_payroll(15000, allowances=2000, overtime_entries=entries)
    second = calculate_payroll(15000, allowances=2000, overtime_entries=entries)
    monetary_keys = (
        'gross',
        'taxable',
        'tax',
        'pension_employee',
        'pension_employer',
        'net',
        'overtime_pay',
        'overtime_total_hours',
    )
    for key in monetary_keys:
        assert first[key] == second[key], f'{key} differs between runs'


# --- Pro rated salary: 30-day convention, full calendar months ---


def test_prorata_full_december_is_full_salary():
    assert calculate_prorated_salary(30000, date(2026, 1, 1), date(2026, 1, 31)) == Decimal('30000')


def test_prorata_31day_month_missing_last_day():
    """Working 1–30 of a 31-day month is already the 30-day pay month."""
    assert calculate_prorated_salary(30000, date(2026, 1, 1), date(2026, 1, 30)) == Decimal('30000')


def test_prorata_full_feb_month_is_full_salary():
    """Worked all of February = a full pay month, not 28/30 of salary."""
    assert calculate_prorated_salary(6000, date(2026, 2, 1)) == Decimal('6000')


def test_prorata_full_leap_feb():
    assert calculate_prorated_salary(6000, date(2028, 2, 1)) == Decimal('6000')


def test_prorata_midmonth_hire_inclusive():
    """Started on the 16th: 15 days worked → exactly half of a 30-day month."""
    assert calculate_prorated_salary(9000, date(2026, 4, 16)) == Decimal('4500.00')


def test_prorata_hire_midmonth_counts_from_hire():
    assert calculate_prorated_salary(9000, '2026-04-20') == Decimal('3300.00')


def test_prorata_end_before_start_is_zero():
    assert calculate_prorated_salary(9000, date(2026, 7, 20), date(2026, 7, 10)) == Decimal('0')


def test_prorata_zero_salary_is_zero():
    assert calculate_prorated_salary(0, date(2026, 7, 16)) == Decimal('0')
