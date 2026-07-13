"""
Excel Migration Tool

Helps companies migrate from Excel-based payroll to the system.
Reads common Ethiopian payroll Excel formats and converts to CSV
for import into the payroll engine.

Supported formats:
- Standard payroll spreadsheet (name, basic, allowances, bank)
- ERCA return format
- Bank transfer format

Auto-detects columns by header names.
"""

import io
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Tuple, Optional


def detect_column_mapping(headers: List[str]) -> Dict[str, int]:
    """Auto-detect column mapping from header names.

    Ethiopian payroll spreadsheets use various header formats:
    - "Employee Name" / "Name" / "ስም" / "የሰራተኛ ስም"
    - "Basic Salary" / "Basic" / "መሠረታዊ ደመወዝ"
    - "Allowances" / "Allowance" / "ጠቅላላ ክፍያ"
    - "Bank Account" / "Account No" / "የባንክ ሂሳብ"
    - "TIN" / "TIN No" / "የታክስ ተለያይ ቁጥር"
    - "Employee ID" / "ID" / "Emp ID"

    Args:
        headers: List of header strings from the Excel file

    Returns:
        Dict mapping standard field names to column indices
    """
    mapping = {}
    normalized = [h.strip().lower() for h in headers]

    # Employee ID
    for i, h in enumerate(normalized):
        if h in ('employee id', 'emp id', 'emp_id', 'id', 'employee_id', 'no', 'no.'):
            mapping['employee_id'] = i
            break

    # Name
    for i, h in enumerate(normalized):
        if h in ('name', 'employee name', 'emp name', 'full name', 'employee_name',
                 'የሰራተኛ ስም', 'ስም', 'የሙሉ ስም'):
            mapping['name'] = i
            break

    # TIN
    for i, h in enumerate(normalized):
        if h in ('tin', 'tin no', 'tin_no', 'tin number', 'የታክስ ተለያይ ቁጥር'):
            mapping['tin'] = i
            break

    # Basic Salary
    for i, h in enumerate(normalized):
        if h in ('basic salary', 'basic', 'salary', 'base salary', 'basic_salary',
                 'መሠረታዊ ደመወዝ', 'ደመወዝ'):
            mapping['basic_salary'] = i
            break

    # Allowances
    for i, h in enumerate(normalized):
        if h in ('allowances', 'allowance', 'total allowances', 'other allowances',
                 'ጠቅላላ ክፍያ', 'ክፍያ'):
            mapping['allowances'] = i
            break

    # Transport Allowance
    for i, h in enumerate(normalized):
        if h in ('transport', 'transport allowance', 'ትራንስፖርት', 'የትራንስፖርት ክፍያ'):
            mapping['transport_allowance'] = i
            break

    # Bank Account
    for i, h in enumerate(normalized):
        if h in ('bank', 'bank account', 'account', 'account no', 'bank_account',
                 'account number', 'የባንክ ሂሳብ', 'ባንክ'):
            mapping['bank_account'] = i
            break

    # Department
    for i, h in enumerate(normalized):
        if h in ('department', 'dept', '部门', 'ክፍል'):
            mapping['department'] = i
            break

    # Position
    for i, h in enumerate(normalized):
        if h in ('position', 'title', 'job title', 'role', 'የስራ ደረጃ'):
            mapping['position'] = i
            break

    return mapping


