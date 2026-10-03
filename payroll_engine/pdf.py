"""
PDF Payslip Generator for Ethiopian Payroll Engine

Uses ReportLab to generate professional payslips in PDF format.
Output: A4-sized PDF with company header, employee details, earnings,
deductions, and net pay summary.

Fonts: Helvetica for Latin and digits; embedded NotoSansEthiopic for Amharic.
"""

import os
import re
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, SimpleDocTemplate, Spacer, TableStyle
from reportlab.platypus import Paragraph as _Paragraph
from reportlab.platypus import Table as _Table

# Register NotoSansEthiopic font
_FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
_FONT_PATH = os.path.join(_FONT_DIR, 'NotoSansEthiopic-Regular.ttf')
_FONT_REGISTERED = False


def _item_label(line_item):
    """Bilingual display label for one engine line item.

    Labels come from PayItemType.name_en / name_am via the engine's line item,
    never from a hardcoded string in this module. A per-employee custom_label
    wins over the type name, and if only one language is available we show just
    that rather than a half-empty "Label /".
    """
    en = (line_item.get('item_label') or '').strip()
    am = (line_item.get('item_label_am') or '').strip()
    if en and am and en != am:
        return f'{en} / {am}'
    return en or am or (line_item.get('item_key') or '').strip()


def _ensure_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    if os.path.exists(_FONT_PATH):
        pdfmetrics.registerFont(TTFont('NotoSansEthiopic', _FONT_PATH))
        _FONT_REGISTERED = True


_ensure_font()


def _ensure_pdf(payslip, emp, company_info=None):
    """Ensure a payslip has a generated PDF. Returns the file path.

    Handles race conditions: if two requests hit the same payslip
    simultaneously, only one generates. The other reads the result.

    State machine: not_generated → generating → generated / failed
    """
    from payroll_engine import db

    # Fast path: already generated and file exists
    if payslip.pdf_status == 'generated' and payslip.pdf_file_path and os.path.exists(payslip.pdf_file_path):
        return payslip.pdf_file_path

    # Try to claim the 'generating' state (race-condition guard)
    # Use a DB-level atomic update so only one request wins
    from sqlalchemy import update

    from payroll_engine.models import Payslip

    result = db.session.execute(
        update(Payslip)
        .where(Payslip.id == payslip.id, Payslip.pdf_status != 'generating')
        .values(pdf_status='generating')
    )
    db.session.flush()

    if result.rowcount == 0:
        # Another request claimed it — wait and read the result
        import time

        for _ in range(50):  # Up to 5 seconds
            db.session.expire(payslip)
            if payslip.pdf_status == 'generated' and payslip.pdf_file_path:
                return payslip.pdf_file_path
            if payslip.pdf_status == 'failed':
                raise RuntimeError(f'PDF generation previously failed for payslip {payslip.id}')
            time.sleep(0.1)
        # Timed out — try generating anyway

    # We claimed 'generating' — build the data and generate
    try:
        from payroll_engine.payroll import generate_calculation_flow

        emp_data = {
            'id': emp.employee_id,
            'name': emp.name,
            'basic': emp.basic_salary,
            'allowances': emp.allowances,
            'gross': payslip.gross_salary,
            'tax': payslip.tax,
            'pension_employee': payslip.employee_pension,
            'pension_employer': payslip.employer_pension,
            'net': payslip.net_pay,
            'bank': emp.bank_or_telebirr or '',
            'department': emp.department or '',
            'position': emp.position or '',
            'period': '',
            'tax_explanation': '',
        }
        from payroll_engine.services.worksheet_review import published_row

        snapshot = published_row(payslip)
        if snapshot:
            emp_data.update(snapshot)
            emp_data['period'] = (
                date.fromisoformat(snapshot['worksheet_period_start']).strftime('%B %Y') + ' (Gregorian)'
            )
        emp_data['calc_flow'] = None if emp_data.get('correction_note') else generate_calculation_flow(emp_data)

        # Get period from the payroll run
        from payroll_engine.models import PayrollRun

        run = PayrollRun.query.filter_by(id=payslip.payroll_run_id, company_id=payslip.company_id).first()
        if run and not snapshot:
            emp_data['period'] = run.period or (run.run_date.strftime('%B %Y') if run.run_date else '')

        if company_info is None:
            from payroll_engine.models import Company

            company = db.session.get(Company, run.company_id) if run else None
            company_info = {
                'name': company.name if company else 'Company',
                'address': company.address if company else '',
                'tin': company.tin if company else '',
                'phone': company.phone if company else '',
                'logo_path': os.path.join('payroll_engine', 'static', company.logo_path)
                if company and company.logo_path
                else '',
            }

        from flask import current_app

        output_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'], 'payslips', str(payslip.company_id), str(payslip.payroll_run_id)
        )
        pdf_path = generate_payslip(emp_data, company=company_info, output_dir=output_dir, file_key=str(payslip.id))
        payslip.pdf_file_path = pdf_path
        payslip.pdf_status = 'generated'
        db.session.flush()
        return pdf_path

    except Exception:
        payslip.pdf_status = 'failed'
        db.session.flush()
        raise


