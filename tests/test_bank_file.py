"""
Bank file generation tests.

Tests the pre-validation engine, CSV generation, and Excel generation
for Ethiopian bank bulk payment files.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.bank_file import (
    format_amount,
    generate_csv,
    validate_account_number,
    validate_payroll_for_bank,
)

# ---------------------------------------------------------------
# Account Validation
# ---------------------------------------------------------------


def test_cbe_valid():
    """13-digit CBE account should pass."""
    valid, err = validate_account_number('1000123456789', 'cbe')
    assert valid is True
    assert err is None


def test_cbe_too_short():
    valid, err = validate_account_number('100012345', 'cbe')
    assert valid is False
    assert '13' in err


def test_cbe_too_long():
    valid, _err = validate_account_number('10001234567890', 'cbe')
    assert valid is False


def test_cbe_letters():
    valid, _err = validate_account_number('1000ABC456789', 'cbe')
    assert valid is False


def test_telebirr_valid():
    """10-digit starting with 09 should pass."""
    valid, _err = validate_account_number('0912345678', 'telebirr')
    assert valid is True


def test_telebirr_07_prefix():
    """10-digit starting with 07 should also pass (Ethio Telecom)."""
    valid, _err = validate_account_number('0712345678', 'telebirr')
    assert valid is True


def test_telebirr_wrong_prefix():
    valid, err = validate_account_number('0512345678', 'telebirr')
    assert valid is False
    assert '09 or 07' in err


def test_empty_account():
    valid, err = validate_account_number('', 'cbe')
    assert valid is False
    assert 'empty' in err.lower()


def test_dashen_valid():
    valid, _err = validate_account_number('1000123456789', 'dashen')
    assert valid is True


def test_awash_valid():
    valid, _err = validate_account_number('1000123456789', 'awash')
    assert valid is True


# ---------------------------------------------------------------
# Amount Formatting
# ---------------------------------------------------------------


def test_format_amount_no_commas():
    """Amounts must have no commas."""
    assert ',' not in format_amount(12500.50)


def test_format_amount_two_decimals():
    """Amounts must have exactly 2 decimal places."""
    assert format_amount(12500.5) == '12500.50'
    assert format_amount(12500) == '12500.00'
    assert format_amount(12500.123) == '12500.12'


def test_format_amount_string_type():
    """format_amount returns string, not number."""
    result = format_amount(1000.00)
    assert isinstance(result, str)


# ---------------------------------------------------------------
# Pre-Validation
# ---------------------------------------------------------------


def test_validate_missing_bank():
    """Employee with no bank account should be flagged."""
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': '', 'net': 5000}]
    errors = validate_payroll_for_bank(employees)
    assert len(errors) == 1
    assert 'missing' in errors[0]['error'].lower()


def test_validate_invalid_account():
    """Employee with bad account number should be flagged."""
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:12345', 'net': 5000}]
    errors = validate_payroll_for_bank(employees)
    assert len(errors) == 1
    assert 'invalid' in errors[0]['error'].lower()


def test_validate_negative_net():
    """Employee with negative net pay should be flagged."""
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': -100}]
    errors = validate_payroll_for_bank(employees)
    assert len(errors) == 1
    assert 'positive' in errors[0]['error'].lower()


def test_validate_all_valid():
    """Valid employees should produce no errors."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'cbe:1000123456789', 'net': 8000},
    ]
    errors = validate_payroll_for_bank(employees, bank='cbe')
    assert len(errors) == 0


def test_validate_multiple_errors():
    """Multiple employees with issues should all be flagged."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': '', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'telebirr:0912345678', 'net': -100},
        {'id': 'E003', 'name': 'Carol', 'bank': 'telebirr:0911111111', 'net': 3000},
    ]
    errors = validate_payroll_for_bank(employees)
    assert len(errors) == 2  # Alice (missing bank) + Bob (negative net)


# ---------------------------------------------------------------
# Duplicate Detection
# ---------------------------------------------------------------


def test_validate_duplicate_employee_id():
    """Same employee appearing twice should be caught."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
    ]
    errors = validate_payroll_for_bank(employees)
    assert any('DUPLICATE' in e['error'] and e.get('severity') == 'BLOCK' for e in errors)


