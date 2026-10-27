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
from decimal import Decimal

from payroll_engine.frozen_payslip import UNFROZEN_BASIC_NOTE, frozen_figures, unfrozen_basic_count

UNKNOWN_ALLOWANCE_NOTE = (
    'Allowance breakdown unavailable for some cells: the saved run settings, earning lines, or '
    'inputs needed for a partial exemption are missing. Review before filing.'
)
UNKNOWN_ITEM_NOTE = (
    'Pay-item breakdown unavailable for some columns: the approved item snapshot or per-item tax treatment '
    'was not preserved. Blank cells require review before filing.'
)
BACKFILLED_ITEM_NOTE = (
    'Some item settings were backfilled from settings at migration time, not from approval. '
    'Review these breakdowns against original payroll records before filing.'
)
INCOMPLETE_TOTAL_NOTE = 'Totals are blank where one or more employee values are missing. Review before filing.'


def _report_run_snapshot(payslip, cache):
    from payroll_engine.item_snapshot import run_item_snapshot

    key = (payslip.company_id, payslip.payroll_run_id)
    if key not in cache:
        cache[key] = run_item_snapshot(*key)
    return cache[key]


# Every money figure in a monthly report comes from the values frozen on the
# payslip at approval (see payroll_engine/frozen_payslip.py), never from the
# employee's current record: re-downloading a locked month must give the same
# numbers after a raise.