FONT = 'Helvetica'
# Updated2026 design system colors
PRIMARY = HexColor('#2563eb')
ACCENT = HexColor('#1d4ed8')
LIGHT_BG = HexColor('#eff6ff')
DARK_BG = HexColor('#0f172a')
NET_BG = HexColor('#10b981')
GRAY = HexColor('#64748b')
BORDER = HexColor('#e2e8f0')
SUCCESS = HexColor('#10b981')
WARNING = HexColor('#f59e0b')
DANGER = HexColor('#ef4444')


def _bilingual_markup(text):
    # NotoSansEthiopic contains Ethiopic glyphs but lacks Latin letters/digits.
    # Keep Latin in Helvetica and explicitly select the embedded Ethiopic font.
    return re.sub(r'([\u1200-\u139f\u2d80-\u2ddf\uab00-\uab2f]+)', r'<font name="NotoSansEthiopic">\1</font>', text)


def _paragraph(text, *args, **kwargs):
    return _Paragraph(_bilingual_markup(text), *args, **kwargs)


def _table(data, *args, **kwargs):
    style = ParagraphStyle('BilingualCell', fontName=FONT, fontSize=8, leading=11)
    rows = [
        [
            _paragraph(escape(cell), style)
            if isinstance(cell, str) and re.search(r'[\u1200-\u139f\u2d80-\u2ddf\uab00-\uab2f]', cell)
            else cell
            for cell in row
        ]
        for row in data
    ]
    return _Table(rows, *args, **kwargs)


