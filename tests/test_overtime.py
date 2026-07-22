"""
Overtime rate calculation tests.

Labor Proclamation No. 1156/2019, Article 68:
    Regular day: 1.25x, Night: 1.5x, Holiday: 2.0x, Rest day holiday: 2.5x

Hourly rate = basic_salary / 208 (26 working days × 8 hours)
Per Ethiopian labor law: 48 hours/week, 6 days/week, 26 days/month.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from overtime import (
    calculate_hourly_rate,
    calculate_overtime_pay,
    calculate_total_overtime,
    DEFAULT_OVERTIME_RATES as OVERTIME_RATES,
    DEFAULT_MAX_HOURS_MONTH as MAX_OVERTIME_HOURS_MONTH,
)
from decimal import Decimal

D = Decimal


# --- Hourly rate ---

def test_hourly_rate_basic():
    """10,000 ETB / 208 hours = 48.08 ETB/hour"""
    rate = calculate_hourly_rate(10000)
    expected = (D('10000') / D('208')).quantize(D('0.01'))
    assert rate == expected, f"Expected {expected}, got {rate}"

def test_hourly_rate_zero():
    assert calculate_hourly_rate(0) == D('0')

def test_hourly_rate_negative():
    assert calculate_hourly_rate(-5000) == D('0')

def test_hourly_rate_15000():
    """15,000 / 208 = 72.12"""
    rate = calculate_hourly_rate(15000)
    expected = (D('15000') / D('208')).quantize(D('0.01'))
    assert rate == expected, f"Expected {expected}, got {rate}"


# --- Overtime pay by type ---

def test_overtime_day():
    """10,000 salary, 4 hours day overtime: 48.08 × 4 × 1.25 = 240.40"""
    pay = calculate_overtime_pay(10000, 4, 'day')
    hourly = (D('10000') / D('208')).quantize(D('0.01'))
    expected = (hourly * D('4') * D('1.25')).quantize(D('0.01'))
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_night():
    """10,000 salary, 3 hours night: 48.08 × 3 × 1.50 = 216.36"""
    pay = calculate_overtime_pay(10000, 3, 'night')
    hourly = (D('10000') / D('208')).quantize(D('0.01'))
    expected = (hourly * D('3') * D('1.50')).quantize(D('0.01'))
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_holiday():
    """10,000 salary, 4 hours holiday: 48.08 × 4 × 2.0 = 384.64"""
    pay = calculate_overtime_pay(10000, 4, 'holiday')
    hourly = (D('10000') / D('208')).quantize(D('0.01'))
    expected = (hourly * D('4') * D('2.0')).quantize(D('0.01'))
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_rest_day_holiday():
    """10,000 salary, 2 hours rest day holiday: 48.08 × 2 × 2.5 = 240.40"""
    pay = calculate_overtime_pay(10000, 2, 'rest_day_holiday')
    hourly = (D('10000') / D('208')).quantize(D('0.01'))
    expected = (hourly * D('2') * D('2.5')).quantize(D('0.01'))
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_zero_hours():
    assert calculate_overtime_pay(10000, 0, 'day') == D('0')

def test_overtime_invalid_type():
    try:
        calculate_overtime_pay(10000, 4, 'invalid')
        assert False, "Should have raised ValueError"
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
    """Overtime exceeding 20-hour monthly limit triggers warning."""
    entries = [{'hours': 25, 'type': 'day'}]
    result = calculate_total_overtime(10000, entries)

    assert result['total_hours'] == D('25')
    assert result['exceeds_monthly_limit']
    assert len(result['warnings']) == 1
    assert '20-hour monthly limit' in result['warnings'][0]

def test_total_overtime_empty():
    result = calculate_total_overtime(10000, [])
    assert result['total_hours'] == D('0')
    assert result['total_pay'] == D('0')
    assert not result['exceeds_monthly_limit']


# --- Rate multiplier verification ---

def test_rate_multipliers():
    """Verify all rate multipliers match Labor Proclamation 1156/2019."""
    assert OVERTIME_RATES['day'] == D('1.25')      # Art. 68(1)
    assert OVERTIME_RATES['night'] == D('1.50')     # Art. 68(2)
    assert OVERTIME_RATES['holiday'] == D('2.00')   # Art. 68(3)
    assert OVERTIME_RATES['rest_day_holiday'] == D('2.50')  # Art. 68(4)

def test_monthly_limit():
    """Verify monthly overtime limit matches Art. 89."""
    assert MAX_OVERTIME_HOURS_MONTH == 20


# --- Real-world scenario ---

def test_factory_worker_overtime():
    """
    Factory worker earning 5,000 ETB/month.
    Works 8 hours on a public holiday.
    Hourly: 5000 / 208 = 24.04
    Overtime: 24.04 × 8 × 2.0 = 384.64
    """
    pay = calculate_overtime_pay(5000, 8, 'holiday')
    hourly = (D('5000') / D('208')).quantize(D('0.01'))
    expected = (hourly * D('8') * D('2.0')).quantize(D('0.01'))
    assert pay == expected, f"Expected {expected}, got {pay}"
    assert pay > 0


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"  FAIL: {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
