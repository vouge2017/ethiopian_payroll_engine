"""
Bank File Generator — Ethiopian Payroll Engine

Generates bulk payment files for Ethiopian banks and mobile wallets.
Supports: CBE, Dashen, Awash, Telebirr.

Key rules from the implementation blueprint:
- Account numbers must be TEXT (not numbers) to prevent Excel scientific notation
- No commas in numbers — force 2 decimal places, string data type
- CBE traditional: 13 numeric digits (starts with 1000...)
- Telebirr/CBE Birr/mobile wallets: 10 digits starting with 09 or 07
- Pre-validation catches bad account numbers before file generation
"""

import io
import csv
import re
from typing import List, Dict, Any


# Account validation patterns
ACCOUNT_PATTERNS = {
    'cbe': {
        'name': 'Commercial Bank of Ethiopia (CBE)',
        'pattern': r'^\d{13}$',
        'description': '13 numeric digits (e.g., 1000123456789)',
        'example': '1000123456789',
    },
    'dashen': {
        'name': 'Dashen Bank',
        'pattern': r'^\d{13}$',
        'description': '13 numeric digits',
        'example': '1000123456789',
    },
    'awash': {
        'name': 'Awash Bank',
        'pattern': r'^\d{13}$',
        'description': '13 numeric digits',
        'example': '1000123456789',
    },
    'telebirr': {
        'name': 'Telebirr / Mobile Wallet',
        'pattern': r'^(09|07)\d{8}$',
        'description': '10 digits starting with 09 or 07',
        'example': '0912345678',
    },
}


def validate_account_number(account: str, bank: str) -> tuple:
    """
    Validate an account number against the bank's format rules.

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not account or not account.strip():
        return False, "Account number is empty"

    account = account.strip()

    # Detect bank from account if not specified
    if bank not in ACCOUNT_PATTERNS:
        # Try to auto-detect
        for key, info in ACCOUNT_PATTERNS.items():
            if re.match(info['pattern'], account):
                bank = key
                break
        else:
            return False, f"Unknown bank format: '{bank}'. Supported: {', '.join(ACCOUNT_PATTERNS.keys())}"

    pattern = ACCOUNT_PATTERNS[bank]['pattern']
    if not re.match(pattern, account):
        expected = ACCOUNT_PATTERNS[bank]['description']
        return False, f"Invalid {ACCOUNT_PATTERNS[bank]['name']} account: '{account}'. Expected: {expected}"

    return True, None


def format_amount(amount: float) -> str:
    """
    Format amount for bank file: no commas, forced 2 decimal places, string type.

    Bad:  "12,500.50" or 12500.5
    Good: "12500.50"
    """
    return f"{amount:.2f}"


def validate_payroll_for_bank(employees_data: List[Dict[str, Any]],
                               bank: str = 'cbe',
                               previous_payslips: Dict[str, dict] = None) -> List[Dict[str, Any]]:
    """
    Pre-validate all employees before generating bank file.

    Catches:
    - Missing or invalid account numbers
    - Duplicate employees (same ID twice in same run)
    - Duplicate account numbers (same bank account for different employees)
    - Account number changes from previous run (suspicious)
    - Negative or zero net pay

    Args:
        employees_data: List of employee dicts
        bank: Bank key (cbe, dashen, awash, telebirr)
        previous_payslips: Dict mapping employee_id to previous payslip data
            (used to detect account changes)

    Returns:
        List of error/warning dicts (empty if all valid)
    """
    errors = []

    # --- Track duplicates within this run ---
    seen_ids = {}      # employee_id -> first occurrence index
    seen_accounts = {} # account_number -> first employee_id

    for i, emp in enumerate(employees_data):
        emp_id = emp.get('id', '')
        emp_name = emp.get('name', '')

        # --- CHECK 1: Duplicate employee ID ---
        if emp_id in seen_ids:
            errors.append({
                'employee_id': emp_id,
                'name': emp_name,
                'field': 'employee_id',
                'error': f'DUPLICATE: Employee {emp_id} appears twice in this run '
                         f'(first at row {seen_ids[emp_id] + 1}, again at row {i + 1})',
                'severity': 'BLOCK',
            })
            continue  # Skip further checks for duplicate entry
        seen_ids[emp_id] = i

        # --- CHECK 2: Missing account number ---
        account = emp.get('bank', '').strip()
        if not account:
            errors.append({
                'employee_id': emp_id,
                'name': emp_name,
                'field': 'bank_or_telebirr',
                'error': 'Missing bank/Telebirr account number',
                'severity': 'BLOCK',
            })
            continue

        # Extract account number from format
        if ':' in account:
            parts = account.split(':', 1)
            account_type = parts[0].lower()
            account_number = parts[1].strip()
        else:
            account_number = account
            account_type = bank

        # --- CHECK 3: Invalid account format ---
        bank_key = account_type
        if account_type == 'bank':
            bank_key = bank
        is_valid, error_msg = validate_account_number(account_number, bank_key)
        if not is_valid:
            errors.append({
                'employee_id': emp_id,
                'name': emp_name,
                'field': 'bank_or_telebirr',
                'error': error_msg,
                'severity': 'BLOCK',
            })

        # --- CHECK 4: Same bank account used by different employees ---
        if account_number in seen_accounts:
            errors.append({
                'employee_id': emp_id,
                'name': emp_name,
                'field': 'bank_or_telebirr',
                'error': f'DUPLICATE ACCOUNT: Bank account {account_number} '
                         f'is also assigned to employee {seen_accounts[account_number]}. '
                         f'One account cannot receive two salaries.',
                'severity': 'BLOCK',
            })
        else:
            seen_accounts[account_number] = emp_id

        # --- CHECK 5: Account number changed from previous run ---
        if previous_payslips and emp_id in previous_payslips:
            prev = previous_payslips[emp_id]
            prev_account = prev.get('bank', '').strip()
            if prev_account and ':' in prev_account:
                prev_account = prev_account.split(':', 1)[1].strip()
            if prev_account and account_number != prev_account:
                errors.append({
                    'employee_id': emp_id,
                    'name': emp_name,
                    'field': 'bank_or_telebirr',
                    'error': f'ACCOUNT CHANGED: Was {prev_account} last month, '
                             f'now {account_number}. Verify this is correct.',
                    'severity': 'FLAG',  # Not a block, but needs confirmation
                })

        # --- CHECK 6: Negative or zero net pay ---
        net = emp.get('net', 0)
        if net <= 0:
            errors.append({
                'employee_id': emp_id,
                'name': emp_name,
                'field': 'net_pay',
                'error': f'Net pay must be positive, got {net}',
                'severity': 'BLOCK',
            })

    return errors


def generate_csv(employees_data: List[Dict[str, Any]],
                 bank: str = 'cbe',
                 company_name: str = '',
                 period: str = '') -> bytes:
    """
    Generate a bank-ready CSV file for bulk payment upload.

    Args:
        employees_data: List of employee dicts with id, name, bank, net
        bank: Bank key (cbe, dashen, awash, telebirr)
        company_name: Company name for the header
        period: Pay period (e.g., "July 2025")

    Returns:
        CSV file as bytes
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row — matches CBE bulk upload format
    writer.writerow(['account_number', 'amount', 'narrative', 'currency'])

    # Data rows
    for emp in employees_data:
        account = emp.get('bank', '').strip()

        # Extract account number from format
        if ':' in account:
            account = account.split(':', 1)[1].strip()

        # Format as TEXT — no commas, 2 decimal places
        amount = format_amount(emp.get('net', 0))

        # Narrative: employee name + period
        name = emp.get('name', 'Unknown')
        narrative = f"{period} salary - {name}" if period else f"Salary - {name}"

        writer.writerow([account, amount, narrative, 'ETB'])

    return output.getvalue().encode('utf-8')


