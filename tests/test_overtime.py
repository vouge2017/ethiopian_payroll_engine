"""
Overtime rate calculation tests.

Labor Proclamation No. 1156/2019, Article 68:
    Regular day: 1.25x, Night: 1.5x, Holiday: 2.0x, Rest day holiday: 2.5x

Hourly rate = basic_salary / 208 (26 working days × 8 hours)
Per Ethiopian labor law: 48 hours/week, 6 days/week, 26 days/month.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from decimal import ROUND_HALF_UP, Decimal

from overtime import (
    DEFAULT_MAX_HOURS_MONTH as MAX_OVERTIME_HOURS_MONTH,
)
from overtime import (
    DEFAULT_OVERTIME_RATES as OVERTIME_RATES,
)
from overtime import (
    calculate_hourly_rate,
    calculate_overtime_pay,
    calculate_total_overtime,
    get_overtime_type_label,
)

D = Decimal


# --- Hourly rate ---


def test_hourly_rate_basic():
    """Keep the hourly rate precise; it is an intermediate, not a money amount."""
    rate = calculate_hourly_rate(10000)
    expected = D('10000') / D('208')
    assert rate == expected, f'Expected {expected}, got {rate}'


def test_hourly_rate_zero():
    assert calculate_hourly_rate(0) == D('0')


def test_hourly_rate_negative():
    assert calculate_hourly_rate(-5000) == D('0')


def test_hourly_rate_15000():
    """The intermediate rate remains unrounded at every salary."""
    rate = calculate_hourly_rate(15000)
    expected = D('15000') / D('208')
    assert rate == expected, f'Expected {expected}, got {rate}'


# --- Overtime pay by type ---


def test_overtime_day():
    """Round the final overtime amount, not the intermediate hourly rate."""
    pay = calculate_overtime_pay(10000, 4, 'day')
    expected = (D('10000') / D('208') * D('4') * D('1.50')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
    assert expected == D('288.46')
    assert pay == expected, f'Expected {expected}, got {pay}'


def test_overtime_night():
    """Night overtime rounds after applying hours and the configured multiplier."""
    pay = calculate_overtime_pay(10000, 3, 'night')
    expected = (D('10000') / D('208') * D('3') * D('1.75')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
    assert pay == expected, f'Expected {expected}, got {pay}'


def test_overtime_holiday():
    """Weekly-rest-day overtime keeps the existing 2.0x multiplier."""
    pay = calculate_overtime_pay(10000, 4, 'holiday')
    expected = (D('10000') / D('208') * D('4') * D('2.0')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
    assert pay == expected, f'Expected {expected}, got {pay}'


def test_overtime_rest_day_holiday():
    """Public-holiday overtime keeps the existing 2.5x multiplier."""
    pay = calculate_overtime_pay(10000, 2, 'rest_day_holiday')
    expected = (D('10000') / D('208') * D('2') * D('2.5')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
    assert pay == expected, f'Expected {expected}, got {pay}'


def test_overtime_zero_hours():
    assert calculate_overtime_pay(10000, 0, 'day') == D('0')


def test_overtime_invalid_type():
    try:
        calculate_overtime_pay(10000, 4, 'invalid')
        raise AssertionError('Should have raised ValueError')
    except ValueError:
        pass


# --- Total overtime with multiple entries ---


def test_total_overtime_mixed():
    """Multiple overtime entries in a month."""
    entries = [
        {'hours': 4, 'type': 'day'},
        {'hours': 2, 'type': 'night'},
        {'hours': 4, 'type': 'holiday'},
    ]
    result = calculate_total_overtime(10000, entries)

    assert result['total_hours'] == D('10')
    assert len(result['entries']) == 3
    assert not result['exceeds_monthly_limit']  # 10 < 20
    assert len(result['warnings']) == 0


def test_total_overtime_exceeds_limit():
    """Overtime exceeding limits triggers warnings for daily, weekly, and monthly."""
    entries = [{'hours': 25, 'type': 'day'}]
    result = calculate_total_overtime(10000, entries)

    assert result['total_hours'] == D('25')
    assert result['exceeds_monthly_limit']
    # Now warns for daily (25>4), weekly (25>12), and monthly (25>20)
    assert len(result['warnings']) == 3
    assert 'daily limit' in result['warnings'][0]
    assert 'weekly limit' in result['warnings'][1]
    assert 'monthly limit' in result['warnings'][2]


def test_total_overtime_empty():
    result = calculate_total_overtime(10000, [])
    assert result['total_hours'] == D('0')
    assert result['total_pay'] == D('0')
    assert not result['exceeds_monthly_limit']


# --- Rate multiplier verification ---


def test_rate_multipliers():
    """Verify all rate multipliers match Labor Proclamation 1156/2019."""
    assert OVERTIME_RATES['day'] == D('1.50')  # Art. 68(1)(a)
    assert OVERTIME_RATES['night'] == D('1.75')  # Art. 68(1)(b)
    assert OVERTIME_RATES['holiday'] == D('2.00')  # Art. 68(1)(c)
    assert OVERTIME_RATES['rest_day_holiday'] == D('2.50')  # Art. 68(1)(d)


def test_overtime_labels_match_the_existing_rate_categories():
    """Names must describe the configured categories without changing their rates."""
    assert get_overtime_type_label('holiday') == 'Weekly Rest Day (2.00x)'
    assert get_overtime_type_label('rest_day_holiday') == 'Public Holiday (2.50x)'
    assert OVERTIME_RATES['holiday'] == D('2.00')
    assert OVERTIME_RATES['rest_day_holiday'] == D('2.50')


def test_monthly_limit():
    """Verify overtime limits match Ethiopian law."""
    assert MAX_OVERTIME_HOURS_MONTH == 20
    from payroll_engine.overtime import DEFAULT_MAX_HOURS_DAY, DEFAULT_MAX_HOURS_WEEK

    assert DEFAULT_MAX_HOURS_DAY == 4  # Art. 67(2)
    assert DEFAULT_MAX_HOURS_WEEK == 12  # Art. 67(2)


# --- Real-world scenario ---


def test_factory_worker_overtime():
    """
    Factory worker earning 5,000 ETB/month.
    Works 8 hours on a public holiday.
    The full hourly rate is multiplied before the final amount is rounded.
    """
    pay = calculate_overtime_pay(5000, 8, 'holiday')
    expected = (D('5000') / D('208') * D('8') * D('2.0')).quantize(D('0.01'), rounding=ROUND_HALF_UP)
    assert expected == D('384.62')
    assert pay == expected, f'Expected {expected}, got {pay}'
    assert pay > 0


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f'  PASS: {t.__name__}')
            passed += 1
        except (AssertionError, Exception) as e:
            print(f'  FAIL: {t.__name__} — {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
