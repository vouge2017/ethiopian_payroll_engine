"""
PDF Payslip Generator for Ethiopian Payroll Engine

Uses ReportLab to generate professional payslips in PDF format.
Output: A4-sized PDF with company header, employee details, earnings,
deductions, and net pay summary.

Font: NotoSansEthiopic for full Amharic + Latin rendering.
"""

import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register NotoSansEthiopic font (covers both Ethiopic and Latin glyphs)
_FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
_FONT_PATH = os.path.join(_FONT_DIR, 'NotoSansEthiopic-Regular.ttf')
_FONT_REGISTERED = False

def _ensure_font():
    """Register the font once. Safe to call multiple times."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    if os.path.exists(_FONT_PATH):
        pdfmetrics.registerFont(TTFont('NotoSansEthiopic', _FONT_PATH))
        _FONT_REGISTERED = True

# Register on module load
_ensure_font()

# Font names — use NotoSansEthiopic for everything (covers Latin + Ethiopic)
FONT = 'NotoSansEthiopic'
FONT_BOLD = 'NotoSansEthiopic'  # No bold variant available; same font

PRIMARY = HexColor('#1a5276')
ACCENT = HexColor('#2e86c1')
LIGHT_BG = HexColor('#eaf2f8')
DARK_BG = HexColor('#1a5276')


def generate_payslip(emp: dict, output_dir: str = None) -> str:
    """
    Generate a PDF payslip for a single employee.

    Args:
        emp: Employee dict with keys: id, name, basic, allowances, gross,
             tax, pension_employee, pension_employer, net, bank,
             tax_explanation
        output_dir: Directory to save PDF (defaults to current directory)

    Returns:
        Absolute path to the generated PDF file
    """
    _ensure_font()

    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    filename = f"payslip_{emp['id']}_{date.today().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontName=FONT, textColor=PRIMARY, fontSize=18, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'],
        fontName=FONT, textColor=ACCENT, fontSize=10,
        alignment=TA_CENTER, spaceAfter=12
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading3'],
        fontName=FONT, textColor=PRIMARY, fontSize=11,
        spaceBefore=10, spaceAfter=4
    )
    normal_style = ParagraphStyle(
        'NormalCustom', parent=styles['Normal'],
        fontName=FONT, fontSize=9, spaceAfter=2
    )

    elements = []

    # Header
    elements.append(Paragraph("ETHIOPIAN PAYROLL ENGINE", title_style))
    elements.append(Paragraph("Monthly Payslip / ወርሃዊ ደመወዝ ወረቀት", subtitle_style))
    elements.append(Spacer(1, 8))

    # Employee Info Table
    info_data = [
        ['Employee ID / መለያ:', emp['id'],
         'Date / ቀን:', datetime.now().strftime('%Y-%m-%d')],
        ['Name / ስም:', emp['name'],
         'Department / ክፍል:', 'General'],
    ]
    info_table = Table(info_data, colWidths=[35 * mm, 50 * mm, 35 * mm, 50 * mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY),
        ('TEXTCOLOR', (2, 0), (2, -1), PRIMARY),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # Earnings
    elements.append(Paragraph("Earnings / ገቢ", section_style))
    earnings_data = [
        ['Description / መግለጫ', 'Amount (ETB) / መጠን (ብር)'],
        ['Basic Salary / መሰረታዊ ደመወዝ', f"{emp['basic']:,.2f}"],
        ['Allowances / አበሪዎች', f"{emp['allowances']:,.2f}"],
        ['Gross Salary / ጠቅላይ ደመወዝ', f"{emp['gross']:,.2f}"],
    ]
    earnings_table = Table(earnings_data, colWidths=[100 * mm, 70 * mm])
    earnings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(earnings_table)
    elements.append(Spacer(1, 10))

    # Deductions
    elements.append(Paragraph("Deductions / ከፊዎች", section_style))
    deductions_data = [
        ['Description / መግለጫ', 'Amount (ETB) / መጠን (ብር)'],
        ['Income Tax / የገቢ ታክስ', f"{emp['tax']:,.2f}"],
        ['Employee Pension (7%) / የሰራተኛ እቅድ', f"{emp['pension_employee']:,.2f}"],
        ['Total Deductions / ጠቅላይ ከፊዎች',
         f"{emp['tax'] + emp['pension_employee']:,.2f}"],
    ]
    deductions_table = Table(deductions_data, colWidths=[100 * mm, 70 * mm])
    deductions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(deductions_table)
    elements.append(Spacer(1, 10))

    # Net Pay
    elements.append(Paragraph("Net Pay / ንፅ ደመወዝ", section_style))
    net_data = [['Net Pay / ንፅ ደመወዝ (ETB)', f"{emp['net']:,.2f}"]]
    net_table = Table(net_data, colWidths=[100 * mm, 70 * mm])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, -1), white),
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 15))

    # Payment method
    payment_method = emp.get('bank', 'Not specified')
    elements.append(Paragraph(
        f"Payment Method / የክፍያ ዘዴ: {payment_method}",
        normal_style
    ))
    elements.append(Spacer(1, 10))

    # Footer
    elements.append(Paragraph(
        "This is a computer-generated document. / ይህ ሰነድ በኮምፒውተር የተመረተ ነው።",
        ParagraphStyle('Footer', parent=styles['Normal'],
                       fontName=FONT, fontSize=7,
                       textColor=HexColor('#888888'), alignment=TA_CENTER)
    ))

    doc.build(elements)
    return filepath