def generate_erca_report(payslips: list, company_name: str, period: str | None = None, company=None) -> bytes:
    """
    Generate ERCA-formatted tax filing report.

    Uses company's report template if available, otherwise uses default columns.

    Args:
        payslips: List of Payslip objects with employee relationship loaded
        company_name: Company name for the report header
        period: Period string (e.g., "July 2025"), defaults to current month
        company: Company instance (for template-aware column configuration)

    Returns:
        Excel file as bytes
    """
    from payroll_engine.report_templates import get_column_value, get_enabled_columns

    # Get columns from template or use defaults (ERCA portal format)
    if company:
        columns = get_enabled_columns(company, 'erca')
    else:
        # Fallback: use ERCA portal columns
        columns = [
            {'key': 'employee_name', 'label': 'Employee Full Name', 'data_path': 'employee.name'},
            {'key': 'start_date', 'label': 'Start Date', 'data_path': 'employee.start_date'},
            {'key': 'end_date', 'label': 'End Date', 'data_path': '_end_date'},
            {'key': 'basic_salary', 'label': 'Basic Salary', 'data_path': 'employee.basic_salary'},
            {'key': 'transport_allowance', 'label': 'Transport Allowance', 'data_path': '_transport_allowance'},
            {'key': 'taxable_transport', 'label': 'Taxable Transport Allowance', 'data_path': '_taxable_transport'},
            {'key': 'overtime_pay', 'label': 'Over Time', 'data_path': 'overtime_pay'},
            {'key': 'other_taxable', 'label': 'Other Taxable Benefit', 'data_path': '_other_taxable'},
            {'key': 'total_taxable', 'label': 'Total Taxable', 'data_path': 'taxable'},
            {'key': 'tax_withheld', 'label': 'Tax withheld', 'data_path': 'tax'},
        ]

    # Identify which columns are numeric (for formatting and totals)
    NUMERIC_KEYS = {
        'basic_salary',
        'allowances',
        'gross_salary',
        'overtime_pay',
        'pension_employee',
        'pension_employer',
        'taxable_income',
        'tax_withheld',
        'net_pay',
        'transport_allowance',
        'taxable_transport',
        'other_taxable',
        'total_taxable',
    }

    # Map data_path to actual payslip attribute names

    try:
        import openpyxl
        from openpyxl.cell.cell import MergedCell  # noqa: F401
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        # Fallback to CSV if openpyxl not installed
        return _generate_erca_csv(payslips, company_name, period)

    if period is None:
        period = date.today().strftime('%B %Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'ERCA Tax Filing'

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

    # --- Column headers (row 5) ---
    num_cols = len(columns)
    col_letter_last = openpyxl.utils.get_column_letter(num_cols)

    # Merge title cells to span all columns
    ws.merge_cells(f'A1:{col_letter_last}1')
    ws['A1'] = company_name
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='left', vertical='center')

    ws.merge_cells(f'A2:{col_letter_last}2')
    ws['A2'] = f'ERCA Monthly Tax Filing Report — {period}'
    ws['A2'].font = subtitle_font

    ws.merge_cells(f'A3:{col_letter_last}3')
    ws['A3'] = f'Generated: {date.today().strftime("%d %B %Y")}'
    ws['A3'].font = Font(italic=True, color='666666')

    # Auto-calculate column widths based on label length
    for col_idx, col_cfg in enumerate(columns, 1):
        width = max(len(col_cfg['label']) + 2, 10)
        width = min(width, 30)  # cap at 30
        cell = ws.cell(row=5, column=col_idx, value=col_cfg['label'])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    # --- Data rows ---
    totals = {}  # key -> running total
    incomplete_totals = set()
    unknown_allowance = False
    unknown_item = False
    backfilled = False
    relevant_paths = ('_transport_allowance', '_taxable_transport', '_other_taxable')
    snapshots = {}
    uses_snapshot = any(
        c.get('static_value') is None
        and ((c.get('data_path') or '') in relevant_paths or (c.get('data_path') or '').startswith('_pay_item:'))
        for c in columns
    )

    for i, p in enumerate(payslips, 1):
        row = 5 + i
        snapshot = _report_run_snapshot(p, snapshots) if uses_snapshot else None
        backfilled |= bool(snapshot and snapshot.backfilled)

        for col_idx, col_cfg in enumerate(columns, 1):
            key = col_cfg['key']
            data_path = col_cfg.get('data_path', key)
            static_value = col_cfg.get('static_value')

            # Extract value — use get_column_value for flexibility
            val = get_column_value(p, data_path, company, static_value, snapshot=snapshot)
            if static_value is None and val in (None, ''):
                unknown_allowance |= data_path in relevant_paths
                unknown_item |= data_path.startswith('_pay_item:')
            if key in NUMERIC_KEYS and val in (None, ''):
                incomplete_totals.add(key)

            # Handle row number specially
            if data_path == '_row_number':
                val = i

            if val is None:
                val = ''

            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.border = thin_border

            # Format numeric columns
            if key in NUMERIC_KEYS and isinstance(val, (int, float, Decimal)) and not isinstance(val, bool):
                cell.number_format = etb_format
                cell.alignment = data_align
                totals[key] = totals.get(key, Decimal('0')) + Decimal(str(val))
            elif key == 'row_number':
                cell.alignment = Alignment(horizontal='center')
            else:
                cell.alignment = name_align

    # --- Totals row ---
    totals_row = 5 + len(payslips) + 1
    # Find the first text column for the TOTALS label
    label_col = 1
    for col_idx, col_cfg in enumerate(columns, 1):
        if col_cfg['key'] in ('employee_name', 'employee_id'):
            label_col = col_idx
            break

    ws.cell(row=totals_row, column=label_col, value='TOTALS').font = totals_font
    ws.cell(row=totals_row, column=label_col).fill = totals_fill
    ws.cell(row=totals_row, column=label_col).border = thin_border

    for col_idx, col_cfg in enumerate(columns, 1):
        key = col_cfg['key']
        if key in totals and key not in incomplete_totals:
            cell = ws.cell(row=totals_row, column=col_idx, value=totals[key])
            cell.font = totals_font
            cell.fill = totals_fill
            cell.number_format = etb_format
            cell.alignment = data_align
            cell.border = thin_border

    # --- Gap note: basic salary not stored on legacy-path payslips ---
    shows_basic = any(c.get('data_path') in ('employee.basic_salary', 'basic_salary') for c in columns)
    missing = unfrozen_basic_count(payslips) if shows_basic else 0
    if missing:
        ws.cell(row=totals_row + 2, column=1, value=UNFROZEN_BASIC_NOTE.format(count=missing)).font = Font(
            italic=True, color='B03A2E'
        )

    if unknown_allowance:
        ws.cell(row=totals_row + 3, column=1, value=UNKNOWN_ALLOWANCE_NOTE).font = Font(italic=True, color='B03A2E')

    if unknown_item:
        ws.cell(row=totals_row + 4, column=1, value=UNKNOWN_ITEM_NOTE).font = Font(italic=True, color='B03A2E')
    if backfilled:
        ws.cell(row=totals_row + 5, column=1, value=BACKFILLED_ITEM_NOTE).font = Font(italic=True, color='B03A2E')
    if incomplete_totals:
        ws.cell(row=totals_row + 6, column=1, value=INCOMPLETE_TOTAL_NOTE).font = Font(italic=True, color='B03A2E')

    # --- Print setup ---
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.orientation = 'landscape'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_pension_report(payslips: list, company_name: str, period: str | None = None) -> bytes:
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
        from openpyxl.cell.cell import MergedCell  # noqa: F401
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        return _generate_pension_csv(payslips, company_name, period)

    if period is None:
        period = date.today().strftime('%B %Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Pension Report'

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
    headers = ['No.', 'Employee ID', 'Employee Name', 'Basic Salary', 'Employee 7%', 'Employer 11%', 'Total']
    col_widths = [6, 14, 22, 16, 14, 14, 16]
    for col, (header, width) in enumerate(zip(headers, col_widths, strict=False), 1):
        cell = ws.cell(row=5, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    # --- Data rows ---
    total_employee = Decimal('0')
    total_employer = Decimal('0')

    for i, p in enumerate(payslips, 1):
        emp = p.employee
        fig = frozen_figures(p)
        total = fig['pension_employee'] + fig['pension_employer']
        basic = fig['basic'] if fig['basic'] is not None else ''
        row = 5 + i

        ws.cell(row=row, column=1, value=i).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=2, value=emp.employee_id).alignment = name_align
        ws.cell(row=row, column=3, value=emp.name).alignment = name_align

        for col_idx, val in [(4, basic), (5, fig['pension_employee']), (6, fig['pension_employer']), (7, total)]:
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.number_format = etb_format
            cell.alignment = data_align

        for col_idx in range(1, 8):
            ws.cell(row=row, column=col_idx).border = thin_border

        total_employee += fig['pension_employee']
        total_employer += fig['pension_employer']

    # --- Totals row ---
    totals_row = 5 + len(payslips) + 1
    ws.cell(row=totals_row, column=3, value='TOTALS').font = totals_font
    ws.cell(row=totals_row, column=3).fill = totals_fill
    ws.cell(row=totals_row, column=3).border = thin_border
    for col_idx, val in [(5, total_employee), (6, total_employer), (7, total_employee + total_employer)]:
        cell = ws.cell(row=totals_row, column=col_idx, value=val)
        cell.font = totals_font
        cell.fill = totals_fill
        cell.number_format = etb_format
        cell.alignment = data_align
        cell.border = thin_border

    missing = unfrozen_basic_count(payslips)
    if missing:
        ws.cell(row=totals_row + 2, column=1, value=UNFROZEN_BASIC_NOTE.format(count=missing)).font = Font(
            italic=True, color='B03A2E'
        )

    # --- Print setup ---
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.orientation = 'landscape'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_yearly_summary(payslips: list, company_name: str, year: int) -> bytes:
    """Generate annual tax/pension summary per employee for a given year.

    Args:
        payslips: All Payslip objects for the year (with employee loaded).
        company_name: Company name for header.
        year: Calendar year (e.g. 2026).

    Returns:
        Excel file as bytes.
    """
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        return _generate_yearly_csv(payslips, company_name, year)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Year-End {year}'

    title_font = Font(bold=True, size=16, color='1A5276')
    subtitle_font = Font(bold=True, size=12, color='333333')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1A5276', end_color='1A5276', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    totals_font = Font(bold=True, size=11)
    totals_fill = PatternFill(start_color='D5E8D4', end_color='D5E8D4', fill_type='solid')
    etb_format = '#,##0.00'
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )
    name_align = Alignment(vertical='center')
    data_align = Alignment(horizontal='right', vertical='center')

    ws.merge_cells('A1:H1')
    ws['A1'] = f'{company_name}'
    ws['A1'].font = title_font

    ws.merge_cells('A2:H2')
    ws['A2'] = f'Year-End Summary — {year}'
    ws['A2'].font = subtitle_font

    ws.merge_cells('A3:H3')
    ws['A3'] = f'Generated: {date.today().strftime("%d %B %Y")}'
    ws['A3'].font = Font(italic=True, color='666666')

    headers = [
        'No.',
        'Employee ID',
        'Employee Name',
        'Total Gross',
        'Total Pension',
        'Total Tax',
        'Total Net',
        'Periods Paid',
    ]
    col_widths = [6, 14, 22, 16, 14, 14, 16, 12]
    for col, (header, width) in enumerate(zip(headers, col_widths, strict=False), 1):
        cell = ws.cell(row=5, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    from collections import defaultdict

    emp_agg = defaultdict(lambda: {'gross': 0, 'pension': 0, 'tax': 0, 'net': 0, 'periods': set()})
    for p in payslips:
        eid = p.employee_id
        emp_agg[eid]['gross'] += p.gross_salary
        emp_agg[eid]['pension'] += p.employee_pension
        emp_agg[eid]['tax'] += p.tax
        emp_agg[eid]['net'] += p.net_pay
        emp_agg[eid]['periods'].add(p.payroll_run_id)
        if not emp_agg[eid].get('name'):
            emp_agg[eid]['name'] = p.employee.name if p.employee else f'Employee {eid}'
        if not emp_agg[eid].get('emp_id'):
            emp_agg[eid]['emp_id'] = p.employee.employee_id if p.employee else str(eid)

    grand_gross = grand_pension = grand_tax = grand_net = 0
    for i, (eid, agg) in enumerate(sorted(emp_agg.items()), 1):
        row = 5 + i
        ws.cell(row=row, column=1, value=i).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=2, value=agg.get('emp_id', eid)).alignment = name_align
        ws.cell(row=row, column=3, value=agg.get('name', '')).alignment = name_align
        for col_idx, val in [(4, agg['gross']), (5, agg['pension']), (6, agg['tax']), (7, agg['net'])]:
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.number_format = etb_format
            cell.alignment = data_align
        ws.cell(row=row, column=8, value=len(agg['periods'])).alignment = Alignment(horizontal='center')
        for col_idx in range(1, 9):
            ws.cell(row=row, column=col_idx).border = thin_border
        grand_gross += agg['gross']
        grand_pension += agg['pension']
        grand_tax += agg['tax']
        grand_net += agg['net']

    totals_row = 5 + len(emp_agg) + 1
    ws.cell(row=totals_row, column=3, value='TOTALS').font = totals_font
    ws.cell(row=totals_row, column=3).fill = totals_fill
    ws.cell(row=totals_row, column=3).border = thin_border
    for col_idx, val in [(4, grand_gross), (5, grand_pension), (6, grand_tax), (7, grand_net)]:
        cell = ws.cell(row=totals_row, column=col_idx, value=val)
        cell.font = totals_font
        cell.fill = totals_fill
        cell.number_format = etb_format
        cell.alignment = data_align
        cell.border = thin_border

    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.orientation = 'landscape'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _generate_yearly_csv(payslips, company_name, year):
    """Fallback CSV for year-end summary."""
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Year-End Summary', company_name, str(year)])
    writer.writerow(
        ['No.', 'Employee ID', 'Name', 'Total Gross', 'Total Pension', 'Total Tax', 'Total Net', 'Periods Paid']
    )

    from collections import defaultdict

    emp_agg = defaultdict(lambda: {'gross': 0, 'pension': 0, 'tax': 0, 'net': 0, 'periods': set()})
    for p in payslips:
        eid = p.employee_id
        emp_agg[eid]['gross'] += p.gross_salary
        emp_agg[eid]['pension'] += p.employee_pension
        emp_agg[eid]['tax'] += p.tax
        emp_agg[eid]['net'] += p.net_pay
        emp_agg[eid]['periods'].add(p.payroll_run_id)
        if not emp_agg[eid].get('name'):
            emp_agg[eid]['name'] = p.employee.name if p.employee else f'Employee {eid}'
        if not emp_agg[eid].get('emp_id'):
            emp_agg[eid]['emp_id'] = p.employee.employee_id if p.employee else str(eid)

    from payroll_engine.security import prevent_csv_injection

    for i, (eid, agg) in enumerate(sorted(emp_agg.items()), 1):
        writer.writerow(
            [
                i,
                prevent_csv_injection(agg.get('emp_id', eid)),
                prevent_csv_injection(agg.get('name', '')),
                agg['gross'],
                agg['pension'],
                agg['tax'],
                agg['net'],
                len(agg['periods']),
            ]
        )
    return output.getvalue().encode('utf-8')