def generate_payslip(
    emp: dict, output_dir: str | None = None, company: dict | None = None, file_key: str | None = None
) -> str:
    """
    Generate a PDF payslip for a single employee.

    Args:
        emp: Employee dict with keys: id, name, basic, allowances, gross,
             tax, pension_employee, pension_employer, net, bank,
             tax_explanation, department, position, period
        output_dir: Directory to save PDF
        company: Company dict with keys: name, address, phone, tin, logo_path

    Returns:
        Absolute path to the generated PDF file
    """
    _ensure_font()

    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    from werkzeug.utils import secure_filename

    filename_id = secure_filename(file_key or str(emp['id'])) or 'employee'
    filename = f'payslip_{filename_id}_{date.today().strftime("%Y%m%d")}.pdf'
    filepath = os.path.join(output_dir, filename)

    # Company defaults
    company = company or {}
    company_name = company.get('name', 'Company')
    company_address = company.get('address', '')
    company_tin = company.get('tin', '')
    company_phone = company.get('phone', '')
    logo_path = company.get('logo_path', '')

    # Employee defaults
    department = emp.get('department', '')
    position = emp.get('position', '')
    period = emp.get('period', date.today().strftime('%B %Y'))

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'], fontName=FONT, textColor=PRIMARY, fontSize=16, spaceAfter=2
    )
    ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName=FONT,
        textColor=ACCENT,
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading3'], fontName=FONT, textColor=PRIMARY, fontSize=10, spaceBefore=8, spaceAfter=3
    )
    ParagraphStyle('NormalCustom', parent=styles['Normal'], fontName=FONT, fontSize=8, spaceAfter=2)
    ParagraphStyle('Label', parent=styles['Normal'], fontName=FONT, fontSize=8, textColor=PRIMARY)
    ParagraphStyle('Value', parent=styles['Normal'], fontName=FONT, fontSize=8)

    elements = []

    # ── HEADER: Logo + Company Info ──
    header_data = []

    # Logo column
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, height=18 * mm, width=18 * mm)
            logo_img.hAlign = 'LEFT'
        except Exception:
            logo_img = _paragraph(f'<b>{company_name[0]}</b>', title_style)
    else:
        # First letter circle as placeholder
        logo_img = _paragraph(
            f'<font size="20" color="#1a5276"><b>{company_name[0].upper()}</b></font>',
            ParagraphStyle('LogoLetter', alignment=TA_CENTER, fontName=FONT),
        )

    # Company info column
    company_lines = [f'<b>{company_name}</b>']
    if company_address:
        company_lines.append(company_address)
    if company_tin:
        company_lines.append(f'TIN: {company_tin}')
    if company_phone:
        company_lines.append(f'Tel: {company_phone}')
    company_info = _paragraph(
        '<br/>'.join(company_lines), ParagraphStyle('CompanyInfo', fontName=FONT, fontSize=9, alignment=TA_LEFT)
    )

    # Period column
    period_info = _paragraph(
        f'<b>Payslip</b><br/>{period}',
        ParagraphStyle('Period', fontName=FONT, fontSize=9, alignment=TA_RIGHT, textColor=PRIMARY),
    )

    header_data.append([logo_img, company_info, period_info])
    header_table = _table(header_data, colWidths=[22 * mm, 100 * mm, 48 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(header_table)

    # Divider line
    divider = _table([['']], colWidths=[170 * mm], rowHeights=[1])
    divider.setStyle(
        TableStyle(
            [
                ('LINEABOVE', (0, 0), (-1, 0), 1.5, PRIMARY),
            ]
        )
    )
    elements.append(divider)
    elements.append(Spacer(1, 6))

    # ── EMPLOYEE INFO (bilingual) ──
    info_data = [
        ['Employee ID / የሰራተኛ መለያ:', emp['id'], 'Name / ስም:', emp['name']],
        ['Department / ክፍል:', department or '—', 'Position / ሹም:', position or '—'],
        ['Pay Period / የክፍያ ጊዜ:', period, 'Payment / የክፍያ ዘዴ:', emp.get('bank', '—')],
    ]
    info_table = _table(info_data, colWidths=[35 * mm, 48 * mm, 35 * mm, 52 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ('FONTNAME', (0, 0), (-1, -1), FONT),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY),
                ('TEXTCOLOR', (2, 0), (2, -1), PRIMARY),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 8))

    if emp.get('correction_note'):
        elements.append(_paragraph(escape(emp['correction_note']), styles['Normal']))
        elements.append(Spacer(1, 8))

    # ── EARNINGS ──
    elements.append(_paragraph('Earnings / ገቢዎች', section_style))
    earnings_data = [
        ['Description', 'Amount (ETB)'],
    ]

    # line_items is the elements engine's own breakdown, snapshotted onto the
    # payslip at approval time. It is authoritative when present: the PDF is
    # generated lazily, so recomputing here could diverge from what was paid.
    # Bilingual labels come from PayItemType.name_en / name_am.
    line_items = emp.get('line_items') or []
    earning_lines = [li for li in line_items if li.get('classification') == 'earning' and li.get('earned_amount')]
    deduction_lines = [li for li in line_items if li.get('classification') in ('deduction', 'tax')]

    if earning_lines:
        for li in earning_lines:
            label = _item_label(li)
            if label:
                earnings_data.append([label, f'{li.get("earned_amount", 0):,.2f}'])
    else:
        # Legacy payslip with no engine breakdown (not yet backfilled).
        earnings_data.append(['Basic Salary', f'{emp["basic"]:,.2f}'])
        if emp.get('allowances', 0) > 0:
            earnings_data.append(['Allowances', f'{emp["allowances"]:,.2f}'])
        if emp.get('ot_pay', 0) > 0:
            earnings_data.append(['Overtime', f'{emp["ot_pay"]:,.2f}'])

    earnings_data.append(['Gross Salary', f'{emp["gross"]:,.2f}'])

    earnings_table = _table(earnings_data, colWidths=[110 * mm, 60 * mm])
    earnings_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, -1), FONT),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(earnings_table)
    elements.append(Spacer(1, 6))

    # ── DEDUCTIONS ──
    elements.append(_paragraph('Deductions / ተቀናሾች', section_style))
    deductions_data = [
        ['Description', 'Amount (ETB)'],
    ]

    # Pension and income tax are engine-managed SYSTEM items. They are always
    # present on the payslip, but when the engine supplied a breakdown we use
    # its labels so a company that renamed them is honoured.
    if deduction_lines:
        for li in deduction_lines:
            label = _item_label(li)
            if label:
                deductions_data.append([label, f'{li.get("earned_amount", 0):,.2f}'])
    else:
        # Pension
        deductions_data.append(['Employee Pension (7%)', f'{emp["pension_employee"]:,.2f}'])

        # Tax with bracket breakdown
        tax_breakdown = emp.get('tax_breakdown')
        if tax_breakdown and tax_breakdown.get('brackets'):
            deductions_data.append(['Income Tax', f'{emp["tax"]:,.2f}'])
            for b in tax_breakdown['brackets']:
                if b['rate_pct'] == 0:
                    label = f'  {b["rate_pct"]}% on first {b["upper"]:,.0f}'
                elif b['upper'] is None:
                    label = f'  {b["rate_pct"]}% on remaining {b["taxable_amount"]:,.0f}'
                else:
                    label = f'  {b["rate_pct"]}% on next {b["taxable_amount"]:,.0f}'
                deductions_data.append([label, f'{b["bracket_tax"]:,.2f}'])
        else:
            deductions_data.append(['Income Tax', f'{emp["tax"]:,.2f}'])

    total_deductions = emp['gross'] - emp['net']
    deductions_data.append(['Total Deductions', f'{total_deductions:,.2f}'])
    deductions_table = _table(deductions_data, colWidths=[110 * mm, 60 * mm])
    deductions_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, -1), FONT),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(deductions_table)
    elements.append(Spacer(1, 4))

    # ── CALCULATION FLOW SUMMARY ──
    flow_data = emp.get('calc_flow')
    if flow_data and flow_data.get('steps'):
        flow_summary = (
            f'Gross {emp["gross"]:,.2f} - total deductions {total_deductions:,.2f} = net {emp["net"]:,.2f} (ETB)'
        )
        elements.append(
            _paragraph(
                flow_summary,
                ParagraphStyle(
                    'FlowSummary',
                    fontName=FONT,
                    fontSize=7,
                    textColor=HexColor('#666666'),
                    alignment=TA_CENTER,
                    spaceAfter=4,
                ),
            )
        )

    elements.append(Spacer(1, 8))

    # ── NET PAY ──
    net_data = [['NET PAY / የተቀረ ክፍያ (ETB)', f'{emp["net"]:,.2f}']]
    net_table = _table(net_data, colWidths=[110 * mm, 60 * mm])
    net_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), NET_BG),
                ('TEXTCOLOR', (0, 0), (-1, -1), white),
                ('FONTNAME', (0, 0), (-1, -1), FONT),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(net_table)
    elements.append(Spacer(1, 12))

    # ── FOOTER ──
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'], fontName=FONT, fontSize=7, textColor=HexColor('#888888'), alignment=TA_CENTER
    )
    elements.append(_paragraph('This is a computer-generated document. / ይህ ሰነድ በኮምፒውተር የተመረተ ነው።', footer_style))
    if company_tin:
        elements.append(_paragraph(f'{company_name} — TIN: {company_tin}', footer_style))

    doc.build(elements)
    return filepath
