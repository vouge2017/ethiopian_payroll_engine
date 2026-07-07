"""
Report Generation Module

Generates downloadable reports for:
- ERCA tax filing (monthly)
- Pension contribution reporting (monthly)
- Year-end reconciliation

All reports are generated from Payslip data and downloadable as Excel.
"""

import io
from datetime import date
from typing import List, Dict, Any


def generate_erca_report(payslips: list, company_name: str,
                         period: str = None) -> bytes:
    """
    Generate ERCA-formatted tax filing report.

    Args:
        payslips: List of Payslip objects with employee relationship loaded
        company_name: Company name for the report header
        period: Period string (e.g., "July 2025"), defaults to current month

    Returns:
        Excel file as bytes
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.cell.cell import MergedCell
    except ImportError:
        # Fallback to CSV if openpyxl not installed
        return _generate_erca_csv(payslips, company_name, period)

    if period is None:
        period = date.today().strftime('%B %Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ERCA Tax Filing"

    # Header style
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A5276", end_color="1A5276", fill_type="solid")

    # Title
    ws.merge_cells('A1:I1')
    ws['A1'] = f"ERCA Monthly Tax Filing Report — {company_name}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f"Period: {period}"
    ws['A2'].font = Font(bold=True, size=11)
    ws['A3'] = f"Generated: {date.today().isoformat()}"

    # Column headers
    headers = [
        'No.', 'Employee ID', 'Employee Name', 'TIN',
        'Gross Salary (ETB)', 'Pension 7% (ETB)', 'Taxable Income (ETB)',
        'Tax Withheld (ETB)', 'Net Pay (ETB)'
    ]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    # Data rows
    total_gross = 0
    total_pension = 0
    total_taxable = 0
    total_tax = 0
    total_net = 0

    for i, p in enumerate(payslips, 1):
        emp = p.employee
        taxable = p.gross_salary - p.employee_pension

        row = 5 + i
        ws.cell(row=row, column=1, value=i)
        ws.cell(row=row, column=2, value=emp.employee_id)
        ws.cell(row=row, column=3, value=emp.name)
        ws.cell(row=row, column=4, value=emp.tin or '')
        ws.cell(row=row, column=5, value=p.gross_salary)
        ws.cell(row=row, column=6, value=p.employee_pension)
        ws.cell(row=row, column=7, value=taxable)
        ws.cell(row=row, column=8, value=p.tax)
        ws.cell(row=row, column=9, value=p.net_pay)

        total_gross += p.gross_salary
        total_pension += p.employee_pension
        total_taxable += taxable
        total_tax += p.tax
        total_net += p.net_pay

    # Totals row
    totals_row = 5 + len(payslips) + 1
    ws.cell(row=totals_row, column=3, value='TOTALS').font = Font(bold=True)
    ws.cell(row=totals_row, column=5, value=total_gross).font = Font(bold=True)
    ws.cell(row=totals_row, column=6, value=total_pension).font = Font(bold=True)
    ws.cell(row=totals_row, column=7, value=total_taxable).font = Font(bold=True)
    ws.cell(row=totals_row, column=8, value=total_tax).font = Font(bold=True)
    ws.cell(row=totals_row, column=9, value=total_net).font = Font(bold=True)

    # Auto-width columns — skip MergedCell objects
    for col in ws.columns:
        max_length = 0
        col_letter = None
        for cell in col:
            if isinstance(cell, MergedCell):
                continue
            if col_letter is None:
                col_letter = cell.column_letter
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        if col_letter:
            ws.column_dimensions[col_letter].width = min(max_length + 2, 30)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_pension_report(payslips: list, company_name: str,
                            period: str = None) -> bytes:
    """
    Generate pension contribution report.

    Args:
        payslips: List of Payslip objects with employee relationship loaded
        company_name: Company name for the report header
        period: Period string (e.g., "July 2025")

    Returns:
        Excel file as bytes
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.cell.cell import MergedCell
    except ImportError:
        return _generate_pension_csv(payslips, company_name, period)

    if period is None:
        period = date.today().strftime('%B %Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pension Report"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A5276", end_color="1A5276", fill_type="solid")

    # Title
    ws.merge_cells('A1:G1')
    ws['A1'] = f"Pension Contribution Report — {company_name}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f"Period: {period}"
    ws['A2'].font = Font(bold=True, size=11)

    # Column headers
    headers = [
        'No.', 'Employee ID', 'Employee Name', 'Basic Salary (ETB)',
        'Employee 7% (ETB)', 'Employer 11% (ETB)', 'Total (ETB)'
    ]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    total_employee = 0
    total_employer = 0

    for i, p in enumerate(payslips, 1):
        emp = p.employee
        total = p.employee_pension + p.employer_pension

        row = 4 + i
        ws.cell(row=row, column=1, value=i)
        ws.cell(row=row, column=2, value=emp.employee_id)
        ws.cell(row=row, column=3, value=emp.name)
        ws.cell(row=row, column=4, value=emp.basic_salary)
        ws.cell(row=row, column=5, value=p.employee_pension)
        ws.cell(row=row, column=6, value=p.employer_pension)
        ws.cell(row=row, column=7, value=total)

        total_employee += p.employee_pension
        total_employer += p.employer_pension

    # Totals
    totals_row = 4 + len(payslips) + 1
    ws.cell(row=totals_row, column=3, value='TOTALS').font = Font(bold=True)
    ws.cell(row=totals_row, column=5, value=total_employee).font = Font(bold=True)
    ws.cell(row=totals_row, column=6, value=total_employer).font = Font(bold=True)
    ws.cell(row=totals_row, column=7, value=total_employee + total_employer).font = Font(bold=True)

    for col in ws.columns:
        max_length = 0
        col_letter = None
        for cell in col:
            if isinstance(cell, MergedCell):
                continue
            if col_letter is None:
                col_letter = cell.column_letter
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        if col_letter:
            ws.column_dimensions[col_letter].width = min(max_length + 2, 30)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _generate_erca_csv(payslips, company_name, period):
    """Fallback CSV generation if openpyxl not installed."""
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ERCA Tax Filing Report', company_name, period or ''])
    writer.writerow(['No.', 'Employee ID', 'Name', 'TIN', 'Gross', 'Pension', 'Taxable', 'Tax', 'Net'])
    for i, p in enumerate(payslips, 1):
        emp = p.employee
        taxable = p.gross_salary - p.employee_pension
        writer.writerow([i, emp.employee_id, emp.name, emp.tin or '', p.gross_salary, p.employee_pension, taxable, p.tax, p.net_pay])
    return output.getvalue().encode('utf-8')


def _generate_pension_csv(payslips, company_name, period):
    """Fallback CSV generation if openpyxl not installed."""
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Pension Contribution Report', company_name, period or ''])
    writer.writerow(['No.', 'Employee ID', 'Name', 'Basic Salary', 'Employee 7%', 'Employer 11%', 'Total'])
    for i, p in enumerate(payslips, 1):
        emp = p.employee
        total = p.employee_pension + p.employer_pension
        writer.writerow([i, emp.employee_id, emp.name, emp.basic_salary, p.employee_pension, p.employer_pension, total])
    return output.getvalue().encode('utf-8')
