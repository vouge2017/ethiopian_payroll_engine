"""
Overtime rate calculation tests.

Labor Proclamation No. 1156/2019, Article 68:
    Regular day: 1.25x, Night: 1.5x, Holiday: 2.0x, Rest day holiday: 2.5x

Hourly rate = basic_salary / 30 / 8
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from overtime import (
    calculate_hourly_rate,
    calculate_overtime_pay,
    calculate_total_overtime,
    OVERTIME_RATES,
    MAX_OVERTIME_HOURS_MONTH,
)


# --- Hourly rate ---

def test_hourly_rate_basic():
    """10,000 ETB / 30 days / 8 hours = 41.67 ETB/hour"""
    rate = calculate_hourly_rate(10000)
    expected = round(10000 / 30 / 8, 2)
    assert rate == expected, f"Expected {expected}, got {rate}"

def test_hourly_rate_zero():
    assert calculate_hourly_rate(0) == 0.0

def test_hourly_rate_negative():
    assert calculate_hourly_rate(-5000) == 0.0

def test_hourly_rate_15000():
    """15,000 / 30 / 8 = 62.50"""
    rate = calculate_hourly_rate(15000)
    assert rate == 62.50, f"Expected 62.50, got {rate}"


# --- Overtime pay by type ---

def test_overtime_day():
    """10,000 salary, 4 hours day overtime: 41.67 × 4 × 1.25 = 208.35"""
    pay = calculate_overtime_pay(10000, 4, 'day')
    hourly = round(10000 / 30 / 8, 2)
    expected = round(hourly * 4 * 1.25, 2)
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_night():
    """10,000 salary, 3 hours night: 41.67 × 3 × 1.50 = 187.52"""
    pay = calculate_overtime_pay(10000, 3, 'night')
    hourly = round(10000 / 30 / 8, 2)
    expected = round(hourly * 3 * 1.50, 2)
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_holiday():
    """10,000 salary, 4 hours holiday: 41.67 × 4 × 2.0 = 333.36"""
    pay = calculate_overtime_pay(10000, 4, 'holiday')
    hourly = round(10000 / 30 / 8, 2)
    expected = round(hourly * 4 * 2.0, 2)
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_rest_day_holiday():
    """10,000 salary, 2 hours rest day holiday: 41.67 × 2 × 2.5 = 208.35"""
    pay = calculate_overtime_pay(10000, 2, 'rest_day_holiday')
    hourly = round(10000 / 30 / 8, 2)
    expected = round(hourly * 2 * 2.5, 2)
    assert pay == expected, f"Expected {expected}, got {pay}"

def test_overtime_zero_hours():
    assert calculate_overtime_pay(10000, 0, 'day') == 0.0

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

    assert result['total_hours'] == 10.0
    assert len(result['entries']) == 3
    assert not result['exceeds_monthly_limit']  # 10 < 20
    assert len(result['warnings']) == 0

def test_total_overtime_exceeds_limit():
    """Overtime exceeding 20-hour monthly limit triggers warning."""
    entries = [{'hours': 25, 'type': 'day'}]
    result = calculate_total_overtime(10000, entries)

    assert result['total_hours'] == 25.0
    assert result['exceeds_monthly_limit']
    assert len(result['warnings']) == 1
    assert '20-hour monthly limit' in result['warnings'][0]

def test_total_overtime_empty():
    result = calculate_total_overtime(10000, [])
    assert result['total_hours'] == 0.0
    assert result['total_pay'] == 0.0
    assert not result['exceeds_monthly_limit']


# --- Rate multiplier verification ---

def test_rate_multipliers():
    """Verify all rate multipliers match Labor Proclamation 1156/2019."""
    assert OVERTIME_RATES['day'] == 1.25      # Art. 68(1)
    assert OVERTIME_RATES['night'] == 1.50     # Art. 68(2)
    assert OVERTIME_RATES['holiday'] == 2.00   # Art. 68(3)
    assert OVERTIME_RATES['rest_day_holiday'] == 2.50  # Art. 68(4)

def test_monthly_limit():
    """Verify monthly overtime limit matches Art. 89."""
    assert MAX_OVERTIME_HOURS_MONTH == 20


# --- Real-world scenario ---

def test_factory_worker_overtime():
    """
    Factory worker earning 5,000 ETB/month.
    Works 8 hours on a public holiday.
    Hourly: 5000 / 30 / 8 = 20.83
    Overtime: 20.83 × 8 × 2.0 = 333.28
    """
    pay = calculate_overtime_pay(5000, 8, 'holiday')
    hourly = round(5000 / 30 / 8, 2)
    expected = round(hourly * 8 * 2.0, 2)
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
