"""Payroll workflow service — orchestrates CSV parsing, validation, and draft creation.

Routes in main.py delegate to this module so they stay thin.
"""

import math
import os
from datetime import date

"""Payroll workflow service — orchestrates CSV parsing, validation, and draft creation.

Routes in main.py delegate to this module so they stay thin.
"""

import math
import os
from datetime import date

from payroll_engine.payroll import calculate_payroll
from payroll_engine.tax import calculate_tax_breakdown


def parse_and_calculate_payroll(
    filepath: str,
    use_element_engine: bool = os.environ.get("USE_ELEMENT_ENGINE", "0") == "1",
) -> tuple[list[dict], list[str]]:
    """Parse a CSV or Excel file and calculate payroll for each row.

    Args:
        filepath: Path to CSV or Excel file
        use_element_engine: If True, use the element engine for calculation.
                           If False, use the legacy calculate_payroll function.
                           Default: False (backward compatible).

    Returns:
        (employees_data, row_errors) where employees_data is a list of dicts
        with calculated payroll fields, and row_errors is a list of error strings.
    """
    employees_data = []
    row_errors = []

    # Detect file type
    ext = os.path.splitext(filepath)[1].lower()
    is_excel = ext in (".xlsx", ".xls")

    if is_excel:
        from payroll_engine.excel_import import parse_salary, read_xlsx

        rows = read_xlsx(filepath)
        if not rows:
            raise ValueError("Excel file is empty or has no data")
        required = ["employee_id", "name", "basic_salary", "allowances"]
        available = set(rows[0].keys()) if rows else set()
        missing = [col for col in required if col not in available]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        reader_iter = enumerate(rows, start=2)
    else:
        import csv as csv_module

        f_handle = open(filepath, newline="", encoding="utf-8")
        reader = csv_module.DictReader(f_handle)
        if not reader.fieldnames:
            f_handle.close()
            raise ValueError("CSV file is empty or has no headers")
        required = ["employee_id", "name", "basic_salary", "allowances"]
        missing = [col for col in required if col not in reader.fieldnames]
        if missing:
            f_handle.close()
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        reader_iter = enumerate(reader, start=2)

    try:
        for row_idx, row in reader_iter:
            try:
                if is_excel:
                    basic_raw = row.get("basic_salary", 0) or 0
                    allow_raw = row.get("allowances", 0) or 0
                    basic = float(parse_salary(basic_raw))
                    allow = float(parse_salary(allow_raw))
                else:
                    basic_raw = row.get("basic_salary", "0") or "0"
                    allow_raw = row.get("allowances", "0") or "0"
                    basic = float(basic_raw)
                    allow = float(allow_raw)
                if not (math.isfinite(basic) and math.isfinite(allow)):
                    raise ValueError("NaN or Infinity")
            except (ValueError, TypeError):
                row_errors.append(
                    f"Row {row_idx}: invalid numeric value "
                    f"(basic_salary='{row.get('basic_salary', '')}', "
                    f"allowances='{row.get('allowances', '')}')"
                )
                continue

            if use_element_engine:
                # Use element engine for calculation
                from payroll_engine.elements import (
                    calculate_payroll_with_elements,
                    ETHIOPIA_ELEMENTS,
                )

                employee_values = {
                    "basic_salary": basic,
                    "allowance": allow,
                    "overtime_pay": 0.0,
                    "other_deduction": 0.0,
                }
                result = calculate_payroll_with_elements(
                    ETHIOPIA_ELEMENTS, employee_values
                )
                tax_bd = calculate_tax_breakdown(result["taxable_income"])

                employees_data.append(
                    {
                        "id": str(row.get("employee_id", "")).strip(),
                        "name": str(row.get("name", "")).strip(),
                        "phone": str(row.get("phone", "")).strip(),
                        "department": str(row.get("department", "")).strip(),
                        "position": str(row.get("position", "")).strip(),
                        "start_date": str(row.get("start_date", "")).strip(),
                        "basic": basic,
                        "allowances": allow,
                        "gross": result["gross"],
                        "taxable": result["taxable_income"],
                        "tax": result["tax"],
                        "pension_employee": result["pension"],
                        "pension_employer": result["employer_pension"],
                        "net": result["net_pay"],
                        "bank_account": str(row.get("bank_account", "")).strip(),
                        "bank": str(row.get("bank_or_telebirr", "")).strip(),
                        "tin": str(row.get("tin", "")).strip(),
                        "fayda_fin": str(row.get("fayda_fin", "")).strip(),
                        "tax_breakdown": tax_bd,
                    }
                )
            else:
                # Use legacy calculate_payroll function
                result = calculate_payroll(basic, allow)
                tax_bd = calculate_tax_breakdown(result["taxable"])

                employees_data.append(
                    {
                        "id": str(row.get("employee_id", "")).strip(),
                        "name": str(row.get("name", "")).strip(),
                        "phone": str(row.get("phone", "")).strip(),
                        "department": str(row.get("department", "")).strip(),
                        "position": str(row.get("position", "")).strip(),
                        "start_date": str(row.get("start_date", "")).strip(),
                        "basic": basic,
                        "allowances": allow,
                        "gross": result["gross"],
                        "taxable": result["taxable"],
                        "tax": result["tax"],
                        "pension_employee": result["pension_employee"],
                        "pension_employer": result["pension_employer"],
                        "net": result["net"],
                        "bank_account": str(row.get("bank_account", "")).strip(),
                        "bank": str(row.get("bank_or_telebirr", "")).strip(),
                        "tin": str(row.get("tin", "")).strip(),
                        "fayda_fin": str(row.get("fayda_fin", "")).strip(),
                        "tax_breakdown": tax_bd,
                    }
                )
    finally:
        if not is_excel:
            f_handle.close()

    return employees_data, row_errors