def _generate_erca_csv(payslips, company_name, period):
    """Fallback CSV generation if openpyxl not installed.
    Uses ERCA portal column format.
    """
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ERCA Tax Filing Report', company_name, period or ''])
    # ERCA portal headers
    writer.writerow(
        [
            'Employee Full Name',
            'Start Date',
            'End Date',
            'Basic Salary',
            'Transport Allowance',
            'Taxable Transport Allowance',
            'Over Time',
            'Other Taxable Benefit',
            'Total Taxable',
            'Tax withheld',
        ]
    )
    from payroll_engine.report_templates import get_column_value
    from payroll_engine.security import prevent_csv_injection

    unknown_allowance = False
    backfilled = False
    snapshots = {}
    for _i, p in enumerate(payslips, 1):
        emp = p.employee
        fig = frozen_figures(p)
        snapshot = _report_run_snapshot(p, snapshots)
        breakdown = [
            get_column_value(p, path, snapshot=snapshot)
            for path in ('_transport_allowance', '_taxable_transport', '_other_taxable')
        ]
        unknown_allowance |= any(value == '' for value in breakdown)
        backfilled |= bool(snapshot and snapshot.backfilled)
        start_date = emp.start_date.strftime('%d/%m/%Y') if emp.start_date else ''

        writer.writerow(
            [
                prevent_csv_injection(emp.name),
                start_date,
                '',  # End Date
                '' if fig['basic'] is None else fig['basic'],
                breakdown[0],
                breakdown[1],
                '' if fig['overtime'] is None else fig['overtime'],  # Over Time
                breakdown[2],
                '' if fig['taxable'] is None else fig['taxable'],  # Total Taxable
                fig['tax'],  # Tax withheld
            ]
        )
    missing = unfrozen_basic_count(payslips)
    if missing:
        writer.writerow([UNFROZEN_BASIC_NOTE.format(count=missing)])
    if unknown_allowance:
        writer.writerow([UNKNOWN_ALLOWANCE_NOTE])
    if backfilled:
        writer.writerow([BACKFILLED_ITEM_NOTE])
    return output.getvalue().encode('utf-8')


def _generate_pension_csv(payslips, company_name, period):
    """Fallback CSV generation if openpyxl not installed."""
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Pension Contribution Report', company_name, period or ''])
    writer.writerow(['No.', 'Employee ID', 'Name', 'Basic Salary', 'Employee 7%', 'Employer 11%', 'Total'])
    from payroll_engine.security import prevent_csv_injection

    for i, p in enumerate(payslips, 1):
        emp = p.employee
        fig = frozen_figures(p)
        writer.writerow(
            [
                i,
                prevent_csv_injection(emp.employee_id),
                prevent_csv_injection(emp.name),
                '' if fig['basic'] is None else fig['basic'],
                fig['pension_employee'],
                fig['pension_employer'],
                fig['pension_employee'] + fig['pension_employer'],
            ]
        )
    missing = unfrozen_basic_count(payslips)
    if missing:
        writer.writerow([UNFROZEN_BASIC_NOTE.format(count=missing)])
    return output.getvalue().encode('utf-8')
