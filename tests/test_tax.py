"""
Tax calculation tests — covers every bracket boundary.

Proclamation No. 1395/2025 brackets:
    0 – 2,000     : 0%
    2,001 – 4,000 : 15%
    4,001 – 7,000 : 20%
    7,001 – 10,000: 25%
    10,001 – 14,000: 30%
    14,001+       : 35%

No personal relief — removed per Proclamation 1395/2025.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from decimal import Decimal

from tax import calculate_tax

D = Decimal
PERSONAL_RELIEF = D('0')  # Removed — not in Proclamation 1395/2025


# --- Zero and negative ---

def test_tax_zero():
    assert calculate_tax(0) == D('0')

def test_tax_negative():
    assert calculate_tax(-100) == D('0')


# --- Bracket 1: 0-2,000 at 0% ---

def test_tax_at_2000():
    """Top of bracket 1. Tax = 0 (all at 0%)."""
    assert calculate_tax(2000) == D('0')

def test_tax_below_2000():
    assert calculate_tax(1500) == D('0')


# --- Bracket 2: 2,001-4,000 at 15% ---

def test_tax_at_2001():
    """Just into bracket 2. 1 ETB at 15% = 0.15. No relief."""
    result = calculate_tax(2001)
    expected = max(D('0'), D('1') * D('0.15') - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_at_4000():
    """Top of bracket 2. 2000 at 0% + 2000 at 15% = 300. No relief: 150."""
    result = calculate_tax(4000)
    expected = max(D('0'), D('2000') * D('0.15') - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"


# --- Bracket 3: 4,001-7,000 at 20% ---

def test_tax_at_4001():
    """Just into bracket 3. 2000@0% + 2000@15% + 1@20% = 300.2. No relief: 150.2."""
    result = calculate_tax(4001)
    gross_tax = D('2000') * D('0.15') + D('1') * D('0.20')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_at_7000():
    """Top of bracket 3. 2000@0% + 2000@15% + 3000@20% = 900. No relief: 750."""
    result = calculate_tax(7000)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"


# --- Bracket 4: 7,001-10,000 at 25% ---

def test_tax_at_7001():
    """Just into bracket 4. 2000@0% + 2000@15% + 3000@20% + 1@25% = 900.25. No relief: 750.25."""
    result = calculate_tax(7001)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20') + D('1') * D('0.25')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_at_10000():
    """Top of bracket 4. 2000@0% + 2000@15% + 3000@20% + 3000@25% = 1650. No relief: 1500."""
    result = calculate_tax(10000)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20') + D('3000') * D('0.25')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"


# --- Bracket 5: 10,001-14,000 at 30% ---

def test_tax_at_10001():
    """Just into bracket 5. Previous + 1@30% = 1650.3. No relief: 1500.3."""
    result = calculate_tax(10001)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20') + D('3000') * D('0.25') + D('1') * D('0.30')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_at_14000():
    """Top of bracket 5. Previous + 4000@30% = 2850. No relief: 2700."""
    result = calculate_tax(14000)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20') + D('3000') * D('0.25') + D('4000') * D('0.30')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"


# --- Bracket 6: 14,001+ at 35% ---

def test_tax_at_14001():
    """Just into bracket 6. Previous + 1@35% = 2850.35. No relief: 2700.35."""
    result = calculate_tax(14001)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20') + D('3000') * D('0.25') + D('4000') * D('0.30') + D('1') * D('0.35')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_at_20000():
    """High earner. 2000@0% + 2000@15% + 3000@20% + 3000@25% + 4000@30% + 6000@35% = 4950. No relief: 4800."""
    result = calculate_tax(20000)
    gross_tax = D('2000') * D('0.15') + D('3000') * D('0.20') + D('3000') * D('0.25') + D('4000') * D('0.30') + D('6000') * D('0.35')
    expected = max(D('0'), gross_tax - PERSONAL_RELIEF)
    assert result == expected, f"Expected {expected}, got {result}"


# --- Full payroll verification (15,000 ETB with correct deduction order) ---

def test_full_payroll_15000():
    """
    Verify the complete payroll calculation for 15,000 ETB gross.
    This tests the deduction order: Gross → Pension → Tax → Net.

    Gross: 15,000
    Pension (7% of basic 10,000): 700
    Taxable: 15,000 - 700 = 14,300
    Tax on 14,300: 2000@0% + 2000@15% + 3000@20% + 3000@25% + 4000@30% + 300@35%
                 = 0 + 300 + 600 + 750 + 1200 + 105 = 2955
                 minus 150 relief = 2805
    Net: 15,000 - 2805 - 700 = 11,495

    Note: This test verifies tax calculation on the TAXABLE amount (after pension).
    The 15,000 test case from the checklist assumes basic=10,000, allowances=5,000.
    """
    from pension import employee_pension

    gross = D('15000')
    basic = D('10000')  # Pension is on basic salary, not gross
    allowances = D('5000')

    emp_pen = employee_pension(basic)
    assert emp_pen == D('700'), f"Expected pension 700, got {emp_pen}"

    taxable = gross - emp_pen
    assert taxable == D('14300'), f"Expected taxable 14300, got {taxable}"

    tax = calculate_tax(taxable)
    expected_tax = D('2955')
    assert tax == expected_tax, f"Expected tax {expected_tax}, got {tax}"

    net = gross - tax - emp_pen
    expected_net = D('11345')
    assert net == expected_net, f"Expected net {expected_net}, got {net}"


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
