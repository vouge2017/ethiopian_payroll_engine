"""Payroll workflow service — orchestrates CSV parsing, validation, and draft creation.

Routes in main.py delegate to this module so they stay thin.
"""
import csv as csv_module
import math
import os
from datetime import date
from typing import List, Dict, Tuple, Optional

from payroll_engine.payroll import calculate_payroll
from payroll_engine.tax import calculate_tax_breakdown


def parse_and_calculate_payroll(filepath: str) -> Tuple[List[Dict], List[str]]:
    """Parse a CSV or Excel file and calculate payroll for each row.

    Returns:
        (employees_data, row_errors) where employees_data is a list of dicts
        with calculated payroll fields, and row_errors is a list of error strings.
    """
    import os
    employees_data = []
    row_errors = []

    # Detect file type
    ext = os.path.splitext(filepath)[1].lower()
    is_excel = ext in ('.xlsx', '.xls')

    if is_excel:
        from payroll_engine.excel_import import read_xlsx, parse_salary
        rows = read_xlsx(filepath)
        if not rows:
            raise ValueError('Excel file is empty or has no data')
        required = ['employee_id', 'name', 'basic_salary', 'allowances']
        available = set(rows[0].keys()) if rows else set()
        missing = [col for col in required if col not in available]
        if missing:
            raise ValueError(f'Missing required columns: {", ".join(missing)}')
        reader_iter = enumerate(rows, start=2)
    else:
        import csv as csv_module
        f_handle = open(filepath, newline='', encoding='utf-8')
        reader = csv_module.DictReader(f_handle)
        if not reader.fieldnames:
            f_handle.close()
            raise ValueError('CSV file is empty or has no headers')
        required = ['employee_id', 'name', 'basic_salary', 'allowances']
        missing = [col for col in required if col not in reader.fieldnames]
        if missing:
            f_handle.close()
            raise ValueError(f'Missing required columns: {", ".join(missing)}')
        reader_iter = enumerate(reader, start=2)

    try:
        for row_idx, row in reader_iter:
            try:
                if is_excel:
                    basic_raw = row.get('basic_salary', 0) or 0
                    allow_raw = row.get('allowances', 0) or 0
                    basic = float(parse_salary(basic_raw))
                    allow = float(parse_salary(allow_raw))
                else:
                    basic_raw = row.get('basic_salary', '0') or '0'
                    allow_raw = row.get('allowances', '0') or '0'
                    basic = float(basic_raw)
                    allow = float(allow_raw)
                if not (math.isfinite(basic) and math.isfinite(allow)):
                    raise ValueError('NaN or Infinity')
            except (ValueError, TypeError):
                row_errors.append(
                    f"Row {row_idx}: invalid numeric value "
                    f"(basic_salary='{row.get('basic_salary', '')}', "
                    f"allowances='{row.get('allowances', '')}')"
                )
                continue
            result = calculate_payroll(basic, allow)
            tax_bd = calculate_tax_breakdown(result['taxable'])
            employees_data.append({
                'id': str(row.get('employee_id', '')).strip(),
                'name': str(row.get('name', '')).strip(),
                'phone': str(row.get('phone', '')).strip(),
                'department': str(row.get('department', '')).strip(),
                'position': str(row.get('position', '')).strip(),
                'start_date': str(row.get('start_date', '')).strip(),
                'basic': basic,
                'allowances': allow,
                'gross': result['gross'],
                'taxable': result['taxable'],
                'tax': result['tax'],
                'pension_employee': result['pension_employee'],
                'pension_employer': result['pension_employer'],
                'net': result['net'],
                'bank_account': str(row.get('bank_account', '')).strip(),
                'bank': str(row.get('bank_or_telebirr', '')).strip(),
                'tin': str(row.get('tin', '')).strip(),
                'tax_breakdown': tax_bd,
            })
    finally:
        if not is_excel:
            f_handle.close()

    return employees_data, row_errors


def check_csv_row_limit(employees_data: List, max_rows: int = 5000) -> Optional[str]:
    """Return an error message if row limit is exceeded, else None."""
    if len(employees_data) > max_rows:
        return (
            f'CSV contains {len(employees_data)} employees — '
            f'maximum allowed is {max_rows}.'
        )
    return None


def build_period_string(ref_date=None) -> str:
    """Build an Ethiopian period string 'YYYY-MM' from a Gregorian date."""
    from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian
    ref_date = ref_date or date.today()
    eth_year, eth_month, _ = gregorian_to_ethiopian(ref_date)
    return f'{eth_year}-{eth_month:02d}'


def get_previous_payslips(company_id: int):
    """Fetch previous month's payslip data for salary comparison."""
    from payroll_engine import db
    from payroll_engine.models import PayrollRun
    previous_payslips = {}
    last_run = PayrollRun.query.filter_by(
        company_id=company_id, status='completed'
    ).order_by(PayrollRun.run_date.desc()).first()
    if last_run:
        for p in last_run.payslips:
            emp = p.employee
            previous_payslips[emp.employee_id] = {
                'basic': emp.basic_salary,
                'allowances': emp.allowances,
            }
    return previous_payslips


def check_duplicate_period(company_id: int, period: str) -> Optional[Tuple[str, str]]:
    """Check if a payroll run already exists for this period.

    Returns (status_message, redirect) tuple or None if no conflict.
    """
    from payroll_engine import db
    from payroll_engine.models import PayrollRun
    from payroll_engine.ethiopian_calendar import get_ethiopian_month_name

    existing = PayrollRun.query.filter_by(
        company_id=company_id,
        period=period
    ).filter(
        PayrollRun.status.notin_(['failed', 'rejected'])
    ).first()
    if existing:
        eth_parts = period.split('-')
        month_name = get_ethiopian_month_name(int(eth_parts[1]), 'en')
        if existing.status == 'locked':
            return (
                f'{month_name} {eth_parts[0]} is locked '
                f'(#{existing.reference}). '
                f'Ask the owner to unlock it first.',
                'locked'
            )
        return (
            f'A payroll run for {month_name} {eth_parts[0]} already exists '
            f'(#{existing.reference}, status: {existing.status}). '
            f'Delete or reject it first to reprocess.',
            'duplicate'
        )
    return None


def create_payroll_run(company_id: int, employees_data: List, validation_results: list) -> dict:
    """Create a complete payroll run with draft and validation results.

    Wraps all DB writes in a transaction so a partial failure rolls back cleanly.

    Returns dict with keys: run_id, employees_data, totals.
    """
    from payroll_engine import db
    from payroll_engine.models import PayrollRun, PayrollDraft, PayrollValidationResult

    try:
        run = PayrollRun(
            company_id=company_id,
            run_date=date.today(),
            status='review',
        )
        run.generate_period()
        db.session.add(run)
        db.session.flush()
        run.generate_reference()

        for vr in validation_results:
            db_vr = PayrollValidationResult(
                payroll_run_id=run.id,
                rule_code=vr.rule_code,
                severity=vr.severity,
                message=vr.message,
                details_json=vr.details,
            )
            db.session.add(db_vr)

        draft = PayrollDraft(
            payroll_run_id=run.id,
            employee_data=employees_data,
        )
        db.session.add(draft)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    total_gross = sum(e['gross'] for e in employees_data)
    total_tax = sum(e['tax'] for e in employees_data)
    total_net = sum(e['net'] for e in employees_data)

    return {
        'run_id': run.id,
        'employees_data': employees_data,
        'validation_results': validation_results,
        'total_gross': total_gross,
        'total_tax': total_tax,
        'total_net': total_net,
    }