def parse_excel_data(rows: List[List], mapping: Dict[str, int]) -> Tuple[List[Dict], List[str]]:
    """Parse Excel rows into employee data dicts.

    Args:
        rows: List of rows (each row is a list of cell values)
        mapping: Column mapping from detect_column_mapping

    Returns:
        Tuple of (parsed_data, errors)
    """
    data = []
    errors = []

    for row_num, row in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            continue  # Skip empty rows

        def get(field):
            idx = mapping.get(field)
            if idx is not None and idx < len(row):
                val = row[idx]
                if val is None:
                    return ''
                return str(val).strip()
            return ''

        def get_decimal(field):
            val = get(field)
            if not val:
                return Decimal('0')
            try:
                # Remove commas, currency symbols, spaces
                cleaned = val.replace(',', '').replace('ETB', '').replace('etb', '').strip()
                return Decimal(cleaned)
            except (InvalidOperation, ValueError):
                errors.append(f"Row {row_num}: Invalid number for {field}: '{val}'")
                return Decimal('0')

        emp_id = get('employee_id')
        name = get('name')

        if not name:
            errors.append(f"Row {row_num}: Missing employee name, skipping")
            continue

        # Auto-generate ID if missing
        if not emp_id:
            emp_id = f'EMP{row_num - 1:03d}'

        # Parse bank account format
        bank_raw = get('bank_account')
        bank = ''
        if bank_raw:
            # Try to detect bank from account number
            if ':' in bank_raw:
                bank = bank_raw  # Already in format "bank:account"
            elif re.match(r'^1\d{12}$', bank_raw):
                bank = f'cbe:{bank_raw}'  # CBE format
            elif re.match(r'^(0?9|0?7)\d{8}$', bank_raw):
                bank = f'telebirr:{bank_raw}'  # Telebirr format
            else:
                bank = f'bank:{bank_raw}'  # Unknown bank

        basic = get_decimal('basic_salary')
        allowances = get_decimal('allowances')
        transport = get_decimal('transport_allowance')

        # If transport is separate, add it to allowances
        if transport > 0 and allowances == 0:
            allowances = transport

        data.append({
            'employee_id': emp_id,
            'name': name,
            'tin': get('tin'),
            'basic_salary': basic,
            'allowances': allowances,
            'transport_allowance': transport,
            'bank_account': bank,
            'department': get('department'),
            'position': get('position'),
        })

    return data, errors


def read_excel_file(file_path: str) -> Tuple[List[List], List[str]]:
    """Read an Excel file and return rows.

    Args:
        file_path: Path to .xlsx or .xls file

    Returns:
        Tuple of (rows, errors)
    """
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
        wb.close()
        return rows, []
    except ImportError:
        return [], ['openpyxl not installed. Cannot read Excel files.']
    except Exception as e:
        return [], [f'Error reading Excel file: {str(e)}']


def read_csv_file(file_path: str) -> Tuple[List[List], List[str]]:
    """Read a CSV file and return rows.

    Args:
        file_path: Path to .csv file

    Returns:
        Tuple of (rows, errors)
    """
    import csv
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            rows = []
            for row in reader:
                # Skip comment rows
                if row and row[0].strip().startswith('#'):
                    continue
                # Skip empty rows
                if not any(cell.strip() for cell in row):
                    continue
                rows.append(row)
            return rows, []
    except Exception as e:
        return [], [f'Error reading CSV file: {str(e)}']


def migrate_file(file_path: str) -> Tuple[List[Dict], List[str], Dict[str, int]]:
    """Migrate an Excel or CSV file to the payroll engine format.

    Auto-detects file type, column mapping, and parses data.

    Args:
        file_path: Path to the file (.xlsx, .xls, or .csv)

    Returns:
        Tuple of (parsed_data, errors, column_mapping)
    """
    # Detect file type
    if file_path.endswith(('.xlsx', '.xls')):
        rows, errors = read_excel_file(file_path)
    elif file_path.endswith('.csv'):
        rows, errors = read_csv_file(file_path)
    else:
        return [], ['Unsupported file type. Use .xlsx, .xls, or .csv'], {}

    if errors:
        return [], errors, {}

    if not rows:
        return [], ['File is empty'], {}

    # First row is headers
    headers = rows[0]
    data_rows = rows[1:]

    # Auto-detect columns
    mapping = detect_column_mapping(headers)

    if 'name' not in mapping:
        return [], ['Could not detect "Name" column. Please ensure the file has a Name/Employee Name column.'], mapping

    # Parse data
    data, parse_errors = parse_excel_data(data_rows, mapping)

    return data, parse_errors, mapping


def generate_import_csv(data: List[Dict]) -> str:
    """Generate a CSV file ready for import into the payroll engine.

    Args:
        data: List of employee dicts from migrate_file

    Returns:
        CSV string
    """
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['employee_id', 'name', 'tin', 'basic_salary', 'allowances',
                     'bank_account', 'department', 'position'])
    for emp in data:
        writer.writerow([
            emp.get('employee_id', ''),
            emp.get('name', ''),
            emp.get('tin', ''),
            str(emp.get('basic_salary', 0)),
            str(emp.get('allowances', 0)),
            emp.get('bank_account', ''),
            emp.get('department', ''),
            emp.get('position', ''),
        ])
    return output.getvalue()
