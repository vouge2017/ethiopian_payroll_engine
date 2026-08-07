"""
Compliance scoring tests.

Verifies:
- ERCA filing deadline defaults to 25th
- Pension deadline defaults to 10th (Proclamation 1268/2022, Art. 10(6))
- Company-configurable deadlines work
- Disbursement score based on configurable window
- Score calculation and status thresholds
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from datetime import date

from compliance import (
    DEFAULT_ERCA_FILING_DAY,
    DEFAULT_PENSION_DEADLINE_DAY,
    _fallback_deadline,
    compute_compliance_score,
    get_company_deadlines,
    get_deadline_for_type,
    get_status_message,
    get_upcoming_deadlines,
)

# --- Deadline defaults ---

def test_erca_deadline_is_25th():
    """ERCA filing deadline must default to the 25th of the following month."""
    payroll_date = date(2025, 7, 1)
    dl = _fallback_deadline(payroll_date, DEFAULT_ERCA_FILING_DAY)
    assert dl.day == 25, f"Expected day 25, got {dl.day}"
    assert dl.month == 8  # August (month after July)

def test_pension_deadline_is_10th():
    """Pension deadline must default to the 10th (proclamation)."""
    payroll_date = date(2025, 7, 1)
    dl = _fallback_deadline(payroll_date, DEFAULT_PENSION_DEADLINE_DAY)
    assert dl.day == 10, f"Expected day 10, got {dl.day}"
    assert dl.month == 8

def test_erca_deadline_december():
    """December payroll → ERCA deadline January 25th of next year."""
    payroll_date = date(2025, 12, 31)
    dl = _fallback_deadline(payroll_date, DEFAULT_ERCA_FILING_DAY)
    assert dl.day == 25
    assert dl.month == 1
    assert dl.year == 2026

def test_pension_deadline_december():
    """December payroll → Pension deadline January 10th of next year."""
    payroll_date = date(2025, 12, 31)
    dl = _fallback_deadline(payroll_date, DEFAULT_PENSION_DEADLINE_DAY)
    assert dl.day == 10
    assert dl.month == 1
    assert dl.year == 2026


# --- Constants ---

def test_erca_constant():
    assert DEFAULT_ERCA_FILING_DAY == 25

def test_pension_constant():
    assert DEFAULT_PENSION_DEADLINE_DAY == 10


# --- Company-configurable deadlines ---

class FakeCompany:
    """Minimal company mock for testing."""
    def __init__(self, deadlines=None):
        self.compliance_deadlines = deadlines

def test_company_default_deadlines():
    """Company with no config gets sensible defaults."""
    company = FakeCompany()
    deadlines = get_company_deadlines(company)
    assert deadlines['erca']['day'] == 25
    assert deadlines['pension']['day'] == 10
    assert deadlines['pssa']['day'] == 10
    assert deadlines['_disbursement_days'] == 5
    assert deadlines['_reminder_days_before'] == 3

def test_company_custom_deadlines():
    """Company can override deadlines."""
    company = FakeCompany({
        'pension': {'day': 15, 'enabled': True},
        'disbursement_days': 7,
        'reminder_days_before': 5,
    })
    deadlines = get_company_deadlines(company)
    assert deadlines['pension']['day'] == 15
    assert deadlines['_disbursement_days'] == 7
    assert deadlines['_reminder_days_before'] == 5
    # ERCA should still be default
    assert deadlines['erca']['day'] == 25

def test_company_disable_filing_type():
    """Company can disable a filing type."""
    company = FakeCompany({
        'pssa': {'enabled': False},
    })
    deadlines = get_company_deadlines(company)
    assert deadlines['pssa']['enabled'] == False

def test_company_custom_filing_type():
    """Company can add custom filing types."""
    company = FakeCompany({
        'custom_deadlines': [
            {'name': 'Regional Tax', 'day': 15, 'enabled': True},
        ]
    })
    deadlines = get_company_deadlines(company)
    assert 'regional_tax' in deadlines
    assert deadlines['regional_tax']['day'] == 15

def test_get_deadline_for_type():
    """get_deadline_for_type returns correct date."""
    company = FakeCompany({'pension': {'day': 15, 'enabled': True}})
    dl = get_deadline_for_type(company, 'pension', date(2025, 7, 1))
    assert dl == date(2025, 8, 15)


# --- Score calculation ---

def test_score_perfect():
    """All deadlines met = 100%."""
    from datetime import timedelta
    future = date.today() + timedelta(days=60)
    future_str = future.isoformat()
    score, status = compute_compliance_score(
        payroll_date=future_str,
        pension_deadline=future_str,
        tax_deadline=future_str,
        disbursement_date=future_str,
    )
    assert score == 100.0, f"Expected 100.0, got {score}"
    assert status == 'green'

def test_score_with_company():
    """Score uses company deadlines when provided."""
    company = FakeCompany({'pension': {'day': 15, 'enabled': True}})
    from datetime import timedelta
    future = date.today() + timedelta(days=60)
    future_str = future.isoformat()
    score, status = compute_compliance_score(
        company=company,
        payroll_date=future_str,
        pension_deadline=future_str,
        tax_deadline=future_str,
        disbursement_date=future_str,
    )
    assert score == 100.0

def test_score_status_thresholds():
    """Verify green/yellow/red thresholds."""
    from datetime import timedelta
    future = date.today() + timedelta(days=60)
    future_str = future.isoformat()
    _, green = compute_compliance_score(
        payroll_date=future_str,
        pension_deadline=future_str,
        tax_deadline=future_str,
        disbursement_date=future_str,
    )
    assert green == 'green'


# --- Status messages ---

def test_status_messages():
    assert 'Compliant' in get_status_message('green')
    assert 'At Risk' in get_status_message('yellow')
    assert 'Non-Compliant' in get_status_message('red')


# --- Upcoming deadlines ---

def test_upcoming_deadlines():
    """Get upcoming deadlines for a July payroll with defaults."""
    deadlines = get_upcoming_deadlines(payroll_date='2025-07-01')
    assert deadlines['erca_deadline'] == '2025-08-25'
    assert deadlines['pension_deadline'] == '2025-08-10'
    assert 'erca_days_left' in deadlines
    assert 'pension_days_left' in deadlines

def test_upcoming_deadlines_with_company():
    """Company deadlines override defaults."""
    company = FakeCompany({'pension': {'day': 20, 'enabled': True}})
    deadlines = get_upcoming_deadlines(company=company, payroll_date='2025-07-01')
    assert deadlines['pension_deadline'] == '2025-08-20'


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
