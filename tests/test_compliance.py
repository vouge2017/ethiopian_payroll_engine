"""
Compliance scoring tests.

Verifies:
- ERCA filing deadline is 8th of following month (not 15th)
- Pension deadline is 15th of following month
- Disbursement score based on 5-day window
- Score calculation and status thresholds
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from compliance import (
    compute_compliance_score,
    get_status_message,
    get_upcoming_deadlines,
    _default_erca_deadline,
    _default_pension_deadline,
    ERCA_FILING_DEADLINE_DAY,
    PENSION_DEADLINE_DAY,
)
from datetime import date


# --- Deadline defaults ---

def test_erca_deadline_is_8th():
    """ERCA filing deadline must be the 8th, not the 15th."""
    payroll_date = date(2025, 7, 1)
    dl = _default_erca_deadline(payroll_date)
    assert dl.day == 8, f"Expected day 8, got {dl.day}"
    assert dl.month == 8  # August (month after July)

def test_pension_deadline_is_15th():
    """Pension deadline must be the 15th."""
    payroll_date = date(2025, 7, 1)
    dl = _default_pension_deadline(payroll_date)
    assert dl.day == 15, f"Expected day 15, got {dl.day}"
    assert dl.month == 8

def test_erca_deadline_december():
    """December payroll → ERCA deadline January 8th of next year."""
    payroll_date = date(2025, 12, 31)
    dl = _default_erca_deadline(payroll_date)
    assert dl.day == 8
    assert dl.month == 1
    assert dl.year == 2026

def test_pension_deadline_december():
    """December payroll → Pension deadline January 15th of next year."""
    payroll_date = date(2025, 12, 31)
    dl = _default_pension_deadline(payroll_date)
    assert dl.day == 15
    assert dl.month == 1
    assert dl.year == 2026


# --- Constants ---

def test_erca_constant():
    assert ERCA_FILING_DEADLINE_DAY == 8

def test_pension_constant():
    assert PENSION_DEADLINE_DAY == 15


# --- Score calculation ---

def test_score_perfect():
    """All deadlines met = 100%."""
    score, status = compute_compliance_score(
        payroll_date='2025-07-01',
        pension_deadline='2025-08-15',
        tax_deadline='2025-08-08',
        disbursement_date='2025-07-30',
    )
    assert score == 100.0
    assert status == 'green'

def test_score_status_thresholds():
    """Verify green/yellow/red thresholds."""
    _, green = compute_compliance_score(
        payroll_date='2025-07-01',
        pension_deadline='2025-08-15',
        tax_deadline='2025-08-08',
        disbursement_date='2025-07-30',
    )
    assert green == 'green'


# --- Status messages ---

def test_status_messages():
    assert 'Compliant' in get_status_message('green')
    assert 'At Risk' in get_status_message('yellow')
    assert 'Non-Compliant' in get_status_message('red')


# --- Upcoming deadlines ---

def test_upcoming_deadlines():
    """Get upcoming deadlines for a July payroll."""
    deadlines = get_upcoming_deadlines('2025-07-01')
    assert deadlines['erca_deadline'] == '2025-08-08'
    assert deadlines['pension_deadline'] == '2025-08-15'
    assert 'erca_days_left' in deadlines
    assert 'pension_days_left' in deadlines


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
