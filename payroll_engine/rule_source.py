"""
Rule Source — Every calculation traces back to its legal basis.

Each rule has:
- source: The legal reference (proclamation, article, section)
- verified: Whether an accountant has confirmed this rule
- verified_at: When it was last verified
- verified_by: Who verified it
- effective_date: When the rule became effective
- notes: Any accountant notes

When a rule changes (new proclamation), the system flags it
and the accountant re-verifies. The explanation updates automatically.

Usage:
    from payroll_engine.rule_source import RULE_SOURCES, get_rule_source
    source = get_rule_source('tax_brackets')
"""
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class RuleSource:
    """A single rule with its legal source."""
    rule_id: str                # Machine-readable ID
    name: str                   # Human-readable name
    name_am: str                # Amharic name
    source: str                 # Legal reference (e.g., "Proclamation No. 1395/2025, Article 11")
    source_url: str | None = None  # Link to the law
    effective_date: str | None = None  # When the rule became effective
    category: str = 'general'   # tax, pension, overtime, leave, severance, compliance
    verified: bool = False
    verified_at: str | None = None
    verified_by: str | None = None
    notes: str | None = None
    explanation: str = ''       # Plain-English explanation


# ─────────────────────────────────────────────
# Default rule sources — based on Ethiopian law
# ─────────────────────────────────────────────

RULE_SOURCES = {
    # ─── TAX ───
    'tax_brackets': RuleSource(
        rule_id='tax_brackets',
        name='Income Tax Brackets',
        name_am='የገቢ ግብር�ደን',
        source='Proclamation No. 1395/2025, Article 11',
        source_url='https://lawethiopia.com/images/proc1395-2025.pdf',
        effective_date='2025-09-01',
        category='tax',
        explanation='Monthly taxable income is taxed at progressive rates: 0% on first ETB 2,000, 15% on ETB 2,001-4,000, 20% on ETB 4,001-7,000, 25% on ETB 7,001-10,000, 30% on ETB 10,001-14,000, 35% above ETB 14,000.',
    ),
    'tax_no_personal_relief': RuleSource(
        rule_id='tax_no_personal_relief',
        name='No Personal Relief',
        name_am='የግል ማቃለል የለም',
        source='Proclamation No. 979/2016, Article 10(3); Proclamation No. 1395/2025',
        effective_date='2016-01-01',
        category='tax',
        explanation='Ethiopian income tax law does not allow personal relief deductions from employment income. Tax is calculated on the full taxable amount.',
    ),
    'tax_cash_limit': RuleSource(
        rule_id='tax_cash_limit',
        name='Cash Payment Limit',
        name_am='የጥሬ ገንዘብ ገደብ',
        source='Proclamation No. 1395/2025, Article 81',
        effective_date='2025-09-01',
        category='tax',
        explanation='Salaries above ETB 50,000 must be paid electronically (bank transfer or mobile wallet). Cash payment is not permitted above this threshold.',
    ),

    # ─── PENSION ───
    'pension_employee_rate': RuleSource(
        rule_id='pension_employee_rate',
        name='Employee Pension Rate',
        name_am='የሰራተኛ ጡረታ ተመን',
        source='Proclamation No. 1268/2022, Article 10',
        effective_date='2022-01-01',
        category='pension',
        explanation='Employee contributes 7% of basic salary to pension. No maximum ceiling.',
    ),
    'pension_employer_rate': RuleSource(
        rule_id='pension_employer_rate',
        name='Employer Pension Rate',
        name_am='የሰራተኛ አሰሪ ጡረታ ተመን',
        source='Proclamation No. 1268/2022, Article 10',
        effective_date='2022-01-01',
        category='pension',
        explanation='Employer contributes 11% of basic salary to pension. No maximum ceiling.',
    ),
    'pension_no_ceiling': RuleSource(
        rule_id='pension_no_ceiling',
        name='No Pension Ceiling',
        name_am='የጡረታ ገደብ የለም',
        source='Proclamation No. 1268/2022, Article 10',
        effective_date='2022-01-01',
        category='pension',
        explanation='There is no maximum insurable earnings ceiling for pension contributions in Ethiopia. Contributions are calculated on the full basic salary.',
    ),

    # ─── OVERTIME ───
    'overtime_day_rate': RuleSource(
        rule_id='overtime_day_rate',
        name='Day Overtime Rate',
        name_am='የቀን ተጨማሪ ሰዓት ተመን',
        source='Proclamation No. 1156/2019, Article 68(1)',
        effective_date='2019-01-01',
        category='overtime',
        explanation='Day overtime is paid at 1.5× the hourly rate. Hourly rate = basic salary ÷ 26 days ÷ 8 hours.',
    ),
    'overtime_night_rate': RuleSource(
        rule_id='overtime_night_rate',
        name='Night Overtime Rate',
        name_am='የምሽት ተጨማሪ ሰዓት ተመን',
        source='Proclamation No. 1156/2019, Article 68(2)',
        effective_date='2019-01-01',
        category='overtime',
        explanation='Night overtime (10 PM - 6 AM) is paid at 1.75× the hourly rate.',
    ),
    'overtime_holiday_rate': RuleSource(
        rule_id='overtime_holiday_rate',
        name='Holiday Overtime Rate',
        name_am='የበዓል ተጨማሪ ሰዓት ተመን',
        source='Proclamation No. 1156/2019, Article 68(3)',
        effective_date='2019-01-01',
        category='overtime',
        explanation='Holiday overtime is paid at 2.0× the hourly rate.',
    ),
    'overtime_rest_holiday_rate': RuleSource(
        rule_id='overtime_rest_holiday_rate',
        name='Rest Day + Holiday Overtime Rate',
        name_am='የእረፍት ቀን + በዓል ተጨማሪ ሰዓት ተመን',
        source='Proclamation No. 1156/2019, Article 68(4)',
        effective_date='2019-01-01',
        category='overtime',
        explanation='Rest day combined with holiday overtime is paid at 2.5× the hourly rate.',
    ),
    'overtime_hourly_rate_formula': RuleSource(
        rule_id='overtime_hourly_rate_formula',
        name='Hourly Rate Formula',
        name_am='የሰዓት ተመን ቀመር',
        source='Proclamation No. 1156/2019, Article 67(2)',
        effective_date='2019-01-01',
        category='overtime',
        explanation='Hourly rate = Monthly basic salary ÷ 26 working days ÷ 8 hours per day.',
    ),

    # ─── LEAVE ───
    'leave_annual': RuleSource(
        rule_id='leave_annual',
        name='Annual Leave',
        name_am='ዓመታዊ ፈቃድ',
        source='Proclamation No. 1156/2019, Article 77(1)(a)',
        effective_date='2019-01-01',
        category='leave',
        explanation='Employees are entitled to 16 working days of annual leave in the first year of employment.',
    ),
    'leave_annual_increase': RuleSource(
        rule_id='leave_annual_increase',
        name='Annual Leave Increase',
        name_am='የዓመታዊ ፈቃድ ጭማሪ',
        source='Proclamation No. 1156/2019, Article 77(1)(b)',
        effective_date='2019-01-01',
        category='leave',
        explanation='Annual leave increases by 1 day for every 2 additional years of service.',
    ),
    'leave_sick': RuleSource(
        rule_id='leave_sick',
        name='Sick Leave',
        name_am='የህመም ፈቃድ',
        source='Proclamation No. 1156/2019, Article 85(2)',
        effective_date='2019-01-01',
        category='leave',
        explanation='Employees are entitled to up to 180 days (6 months) of sick leave in a 12-month period.',
    ),
    'leave_sick_pay': RuleSource(
        rule_id='leave_sick_pay',
        name='Sick Pay',
        name_am='የህመም ክፍያ',
        source='Proclamation No. 1156/2019, Article 86',
        effective_date='2019-01-01',
        category='leave',
        explanation='Days 1-30: 100% salary. Days 31-90: 50% salary. Days 91-180: unpaid.',
    ),
    'leave_maternity': RuleSource(
        rule_id='leave_maternity',
        name='Maternity Leave',
        name_am='የወሊድ ፈቃድ',
        source='Proclamation No. 1156/2019, Article 88(3)',
        effective_date='2019-01-01',
        category='leave',
        explanation='Female employees are entitled to 120 days of maternity leave with full pay.',
    ),
    'leave_paternity': RuleSource(
        rule_id='leave_paternity',
        name='Paternity Leave',
        name_am='የአባት ፈቃድ',
        source='Proclamation No. 1156/2019, Article 81(2)',
        effective_date='2019-01-01',
        category='leave',
        explanation='Male employees are entitled to 3 days of paternity leave with full pay.',
    ),

    # ─── SEVERANCE ───
    'severance_year1': RuleSource(
        rule_id='severance_year1',
        name='Severance — Year 1',
        name_am='የስራ ማቋረጫ — የመጀመሪያ ዓመት',
        source='Proclamation No. 1156/2019, Article 40(1)',
        effective_date='2019-01-01',
        category='severance',
        explanation='For the first year of service: 30 days (1 month) of basic salary.',
    ),
    'severance_additional_years': RuleSource(
        rule_id='severance_additional_years',
        name='Severance — Additional Years',
        name_am='የስራ ማቋረጫ — ተጨማሪ ዓመታት',
        source='Proclamation No. 1156/2019, Article 40(2)',
        effective_date='2019-01-01',
        category='severance',
        explanation='For each additional year of service: 10 days of basic salary.',
    ),
    'severance_maximum': RuleSource(
        rule_id='severance_maximum',
        name='Severance Maximum',
        name_am='የስራ ማቋረጫ ከፍተኛ',
        source='Proclamation No. 1156/2019, Article 40',
        effective_date='2019-01-01',
        category='severance',
        explanation='Maximum severance is 12 months of basic salary.',
    ),
}


