"""
Severance pay calculation tests.

Labor Proclamation No. 1156/2019, Article 40:
    Year 1: 30 days of average daily wages
    Each additional year: +1/3 of base (≈10 days)
    Cap: 12 months of salary

Formula: daily_rate × total_days
    daily_rate = monthly_salary / 30
    total_days = 30 + (years - 1) × 10  (for years >= 1)
    total_days = years × 30             (for years < 1, prorated)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from decimal import Decimal as D
from severance import (
    calculate_years_of_service,
    calculate_severance,
    TerminationReason,
    DEFAULT_MAX_SEVERANCE_MONTHS as MAX_SEVERANCE_MONTHS,
)


# --- Years of service ---

def test_years_exact():
    """Exactly 5 years."""
    years = calculate_years_of_service('2020-01-01', '2025-01-01')
    assert 4.99 < years < 5.01, f"Expected ~5.0, got {years}"

def test_years_partial():
    """5 years and 6 months."""
    years = calculate_years_of_service('2020-01-01', '2025-07-01')
    assert 5.4 < years < 5.6, f"Expected ~5.5, got {years}"

def test_years_same_date():
    """Same start and end = 0 years."""
    years = calculate_years_of_service('2025-01-01', '2025-01-01')
    assert years == 0.0

def test_years_end_before_start():
    """End before start = 0."""
    years = calculate_years_of_service('2025-01-01', '2020-01-01')
    assert years == 0.0


# --- Eligibility ---

def test_severance_redundancy_eligible():
    result = calculate_severance(8000, '2020-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    assert result['final_amount'] > 0

def test_severance_mutual_agreement_eligible():
    result = calculate_severance(8000, '2020-01-01', '2025-01-01', 'mutual_agreement')
    assert result['eligible']
    assert result['final_amount'] > 0

def test_severance_resignation_not_eligible():
    result = calculate_severance(8000, '2020-01-01', '2025-01-01', 'resignation')
    assert not result['eligible']
    assert result['final_amount'] == 0.0
    assert 'Resignation' in result['reason']

def test_severance_for_cause_not_eligible():
    result = calculate_severance(8000, '2020-01-01', '2025-01-01', 'termination_for_cause')
    assert not result['eligible']
    assert result['final_amount'] == 0.0
    assert 'cause' in result['reason'].lower()


# --- Calculation (Art. 40 formula) ---

def test_severance_simple():
    """5 years, salary 8000. Art. 40: 30 + 4×10 = 70 days."""
    result = calculate_severance(8000, '2020-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    # Result is calculated by the engine — verify it's reasonable
    daily = D('8000') / D('30')
    min_expected = (daily * 70).quantize(D('0.01'))
    # Allow small rounding difference
    assert abs(result['final_amount'] - min_expected) < 50, \
        f"Expected ~{min_expected}, got {result['final_amount']}"

def test_severance_partial_year():
    """5.5 years, salary 8000. 30 + 4.5×10 = 75 days."""
    result = calculate_severance(8000, '2020-01-01', '2025-07-01', 'redundancy')
    assert result['eligible']
    daily = D('8000') / D('30')
    min_expected = (daily * 75).quantize(D('0.01'))
    assert abs(result['final_amount'] - min_expected) < 50, \
        f"Expected ~{min_expected}, got {result['final_amount']}"

def test_severance_cap():
    """15 years: 30 + 14×10 = 170 days. Cap is 360 days (12 months)."""
    result = calculate_severance(8000, '2010-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    daily = D('8000') / D('30')
    min_expected = (daily * 170).quantize(D('0.01'))
    assert abs(result['final_amount'] - min_expected) < 50

def test_severance_at_cap_boundary():
    """40 years would exceed cap. Cap = 12 months = 360 days."""
    result = calculate_severance(8000, '1985-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    daily = D('8000') / D('30')
    cap_amount = (daily * 360).quantize(D('0.01'))
    assert abs(result['final_amount'] - cap_amount) < 50

def test_severance_zero_salary():
    result = calculate_severance(0, '2020-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    assert result['final_amount'] == 0.0


# --- Real-world scenario ---

def test_factory_worker_severance():
    """Factory worker: 5,000 ETB/month, worked ~3.5 years, made redundant."""
    result = calculate_severance(5000, '2022-06-01', '2026-01-01', 'redundancy')
    assert result['eligible']
    assert result['final_amount'] > 8000  # Should be around 9000-9500
    assert result['final_amount'] < 12000


def test_max_severance_constant():
    """Verify the 12-month cap constant matches Art. 40(3)."""
    assert MAX_SEVERANCE_MONTHS == 12


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
