"""
Cash compliance validation tests.

Ethiopian law (Proclamation No. 1395/2025, Article 81) requires electronic
payment for salaries above ETB 50,000. The system flags this as a FLAG
(not BLOCK) — it informs the owner but does not prevent payroll from proceeding.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.validation import validate_payroll_data


def _make_emp(name='Dawit Mekonnen', net=55000, bank=''):
    """Helper to create a minimal employee data dict."""
    return {
        'id': 'EMP001',
        'name': name,
        'basic': 45000,
        'allowances': 10000,
        'gross': 55000,
        'taxable': 51850,
        'tax': 12500,
        'pension_employee': 3150,
        'pension_employer': 4950,
        'net': net,
        'bank': bank,
        'tin': '',
    }


def test_cash_compliance_flag_when_over_limit_no_bank():
    """Net pay > 50,000 AND no bank account → FLAG."""
    employees = [_make_emp(net=55000, bank='')]
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 1
    assert cash_flags[0].severity == 'FLAG'
    assert '55,000' in cash_flags[0].message
    assert '50,000' in cash_flags[0].message
    assert cash_flags[0].employee_name == 'Dawit Mekonnen'
    assert 'bank account' in cash_flags[0].hint.lower()


def test_cash_compliance_ok_when_has_bank():
    """Net pay > 50,000 BUT has bank account → no flag."""
    employees = [_make_emp(net=55000, bank='telebirr:0911234567')]
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 0


def test_cash_compliance_ok_when_under_limit():
    """Net pay < 50,000 AND no bank → no flag (under limit)."""
    employees = [_make_emp(net=40000, bank='')]
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 0


def test_cash_compliance_exactly_at_limit():
    """Net pay == 50,000 → no flag (at limit, not above)."""
    employees = [_make_emp(net=50000, bank='')]
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 0


def test_cash_compliance_one_above_limit():
    """Net pay == 50,001 → FLAG."""
    employees = [_make_emp(net=50001, bank='')]
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 1
    assert cash_flags[0].severity == 'FLAG'


def test_cash_compliance_multiple_employees():
    """Mixed scenario: one over no bank, one over with bank, one under."""
    employees = [
        _make_emp(name='Alemayehu', net=55000, bank=''),           # FLAG
        _make_emp(name='Tigist', net=60000, bank='cbe:1000123'),   # OK
        _make_emp(name='Hana', net=30000, bank=''),                # OK (under limit)
    ]
    # Fix IDs to avoid duplicate check
    employees[0]['id'] = 'EMP001'
    employees[1]['id'] = 'EMP002'
    employees[2]['id'] = 'EMP003'
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 1
    assert cash_flags[0].employee_name == 'Alemayehu'


def test_cash_compliance_does_not_block():
    """CASH_COMPLIANCE is a FLAG, never a BLOCK.

    We can't test can_proceed directly because MISSING_BANK is also
    triggered for the same employee (no bank). Instead, verify that
    CASH_COMPLIANCE itself has severity='FLAG'.
    """
    employees = [_make_emp(net=75000, bank='')]
    results = validate_payroll_data(employees)
    cash_flags = [r for r in results if r.rule_code == 'CASH_COMPLIANCE']
    assert len(cash_flags) == 1
    assert cash_flags[0].severity == 'FLAG'  # Not BLOCK
    # Verify MISSING_BANK is the blocker, not CASH_COMPLIANCE
    from payroll_engine.validation import get_summary
    summary = get_summary(results)
    assert summary['blocks'] == 1  # Only MISSING_BANK blocks
    block_codes = [r.rule_code for r in results if r.severity == 'BLOCK' and not r.overridden]
    assert 'MISSING_BANK' in block_codes
    assert 'CASH_COMPLIANCE' not in block_codes