def get_rule_source(rule_id: str) -> RuleSource | None:
    """Get the source for a specific rule."""
    return RULE_SOURCES.get(rule_id)


def get_rules_by_category(category: str) -> list:
    """Get all rules for a specific category."""
    return [r for r in RULE_SOURCES.values() if r.category == category]


def get_all_sources() -> dict:
    """Get all rule sources."""
    return RULE_SOURCES


def get_explanation(rule_id: str) -> str:
    """Get the plain-English explanation for a rule."""
    source = RULE_SOURCES.get(rule_id)
    if source:
        return source.explanation
    return ''


def mark_verified(rule_id: str, verified_by: str) -> RuleSource | None:
    """Mark a rule as verified by an accountant."""
    source = RULE_SOURCES.get(rule_id)
    if source:
        source.verified = True
        source.verified_at = datetime.now(UTC).isoformat()
        source.verified_by = verified_by
    return source


def get_unverified_rules() -> list:
    """Get all rules that haven't been verified by an accountant."""
    return [r for r in RULE_SOURCES.values() if not r.verified]


def get_verification_summary() -> dict:
    """Get a summary of rule verification status."""
    total = len(RULE_SOURCES)
    verified = len([r for r in RULE_SOURCES.values() if r.verified])
    return {
        'total': total,
        'verified': verified,
        'unverified': total - verified,
        'percentage': round(verified / total * 100, 1) if total > 0 else 0,
    }