def check_csv_row_limit(employees_data: list, max_rows: int = 5000) -> str | None:
    """Return an error message if row limit is exceeded, else None."""
    if len(employees_data) > max_rows:
        return f"CSV contains {len(employees_data)} employees — maximum allowed is {max_rows}."
    return None


def build_period_string(ref_date=None) -> str:
    """Build an Ethiopian period string 'YYYY-MM' from a Gregorian date."""
    from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian

    ref_date = ref_date or date.today()
    eth_year, eth_month, _ = gregorian_to_ethiopian(ref_date)
    return f"{eth_year}-{eth_month:02d}"


def get_previous_payslips(company_id: int):
    """Fetch previous month's payslip data for salary comparison."""
    from payroll_engine.models import PayrollRun

    previous_payslips = {}
    last_run = (
        PayrollRun.query.filter_by(company_id=company_id, status="completed")
        .order_by(PayrollRun.run_date.desc())
        .first()
    )
    if last_run:
        for p in last_run.payslips:
            emp = p.employee
            previous_payslips[emp.employee_id] = {
                "basic": emp.basic_salary,
                "allowances": emp.allowances,
            }
    return previous_payslips


def check_duplicate_period(company_id: int, period: str) -> tuple[str, str] | None:
    """Check if a payroll run already exists for this period.

    Returns (status_message, redirect) tuple or None if no conflict.
    """
    from payroll_engine.ethiopian_calendar import get_ethiopian_month_name
    from payroll_engine.models import PayrollRun

    existing = (
        PayrollRun.query.filter_by(company_id=company_id, period=period)
        .filter(PayrollRun.status.notin_(["failed", "rejected"]))
        .first()
    )
    if existing:
        eth_parts = period.split("-")
        month_name = get_ethiopian_month_name(int(eth_parts[1]), "en")
        if existing.status == "locked":
            return (
                f"{month_name} {eth_parts[0]} is locked (#{existing.reference}). Ask the owner to unlock it first.",
                "locked",
            )
        return (
            f"A payroll run for {month_name} {eth_parts[0]} already exists "
            f"(#{existing.reference}, status: {existing.status}). "
            f"Delete or reject it first to reprocess.",
            "duplicate",
        )
    return None


def create_payroll_run(
    company_id: int, employees_data: list, validation_results: list
) -> dict:
    """Create a complete payroll run with draft and validation results.

    Wraps all DB writes in a transaction so a partial failure rolls back cleanly.

    Args:
        company_id: The company doing the payroll run
        employees_data: List of dicts with calculated payroll fields from parse_and_calculate_payroll
        validation_results: List of validation result objects

    Returns:
        Dict with keys: run_id, employees_data, totals, element_engine_used
    """
    from payroll_engine import db
    from payroll_engine.models import PayrollDraft, PayrollRun, PayrollValidationResult

    # Determine if element engine was used
    use_element_engine = os.environ.get("USE_ELEMENT_ENGINE", "0") == "1"
    element_engine_version = (
        "element_engine_v1" if use_element_engine else "legacy_calculate_payroll"
    )

    try:
        run = PayrollRun(
            company_id=company_id,
            run_date=date.today(),
            status="review",
            source="upload",
            calculation_method=element_engine_version,
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
            company_id=company_id,
            employee_data=employees_data,
        )
        db.session.add(draft)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    total_gross = sum(e["gross"] for e in employees_data)
    total_tax = sum(e["tax"] for e in employees_data)
    total_net = sum(e["net"] for e in employees_data)

    return {
        "run_id": run.id,
        "employees_data": employees_data,
        "validation_results": validation_results,
        "total_gross": total_gross,
        "total_tax": total_tax,
        "total_net": total_net,
        "element_engine_used": use_element_engine,
        "calculation_method": element_engine_version,
    }