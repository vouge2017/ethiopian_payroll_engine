"""
Severance pay calculation tests.

Labor Proclamation No. 1156/2019, Articles 40-42:
    Formula: monthly_salary × years_of_service
    Cap: 12 months of salary
    Eligible: redundancy, mutual agreement
    Not eligible: resignation, termination for cause
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from severance import (
    calculate_years_of_service,
    calculate_severance,
    TerminationReason,
    MAX_SEVERANCE_MONTHS,
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


# --- Calculation ---

def test_severance_simple():
    """8,000 × 5 years = 40,000."""
    result = calculate_severance(8000, '2020-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    assert result['final_amount'] == 40000.0

def test_severance_partial_year():
    """8,000 × 5.5 years = 44,000."""
    result = calculate_severance(8000, '2020-01-01', '2025-07-01', 'redundancy')
    assert result['eligible']
    expected = round(8000 * result['years_of_service'], 2)
    assert result['final_amount'] == expected

def test_severance_cap():
    """Cap at 12 months. 8,000 × 15 years = 120,000, capped at 96,000."""
    result = calculate_severance(8000, '2010-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    assert result['calculated_amount'] > result['capped_amount']
    assert result['final_amount'] == 8000 * 12  # 96,000

def test_severance_at_cap_boundary():
    """Exactly 12 years: 8,000 × 12 = 96,000 (at cap, not over)."""
    result = calculate_severance(8000, '2013-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    assert result['final_amount'] <= 8000 * 12

def test_severance_zero_salary():
    result = calculate_severance(0, '2020-01-01', '2025-01-01', 'redundancy')
    assert result['eligible']
    assert result['final_amount'] == 0.0


# --- Real-world scenario ---

def test_factory_worker_severance():
    """
    Factory worker: 5,000 ETB/month, worked 3.5 years, made redundant.
    Severance: 5,000 × 3.5 = 17,500 ETB
    """
    result = calculate_severance(5000, '2022-06-01', '2026-01-01', 'redundancy')
    assert result['eligible']
    expected = round(5000 * result['years_of_service'], 2)
    assert result['final_amount'] == expected
    assert result['final_amount'] > 15000  # Should be around 17,500


def test_max_severance_constant():
    """Verify the 12-month cap constant matches Art. 42."""
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
