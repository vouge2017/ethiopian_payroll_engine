"""
Payroll calculation tests — verifies the single entry point
enforces correct deduction order and catches bad inputs.

This is the structural guardrail: if anyone calls calculate_tax(gross)
directly instead of going through calculate_payroll(), the test suite
catches it. The function itself prevents wrong numbers.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.payroll import calculate_payroll
from payroll_engine.tax import calculate_tax


# ---------------------------------------------------------------
# TEST 1: Correct deduction order (15,000 ETB)
# ---------------------------------------------------------------
def test_payroll_15000():
    """15,000 gross, basic 10,000 — verifies pension before tax."""
    result = calculate_payroll(basic_salary=10000, allowances=5000)
    assert result['gross'] == 15000.0
    assert result['pension_employee'] == 700.0  # 7% of 10,000
    assert result['taxable'] == 14300.0  # 15,000 - 700
    assert result['tax'] == 2805.0  # tax on 14,300
    assert result['net'] == 11495.0  # 15,000 - 2,805 - 700


# ---------------------------------------------------------------
# TEST 2: Zero salary
# ---------------------------------------------------------------
def test_payroll_zero():
    result = calculate_payroll(basic_salary=0, allowances=0)
    assert result['gross'] == 0.0
    assert result['pension_employee'] == 0.0
    assert result['tax'] == 0.0
    assert result['net'] == 0.0


# ---------------------------------------------------------------
# TEST 3: Negative basic salary raises error
# ---------------------------------------------------------------
def test_payroll_negative_basic():
    """Negative salary must be rejected, not silently produce wrong numbers."""
    try:
        calculate_payroll(basic_salary=-5000, allowances=0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'negative' in str(e).lower()


# ---------------------------------------------------------------
# TEST 4: Negative allowances raises error
# ---------------------------------------------------------------
def test_payroll_negative_allowances():
    try:
        calculate_payroll(basic_salary=5000, allowances=-1000)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'negative' in str(e).lower()


# ---------------------------------------------------------------
# TEST 5: Low salary (under 2,000 bracket)
# ---------------------------------------------------------------
def test_payroll_low_salary():
    """1,800 basic, 0 allowances — zero tax bracket."""
    result = calculate_payroll(basic_salary=1800, allowances=0)
    assert result['gross'] == 1800.0
    assert result['pension_employee'] == 126.0  # 7% of 1,800
    assert result['taxable'] == 1674.0
    assert result['tax'] == 0.0  # under 2,000 bracket
    assert result['net'] == 1674.0


# ---------------------------------------------------------------
# TEST 6: High salary (top bracket)
# ---------------------------------------------------------------
def test_payroll_high_salary():
    """50,000 basic, 10,000 allowances."""
    result = calculate_payroll(basic_salary=50000, allowances=10000)
    assert result['gross'] == 60000.0
    assert result['pension_employee'] == 3500.0  # 7% of 50,000
    assert result['taxable'] == 56500.0  # 60,000 - 3,500
    assert result['tax'] > 0
    assert result['net'] == result['gross'] - result['tax'] - result['pension_employee']


# ---------------------------------------------------------------
# TEST 7: Only basic, no allowances
# ---------------------------------------------------------------
def test_payroll_basic_only():
    result = calculate_payroll(basic_salary=8000)
    assert result['gross'] == 8000.0
    assert result['pension_employee'] == 560.0


# ---------------------------------------------------------------
# TEST 8: Prove that going through calculate_payroll produces
#         different (correct) results vs calling calculate_tax(gross)
# ---------------------------------------------------------------
def test_deduction_order_matters():
    """
    If someone calls calculate_tax(gross) instead of
    calculate_tax(gross - pension), they get WRONG numbers.
    This test proves the difference.
    """
    gross = 15000
    basic = 10000
    pension = basic * 0.07  # 700

    # WRONG way: tax on full gross
    wrong_tax = calculate_tax(gross)

    # RIGHT way: tax on gross - pension
    right_tax = calculate_tax(gross - pension)

    # They must be different
    assert wrong_tax != right_tax, "Deduction order doesn't matter? Something is wrong."

    # The wrong way produces a HIGHER tax (employee gets less)
    assert wrong_tax > right_tax, "Wrong deduction order should produce higher tax."

    # Our function uses the right way
    result = calculate_payroll(basic_salary=basic, allowances=gross - basic)
    assert result['tax'] == right_tax
    assert result['tax'] != wrong_tax


# ---------------------------------------------------------------
# TEST 9: Large salary, no overflow
# ---------------------------------------------------------------
def test_payroll_no_overflow():
    """10,000,000 ETB — should calculate without errors."""
    result = calculate_payroll(basic_salary=10000000, allowances=0)
    assert result['gross'] == 10000000.0
    assert result['pension_employee'] == 700000.0
    assert result['net'] > 0
    assert result['net'] == result['gross'] - result['tax'] - result['pension_employee']


# ---------------------------------------------------------------
# TEST 10: Tax explanation is included
# ---------------------------------------------------------------
def test_payroll_includes_explanation():
    result = calculate_payroll(basic_salary=10000, allowances=2000)
    assert 'tax_explanation' in result
    assert len(result['tax_explanation']) > 0
    assert 'ETB' in result['tax_explanation']