def generate_xlsx(employees_data: List[Dict[str, Any]],
                  bank: str = 'cbe',
                  company_name: str = '',
                  period: str = '') -> bytes:
    """
    Generate a bank-ready Excel file with account numbers as TEXT
    (prevents Excel scientific notation on 13-digit numbers).

    Args:
        employees_data: List of employee dicts
        bank: Bank key
        company_name: Company name
        period: Pay period

    Returns:
        XLSX file as bytes
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, numbers
    except ImportError:
        # Fallback to CSV
        return generate_csv(employees_data, bank, company_name, period)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bank Transfer"

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A5276", end_color="1A5276", fill_type="solid")
    text_format = '@'  # Explicit text format — prevents scientific notation

    # Title
    ws.merge_cells('A1:D1')
    ws['A1'] = f"Bank Transfer File — {company_name}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f"Period: {period}" if period else ""
    ws['A2'].font = Font(bold=True, size=11)

    # Headers
    headers = ['Account Number', 'Amount (ETB)', 'Narrative', 'Currency']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    # Data rows
    total_amount = 0
    for i, emp in enumerate(employees_data, 1):
        account = emp.get('bank', '').strip()
        if ':' in account:
            account = account.split(':', 1)[1].strip()

        amount = emp.get('net', 0)
        total_amount += amount
        name = emp.get('name', 'Unknown')
        narrative = f"{period} salary - {name}" if period else f"Salary - {name}"

        row = 4 + i

        # Account number: force TEXT format (prevents Excel scientific notation)
        cell = ws.cell(row=row, column=1, value=account)
        cell.number_format = text_format

        # Amount: 2 decimal places, no commas
        cell = ws.cell(row=row, column=2, value=amount)
        cell.number_format = '0.00'

        ws.cell(row=row, column=3, value=narrative)
        ws.cell(row=row, column=4, value='ETB')

    # Totals row
    totals_row = 4 + len(employees_data) + 1
    ws.cell(row=totals_row, column=1, value='TOTAL').font = Font(bold=True)
    cell = ws.cell(row=totals_row, column=2, value=total_amount)
    cell.font = Font(bold=True)
    cell.number_format = '0.00'

    # Auto-width columns
    for col in ws.columns:
        max_length = 0
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 30)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
