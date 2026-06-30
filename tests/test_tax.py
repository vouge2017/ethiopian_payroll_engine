import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'payroll_engine'))
from tax import calculate_tax

def test_tax_bracket_zero():
    assert calculate_tax(1500) == 0.0, f"Expected 0.0, got {calculate_tax(1500)}"

def test_tax_bracket_15():
    # 2000 tax-free, remaining 1000 at 15% = 150, minus 150 relief = 0
    expected = max(0.0, (3000 - 2000) * 0.15 - 150.0)
    result = calculate_tax(3000)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_bracket_20():
    # 2000 @ 0% + 2000 @ 15% + 1000 @ 20% = 0 + 300 + 200 = 500, minus 150 relief = 350
    expected = max(0.0, (2000 * 0.15) + (1000 * 0.20) - 150.0)
    result = calculate_tax(5000)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_bracket_35():
    # 2000@0 + 2000@15% + 3000@20% + 3000@25% + 4000@30% + 6000@35%
    # = 0 + 300 + 600 + 750 + 1200 + 2100 = 4950, minus 150 relief = 4800
    gross_tax = (2000 * 0.15) + (3000 * 0.20) + (3000 * 0.25) + (4000 * 0.30) + (6000 * 0.35)
    expected = max(0.0, gross_tax - 150.0)
    result = calculate_tax(20000)
    assert result == expected, f"Expected {expected}, got {result}"

def test_tax_negative():
    assert calculate_tax(-100) == 0.0

def test_tax_zero():
    assert calculate_tax(0) == 0.0

if __name__ == '__main__':
    tests = [
        test_tax_bracket_zero,
        test_tax_bracket_15,
        test_tax_bracket_20,
        test_tax_bracket_35,
        test_tax_negative,
        test_tax_zero,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