def test_validate_duplicate_bank_account():
    """Two different employees with the same bank account should be caught."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'telebirr:0912345678', 'net': 3000},
    ]
    errors = validate_payroll_for_bank(employees)
    assert any('DUPLICATE ACCOUNT' in e['error'] for e in errors)


def test_validate_different_accounts_ok():
    """Different employees with different accounts should pass."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'telebirr:0987654321', 'net': 3000},
    ]
    errors = validate_payroll_for_bank(employees)
    assert len(errors) == 0


def test_validate_account_change_flagged():
    """Account number changed from previous run should be flagged (not blocked)."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0999999999', 'net': 5000},
    ]
    previous = {
        'E001': {'bank': 'telebirr:0912345678', 'net': 5000},
    }
    errors = validate_payroll_for_bank(employees, previous_payslips=previous)
    assert any('ACCOUNT CHANGED' in e['error'] and e.get('severity') == 'FLAG' for e in errors)


def test_validate_account_change_not_flagged_if_same():
    """Same account as previous run should NOT be flagged."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
    ]
    previous = {
        'E001': {'bank': 'telebirr:0912345678', 'net': 5000},
    }
    errors = validate_payroll_for_bank(employees, previous_payslips=previous)
    assert not any('ACCOUNT CHANGED' in e.get('error', '') for e in errors)


def test_validate_new_employee_no_flag():
    """New employee (not in previous run) should not be flagged for account change."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
    ]
    previous = {
        'E002': {'bank': 'telebirr:0987654321', 'net': 3000},  # Different employee
    }
    errors = validate_payroll_for_bank(employees, previous_payslips=previous)
    assert not any('ACCOUNT CHANGED' in e.get('error', '') for e in errors)


# ---------------------------------------------------------------
# CSV Generation
# ---------------------------------------------------------------


def test_csv_has_headers():
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000}]
    csv_bytes = generate_csv(employees, period='July 2025')
    lines = csv_bytes.decode('utf-8').strip().split('\n')
    assert 'account_number' in lines[0]
    assert 'amount' in lines[0]


def test_csv_account_is_text():
    """Account number in CSV must be a plain string, not scientific notation."""
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'bank:cbe:1000123456789', 'net': 5000}]
    csv_bytes = generate_csv(employees, bank='cbe', period='July 2025')
    content = csv_bytes.decode('utf-8')
    assert '1000123456789' in content
    assert 'E+' not in content  # No scientific notation
    assert 'e+' not in content


def test_csv_amount_no_commas():
    """Amounts must not have commas."""
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 12500.50}]
    csv_bytes = generate_csv(employees, period='July 2025')
    content = csv_bytes.decode('utf-8')
    assert '12,500' not in content
    assert '12500.50' in content


def test_csv_uses_net_pay():
    """CSV amount should be net pay, not gross."""
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 7481.00}]
    csv_bytes = generate_csv(employees, period='July 2025')
    content = csv_bytes.decode('utf-8')
    assert '7481.00' in content


def test_csv_currency_is_etb():
    employees = [{'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000}]
    csv_bytes = generate_csv(employees, period='July 2025')
    content = csv_bytes.decode('utf-8')
    assert 'ETB' in content


def test_csv_narrative_includes_id_and_name():
    """Narrative should include employee ID to disambiguate same names."""
    employees = [{'id': 'E001', 'name': 'Abebe Kebede', 'bank': 'telebirr:0912345678', 'net': 5000}]
    csv_bytes = generate_csv(employees, period='July 2025')
    content = csv_bytes.decode('utf-8')
    assert 'E001' in content
    assert 'Abebe Kebede' in content
    assert 'July 2025' in content


def test_csv_same_name_different_ids():
    """Two employees with same name but different IDs should have different narratives."""
    employees = [
        {'id': 'E001', 'name': 'Abebe Kebede', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E002', 'name': 'Abebe Kebede', 'bank': 'telebirr:0987654321', 'net': 3000},
    ]
    csv_bytes = generate_csv(employees, period='July 2025')
    lines = csv_bytes.decode('utf-8').strip().split('\n')
    # Both lines should have the name, but with different IDs
    assert 'E001 Abebe Kebede' in lines[1]
    assert 'E002 Abebe Kebede' in lines[2]


def test_csv_multiple_employees():
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'telebirr:0987654321', 'net': 8000},
    ]
    csv_bytes = generate_csv(employees, period='July 2025')
    lines = csv_bytes.decode('utf-8').strip().split('\n')
    assert len(lines) == 3  # header + 2 data rows
