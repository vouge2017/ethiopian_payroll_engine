"""Help & Support blueprint — in-app FAQ and contextual guidance."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

help_bp = Blueprint('help', __name__)


@help_bp.route('/help')
@login_required
def help_center():
    """Main help center with searchable FAQ."""
    section = request.args.get('section', 'all')
    return render_template('help.html', section=section, faq_data=FAQ_DATA)


@help_bp.route('/help/search')
@login_required
def help_search():
    """Search FAQ via query param (for AJAX/JS search)."""
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify(results=[])

    results = []
    for category in FAQ_DATA:
        for item in category['questions']:
            if q in item['question'].lower() or q in item['answer'].lower():
                results.append({
                    'category': category['title'],
                    'question': item['question'],
                    'answer': item['answer'],
                    'anchor': item.get('anchor', ''),
                })

    return jsonify(results=results[:20])


# ─── FAQ Data ─────────────────────────────────────────────────────────────────

FAQ_DATA = [
    {
        'id': 'tax',
        'title': 'Tax & Income Tax',
        'icon': 'bi-percent',
        'questions': [
            {
                'anchor': 'tax-brackets',
                'question': 'What are the current tax brackets?',
                'answer': 'Ethiopia uses progressive tax rates:\n'
                     '- 0–2,000 ETB: 0%\n'
                     '- 2,001–4,000 ETB: 15%\n'
                     '- 4,001–7,000 ETB: 20%\n'
                     '- 7,001–10,000 ETB: 25%\n'
                     '- 10,001–14,000 ETB: 30%\n'
                     '- 14,001+ ETB: 35%\n\n'
                     'These brackets apply to your **taxable income** (gross salary minus pension contribution). '
                     'Source: Proclamation No. 1395/2025, Article 36(1).',
            },
            {
                'anchor': 'tax-calculation',
                'question': 'How is my income tax calculated step by step?',
                'answer': '1. Start with your gross salary\n'
                     '2. Subtract 7% pension → this gives taxable income\n'
                     '3. Apply each tax bracket to portions of taxable income\n'
                     '4. Add up the tax from each bracket → total tax\n\n'
                     'Example: Gross 10,000 ETB\n'
                     '- Pension: 700 (7% of 10,000)\n'
                     '- Taxable: 9,300\n'
                     '- Tax: 0 + 300 + 600 + 575 + 0 = 1,475 tax',
            },
        ],
    },
    {
        'id': 'pension',
        'title': 'Pension (Private Pension)',
        'icon': 'bi-piggy-bank',
        'questions': [
            {
                'anchor': 'pension-rates',
                'question': 'What are the pension contribution rates?',
                'answer': '- **Employee contributes:** 7% of basic salary\n'
                     '- **Employer contributes:** 11% of basic salary\n'
                     '- **Total:** 18% of basic salary goes to your pension\n\n'
                     'Source: Proclamation No. 1268/2022.',
            },
            {
                'anchor': 'pension-ceiling',
                'question': 'Is there a salary ceiling for pension contributions?',
                'answer': 'No. There is **no salary cap** for pension contributions in Ethiopia. '
                     'The 7% employee / 11% employer rates apply to your full basic salary, '
                     'regardless of how much you earn.\n\n'
                     'Source: Proclamation No. 1268/2022 — no ceiling specified.',
            },
            {
                'anchor': 'pension-basic-vs-gross',
                'question': 'Is pension calculated on basic salary or gross salary?',
                'answer': 'Pension is calculated on **basic salary only**. Allowances, bonuses, '
                     'and overtime are not included in the pension calculation.',
            },
            {
                'anchor': 'pension-employer',
                'question': 'Does my employer also contribute?',
                'answer': 'Yes. Your employer contributes 11% of your basic salary to your pension. '
                     'This is in addition to your 7% contribution. The employer contribution '
                     'does not reduce your take-home pay.',
            },
        ],
    },
    {
        'id': 'overtime',
        'title': 'Overtime',
        'icon': 'bi-clock-history',
        'questions': [
            {
                'anchor': 'overtime-rates',
                'question': 'How is overtime pay calculated?',
                'answer': 'Overtime is paid at higher rates than normal working hours:\n\n'
                     '- **Day overtime (6am-10pm):** 1.5× your hourly rate\n'
                     '- **Night overtime (10pm-6am):** 1.75× your hourly rate\n'
                     '- **Weekly rest day:** 2.0× your hourly rate\n'
                     '- **Public holiday:** 2.5× your hourly rate\n\n'
                     '**Limits:** Max 4 hours/day, 12 hours/week (Art. 67(2)).'
                     '- **Rest day + holiday:** 2.5× your hourly rate\n\n'
                     'Hourly rate = Basic Salary ÷ 208 (26 days × 8 hours)\n\n'
                     'Source: Proclamation No. 1156/2019, Article 68.',
            },
            {
                'anchor': 'overtime-limits',
                'question': 'Is there a limit on overtime hours?',
                'answer': 'Yes:\n'
                     '- **Monthly limit:** 20 hours\n'
                     '- **Yearly limit:** 100 hours\n\n'
                     'If you exceed these limits, the system will flag a warning. '
                     'Source: Proclamation No. 1156/2019, Article 89.',
            },
            {
                'anchor': 'overtime-hourly',
                'question': 'How is the hourly rate calculated?',
                'answer': 'Hourly rate = Basic Salary ÷ 208\n\n'
                     '208 = 26 working days × 8 hours per day.\n'
                     'This uses the Ethiopian convention of 26 working days per month (6-day work week).',
            },
        ],
    },
    {
        'id': 'leave',
        'title': 'Leave & Time Off',
        'icon': 'bi-calendar-event',
        'questions': [
            {
                'anchor': 'annual-leave',
                'question': 'How many annual leave days do I get?',
                'answer': '- **Year 1:** 14 working days\n'
                     '- **Each additional year:** +1 day\n'
                     '- **Maximum:** 30 days\n\n'
                     'Your company may offer more days through company policy. '
                     'Source: Proclamation No. 1156/2019.',
            },
            {
                'anchor': 'sick-leave',
                'question': 'How does sick leave work?',
                'answer': 'Total sick leave: up to 180 days (6 months)\n\n'
                     '- **Days 1–30:** Paid at 100% of salary\n'
                     '- **Days 31–90:** Paid at 50% of salary\n'
                     '- **Days 91–180:** Unpaid\n\n'
                     'Source: Proclamation No. 1156/2019.',
            },
            {
                'anchor': 'maternity-leave',
                'question': 'How many days of maternity leave?',
                'answer': '**120 days** (approximately 4 months) of paid maternity leave. '
                     'This is a statutory right for all female employees.\n\n'
                     'Source: Proclamation No. 1156/2019.',
            },
            {
                'anchor': 'paternity-leave',
                'question': 'How many days of paternity leave?',
                'answer': '**3 working days** of paid paternity leave.\n\n'
                     'Source: Proclamation No. 1156/2019.',
            },
            {
                'anchor': 'special-leave',
                'question': 'What is special leave?',
                'answer': '**3 days** of paid leave for special circumstances (e.g., marriage, death of a family member). '
                     'Your company may have additional policies.\n\n'
                     'Source: Proclamation No. 1156/2019.',
            },
        ],
    },
    {
        'id': 'severance',
        'title': 'Severance & Termination',
        'icon': 'bi-box-arrow-right',
        'questions': [
            {
                'anchor': 'severance-formula',
                'question': 'How is severance pay calculated?',
                'answer': 'Severance = Monthly Basic Salary × Years of Service\n\n'
                     '- **Maximum:** 12 months (cap)\n'
                     '- **Eligible for:** Redundancy, mutual agreement termination\n\n'
                     'Source: Proclamation No. 1156/2019, Articles 40–42.',
            },
            {
                'anchor': 'severance-cap',
                'question': 'Is there a maximum severance amount?',
                'answer': 'Yes. Severance is capped at **12 months** of basic salary, '
                     'regardless of how many years you\'ve worked.\n\n'
                     'Source: Proclamation No. 1156/2019, Article 42.',
            },
        ],
    },
    {
        'id': 'payroll',
        'title': 'Payroll & Payslips',
        'icon': 'bi-receipt',
        'questions': [
            {
                'anchor': 'payslip-download',
                'question': 'How do I download my payslip?',
                'answer': 'Go to **My Payslips** from the sidebar. Click on any payslip to view details, '
                     'then click **Download PDF** to get a printable copy.',
            },
            {
                'anchor': 'payslip-calculation',
                'question': 'How do I understand my payslip calculation?',
                'answer': 'Each payslip shows a **step-by-step calculation flow**:\n'
                     '1. Gross Salary (basic + allowances)\n'
                     '2. Pension deduction (7% of basic)\n'
                     '3. Taxable income (gross − pension)\n'
                     '4. Tax calculation by bracket\n'
                     '5. Personal relief applied\n'
                     '6. Net pay (gross − pension − tax − other deductions)\n\n'
                     'Click on any payslip to see the full breakdown.',
            },
            {
                'anchor': 'payroll-approval',
                'question': 'Why does payroll need approval?',
                'answer': 'Payroll goes through a review → approval workflow:\n'
                     '1. **Upload/Review:** Owner or accountant uploads employee data\n'
                     '2. **Approval:** Owner approves with password (and MFA if enabled)\n'
                     '3. **Disbursement:** Bank file is generated for salary payments\n\n'
                     'This two-step process prevents accidental payments and creates an audit trail.',
            },
            {
                'anchor': 'payroll-undo',
                'question': 'Can I undo a payroll approval?',
                'answer': 'Yes, but only within **1 hour** of approval and only if disbursement hasn\'t started. '
                     'After that window, you can create an **adjustment payslip** to correct errors.',
            },
        ],
    },
    {
        'id': 'compliance',
        'title': 'Compliance & Filing',
        'icon': 'bi-shield-check',
        'questions': [
            {
                'anchor': 'erca-deadline',
                'question': 'When is the ERCA tax filing deadline?',
                'answer': 'The monthly tax filing deadline is the **25th of the following month**. '
                     'For example, June payroll taxes must be filed by July 25th.',
            },
            {
                'anchor': 'pension-deadline',
                'question': 'When is the pension payment deadline?',
                'answer': 'Pension contributions must be paid by the **15th of the following month**.',
            },
            {
                'anchor': 'cash-limit',
                'question': 'What is the cash payment limit?',
                'answer': 'Ethiopian law requires electronic payment for salaries above **ETB 50,000**. '
                     'If any employee's net pay exceeds this amount, the system will flag it.\n\n'
                     'Source: Proclamation No. 1395/2025, Article 81.',
            },
            {
                'anchor': 'record-retention',
                'question': 'How long must payroll records be kept?',
                'answer': 'Payroll records (payslips, tax filings) must be retained for **10 years** '
                     'as per Ethiopian tax law. The system automatically manages PDF retention.',
            },
        ],
    },
    {
        'id': 'account',
        'title': 'Account & Security',
        'icon': 'bi-person-lock',
        'questions': [
            {
                'anchor': 'mfa-setup',
                'question': 'How do I enable two-factor authentication (MFA)?',
                'answer': 'Go to **Team Settings** → click **Enable MFA**. '
                     'You\'ll need an authenticator app (Google Authenticator, Authy, etc.). '
                     'Scan the QR code and enter the 6-digit code to verify.\n\n'
                     'MFA is required for payroll approval.',
            },
            {
                'anchor': 'password-change',
                'question': 'How do I change my password?',
                'answer': 'Go to **Team Settings** → **Change Password**. '
                     'Your new password must be at least 8 characters and not commonly used.',
            },
            {
                'anchor': 'forgot-password',
                'question': 'I forgot my password. How do I reset it?',
                'answer': 'Click **Forgot Password** on the login page. '
                     'Enter your phone number and you\'ll receive a reset link. '
                     'The link expires in 1 hour.',
            },
        ],
    },
]


@help_bp.route('/help/faq-data')
@login_required
def faq_data():
    """Return FAQ data as JSON (for dynamic rendering or search)."""
    return jsonify(FAQ_DATA)
