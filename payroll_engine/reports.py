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
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.cell.cell import MergedCell
    except ImportError:
        # Fallback to CSV if openpyxl not installed
        return _generate_erca_csv(payslips, company_name, period)

    if period is None:
        period = date.today().strftime('%B %Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ERCA Tax Filing"

    # Styles
    title_font = Font(bold=True, size=16, color='1A5276')
    subtitle_font = Font(bold=True, size=12, color='333333')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1A5276', end_color='1A5276', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    data_align = Alignment(horizontal='right', vertical='center')
    name_align = Alignment(horizontal='left', vertical='center')
    totals_font = Font(bold=True, size=11, color='1A5276')
    totals_fill = PatternFill(start_color='D6EAF8', end_color='D6EAF8', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )
    etb_format = '#,##0.00'

    # --- Title block ---
    ws.merge_cells('A1:I1')
    ws['A1'] = company_name
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='left', vertical='center')

    ws.merge_cells('A2:I2')
    ws['A2'] = f'ERCA Monthly Tax Filing Report — {period}'
    ws['A2'].font = subtitle_font

    ws.merge_cells('A3:I3')
    ws['A3'] = f'Generated: {date.today().strftime("%d %B %Y")}'
    ws['A3'].font = Font(italic=True, color='666666')

    # --- Column headers (row 5) ---
    headers = [
        'No.', 'Employee ID', 'Employee Name', 'TIN',
        'Gross Salary', 'Pension 7%', 'Taxable Income',
        'Tax Withheld', 'Net Pay'
    ]
    col_widths = [6, 14, 22, 14, 16, 14, 16, 14, 16]
    for col, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=5, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    # --- Data rows ---
    total_gross = 0
    total_pension = 0
    total_taxable = 0
    total_tax = 0
    total_net = 0

    for i, p in enumerate(payslips, 1):
        emp = p.employee
        taxable = p.gross_salary - p.employee_pension
        row = 5 + i

        ws.cell(row=row, column=1, value=i).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=2, value=emp.employee_id).alignment = name_align
        ws.cell(row=row, column=3, value=emp.name).alignment = name_align
        ws.cell(row=row, column=4, value=emp.tin or '').alignment = name_align

        for col_idx, val in [(5, p.gross_salary), (6, p.employee_pension),
                              (7, taxable), (8, p.tax), (9, p.net_pay)]:
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.number_format = etb_format
            cell.alignment = data_align

        # Borders on all cells
        for col_idx in range(1, 10):
            ws.cell(row=row, column=col_idx).border = thin_border

        total_gross += p.gross_salary
        total_pension += p.employee_pension
        total_taxable += taxable
        total_tax += p.tax
        total_net += p.net_pay

    # --- Totals row ---
    totals_row = 5 + len(payslips) + 1
    ws.cell(row=totals_row, column=3, value='TOTALS').font = totals_font
    ws.cell(row=totals_row, column=3).fill = totals_fill
    ws.cell(row=totals_row, column=3).border = thin_border
    for col_idx, val in [(5, total_gross), (6, total_pension),
                          (7, total_taxable), (8, total_tax), (9, total_net)]:
        cell = ws.cell(row=totals_row, column=col_idx, value=val)
        cell.font = totals_font
        cell.fill = totals_fill
        cell.number_format = etb_format
        cell.alignment = data_align
        cell.border = thin_border

    # --- Print setup ---
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.orientation = 'landscape'

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
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.cell.cell import MergedCell
    except ImportError:
        return _generate_pension_csv(payslips, company_name, period)

    if period is None:
        period = date.today().strftime('%B %Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pension Report"

    # Styles
    title_font = Font(bold=True, size=16, color='1A5276')
    subtitle_font = Font(bold=True, size=12, color='333333')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1A5276', end_color='1A5276', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    data_align = Alignment(horizontal='right', vertical='center')
    name_align = Alignment(horizontal='left', vertical='center')
    totals_font = Font(bold=True, size=11, color='1A5276')
    totals_fill = PatternFill(start_color='D6EAF8', end_color='D6EAF8', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )
    etb_format = '#,##0.00'

    # --- Title block ---
    ws.merge_cells('A1:G1')
    ws['A1'] = company_name
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='left', vertical='center')

    ws.merge_cells('A2:G2')
    ws['A2'] = f'Pension Contribution Report — {period}'
    ws['A2'].font = subtitle_font

    ws.merge_cells('A3:G3')
    ws['A3'] = f'Generated: {date.today().strftime("%d %B %Y")}'
    ws['A3'].font = Font(italic=True, color='666666')

    # --- Column headers (row 5) ---
    headers = [
        'No.', 'Employee ID', 'Employee Name', 'Basic Salary',
        'Employee 7%', 'Employer 11%', 'Total'
    ]
    col_widths = [6, 14, 22, 16, 14, 14, 16]
    for col, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=5, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    # --- Data rows ---
    total_employee = 0
    total_employer = 0

    for i, p in enumerate(payslips, 1):
        emp = p.employee
        total = p.employee_pension + p.employer_pension
        row = 5 + i

        ws.cell(row=row, column=1, value=i).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=2, value=emp.employee_id).alignment = name_align
        ws.cell(row=row, column=3, value=emp.name).alignment = name_align

        for col_idx, val in [(4, emp.basic_salary), (5, p.employee_pension),
                              (6, p.employer_pension), (7, total)]:
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.number_format = etb_format
            cell.alignment = data_align

        for col_idx in range(1, 8):
            ws.cell(row=row, column=col_idx).border = thin_border

        total_employee += p.employee_pension
        total_employer += p.employer_pension

    # --- Totals row ---
    totals_row = 5 + len(payslips) + 1
    ws.cell(row=totals_row, column=3, value='TOTALS').font = totals_font
    ws.cell(row=totals_row, column=3).fill = totals_fill
    ws.cell(row=totals_row, column=3).border = thin_border
    for col_idx, val in [(5, total_employee), (6, total_employer),
                          (7, total_employee + total_employer)]:
        cell = ws.cell(row=totals_row, column=col_idx, value=val)
        cell.font = totals_font
        cell.fill = totals_fill
        cell.number_format = etb_format
        cell.alignment = data_align
        cell.border = thin_border

    # --- Print setup ---
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.orientation = 'landscape'

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
        from payroll_engine.security import prevent_csv_injection
        writer.writerow([
            i,
            prevent_csv_injection(emp.employee_id),
            prevent_csv_injection(emp.name),
            prevent_csv_injection(emp.tin or ''),
            p.gross_salary, p.employee_pension, taxable, p.tax, p.net_pay,
        ])
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
        from payroll_engine.security import prevent_csv_injection
        writer.writerow([
            i,
            prevent_csv_injection(emp.employee_id),
            prevent_csv_injection(emp.name),
            emp.basic_salary, p.employee_pension, p.employer_pension, total,
        ])
    return output.getvalue().encode('utf-8')
