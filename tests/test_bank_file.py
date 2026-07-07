"""
Bank file generation tests.

Tests the pre-validation engine, CSV generation, and Excel generation
for Ethiopian bank bulk payment files.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.bank_file import (
    validate_account_number,
    format_amount,
    validate_payroll_for_bank,
    generate_csv,
    generate_xlsx,
    ACCOUNT_PATTERNS,
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
    valid, err = validate_account_number('10001234567890', 'cbe')
    assert valid is False


def test_cbe_letters():
    valid, err = validate_account_number('1000ABC456789', 'cbe')
    assert valid is False


def test_telebirr_valid():
    """10-digit starting with 09 should pass."""
    valid, err = validate_account_number('0912345678', 'telebirr')
    assert valid is True


def test_telebirr_07_prefix():
    """10-digit starting with 07 should also pass (Ethio Telecom)."""
    valid, err = validate_account_number('0712345678', 'telebirr')
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
    valid, err = validate_account_number('1000123456789', 'dashen')
    assert valid is True


def test_awash_valid():
    valid, err = validate_account_number('1000123456789', 'awash')
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
        {'id': 'E002', 'name': 'Bob', 'bank': 'bank:cbe:1000123456789', 'net': 8000},
    ]
    errors = validate_payroll_for_bank(employees, bank='cbe')
    assert len(errors) == 0


def test_validate_multiple_errors():
    """Multiple employees with issues should all be flagged."""
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': '', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'telebirr:0912345678', 'net': -100},
        {'id': 'E003', 'name': 'Carol', 'bank': 'telebirr:0912345678', 'net': 3000},
    ]
    errors = validate_payroll_for_bank(employees)
    assert len(errors) == 2  # Alice (missing bank) + Bob (negative net)


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


def test_csv_narrative_includes_name():
    employees = [{'id': 'E001', 'name': 'Abebe Kebede', 'bank': 'telebirr:0912345678', 'net': 5000}]
    csv_bytes = generate_csv(employees, period='July 2025')
    content = csv_bytes.decode('utf-8')
    assert 'Abebe Kebede' in content
    assert 'July 2025' in content


def test_csv_multiple_employees():
    employees = [
        {'id': 'E001', 'name': 'Alice', 'bank': 'telebirr:0912345678', 'net': 5000},
        {'id': 'E002', 'name': 'Bob', 'bank': 'telebirr:0987654321', 'net': 8000},
    ]
    csv_bytes = generate_csv(employees, period='July 2025')
    lines = csv_bytes.decode('utf-8').strip().split('\n')
    assert len(lines) == 3  # header + 2 data rows
