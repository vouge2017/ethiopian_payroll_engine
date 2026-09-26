"""
Per-company pay-item catalog seed.

Defines the standard catalog (system items: company_id IS NULL) and the
company-template catalog (company_id-scoped copies seeded at company creation
and backfilled for existing companies via the migrate-pay-items CLI command.

System items are NEVER company-scoped — they are the shared definitions that
every company inherits. Company templates are per-company copies that an admin
can customise (rename, re-order, change rates) without affecting other companies.

Spec reference: Phase 2 section 2b (system catalog seed) and 2c (per-company
catalog seeding + flask migrate-pay-items CLI).
"""

from decimal import Decimal

from payroll_engine.constants import (
    ALLOWANCE_ITEM_KEYS,
    COMPANY_TEMPLATE_ITEM_KEYS,
    DEDUCTION_ITEM_KEYS,
    SYSTEM_ITEM_KEYS,
)
from payroll_engine.models import db, PayItemClassification, PayItemCalcMethod, PayItemTaxTreatment, PayItemType


Q = Decimal('0.01')

# ---------------------------------------------------------------------------
# System catalog (company_id IS NULL, is_system=True).
# These rows are shared across ALL companies and are NEVER company-scoped.
# ---------------------------------------------------------------------------

SYSTEM_ITEMS: list[dict] = [
    # Basic salary — the single mandatory earning every company starts with.
    # It's labelled as an "allowance" only in the legacy sense (it was an
    # allowance-type row before elements); here it is its own item type.
    {
        'key': SYSTEM_ITEM_KEYS.BASIC_SALARY.value,
        'name_en': 'Basic Salary',
        'name_am': 'ቀሜታ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 100,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        # FIXED items store their default amount in rate (paid per unit or flat);
        # basic salary is rate × 1 unit by default (units_field = 'working_days').
        'rate': Decimal('0'),          # placeholder; real amount set per-company
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        'regulation_reference': 'Labour Proclamation No. 1156/2019, Art. 8 & 32',
    },
    # Employee pension contribution (7% of basic) — a DEDUCTION from the
    # employee's pay, paid into the pension fund. Classification = deduction.
    # See lock-in 1 (employee_pension = deduction). Calculation: rate × basic.
    {
        'key': SYSTEM_ITEM_KEYS.EMPLOYEE_PENSION.value,
        'name_en': 'Employee Pension (7%)',
        'name_am': 'ኢትዮጵያ የህብረተሰብ መረጃ 7%',
        'classification': PayItemClassification.DEDUCTION,
        'calculation_method': PayItemCalcMethod.PERCENT_OF_BASIC,
        'sort_order': 300,
        'tax_treatment': PayItemTaxTreatment.EXEMPT,
        'rate': None,
        'percent_of_item_key': f'{SYSTEM_ITEM_KEYS.BASIC_SALARY.value}:0.07',
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        'regulation_reference': 'Pension Proclamation No. 745/2017',
    },
    # Employer pension contribution (11% of basic) — an EMPLOYER_CHARGE.
    # NOT a deduction from employee pay; recorded for employer cost tracking.
    # See lock-in 1 (employer_pension = employer_charge). rate = 0.11.
    {
        'key': SYSTEM_ITEM_KEYS.EMPLOYER_PENSION.value,
        'name_en': 'Employer Pension (11%)',
        'name_am': 'ፀጉሮች 11%',
        'classification': PayItemClassification.EMPLOYER_CHARGE,
        'calculation_method': PayItemCalcMethod.PERCENT_OF_BASIC,
        'sort_order': 350,
        'tax_treatment': PayItemTaxTreatment.EXEMPT,
        'rate': None,
        'percent_of_item_key': f'{SYSTEM_ITEM_KEYS.BASIC_SALARY.value}:0.11',
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        'regulation_reference': 'Pension Proclamation No. 745/2017',
    },
    # Income tax — computed by the existing tax module, recorded as a TAX item
    # for line-item reporting. amount is computed at payroll time (not stored
    # on the type). sort_order = 400 so it appears after earnings + deductions.
    {
        'key': SYSTEM_ITEM_KEYS.INCOME_TAX.value,
        'name_en': 'Income Tax',
        'name_am': 'የእጅሮ ስሚስ',
        'classification': PayItemClassification.TAX,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 400,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': None,
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        'regulation_reference': 'Income Tax Proclamation No. 1181/2020',
    },
]

# ---------------------------------------------------------------------------
# Company template catalog.
# These are the per-company items seeded at company creation and backfilled
# for existing companies via flask migrate-pay-items.
#
# Each item is a TEMPLATE — it defines the default configuration for that
# pay item type in a company. The company admin can then customise:
#   - name_en / name_am (rename in their language)
#   - rate (change the fixed amount, e.g. transport = 150 ETB/day)
#   - percent_of_item_key (override the default percent-of-basic, etc.)
#   - sort_order (reorder how items appear)
#   - effective_date / end_date (activate/deactivate)
#
# Company templates are is_system=False, company_id=<company_id>.
# ---------------------------------------------------------------------------

COMPANY_TEMPLATE_ITEMS: list[dict] = [
    # --- General Allowance ---
    #
    # The landing spot for the legacy single `allowances` number. The CSV
    # import format is `basic_salary, allowances` -- one undifferentiated
    # allowance column. Rather than force an itemised CSV (out of scope for
    # this phase), each imported employee gets ONE assignment against this item
    # so the legacy format keeps working under the elements model and can be
    # split into real items later.
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value,
        'name_en': 'General Allowance',
        'name_am': 'አጠቃላይ ክፍያ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 100,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        'regulation_reference': None,
        'max_percent_of_net': None,
    },
    # --- Allowances (standard set) ---
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.TRANSPORT.value,
        'name_en': 'Transport Allowance',
        'name_am': 'ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 150,
        # Regulatory rule lives HERE, not in the route: exempt up to the lower
        # of ETB 2,200 or 25% of basic. Was hardcoded in add_allowance as
        # `min(Decimal('2200'), emp.basic_salary * Decimal('0.25'))`.
        'tax_treatment': PayItemTaxTreatment.PARTIAL,
        'rate': Decimal('0'),     # placeholder; admin sets per-company
        'percent_of_item_key': None,
        'exempt_cap_amount': Decimal('2200'),
        'exempt_cap_percent': Decimal('25'),
        'exempt_cap_basis': 'basic_salary',
        'regulation_reference': 'Income Tax Proclamation - Transport Allowance Exemption',
        'max_percent_of_net': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.HARDSHIP.value,
        'name_en': 'Hardship Allowance',
        'name_am': 'ደረጃ ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 155,
        # Zone-based partial exemption. Was hardcoded as tax_treatment='partial'
        # in add_allowance.
        'tax_treatment': PayItemTaxTreatment.PARTIAL,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        'regulation_reference': 'Directive No. 21/2001, 102/2007',
        'max_percent_of_net': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.HOUSING.value,
        'name_en': 'Housing Allowance',
        'name_am': 'መኖር ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 160,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.COMMUNICATION.value,
        'name_en': 'Communication Allowance',
        'name_am': 'ኢንተርኔት/ፊዮን ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 165,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.PER_DIEM.value,
        'name_en': 'Per Diem',
        'name_am': 'የሰዓት ወጪ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 170,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.MEDICAL.value,
        'name_en': 'Medical Allowance',
        'name_am': 'ጤና ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 175,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.FOOD.value,
        'name_en': 'Food Allowance',
        'name_am': 'መገባት ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 180,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.EDUCATION.value,
        'name_en': 'Education Allowance',
        'name_am': 'ትምህርት ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 185,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.UNIFORM.value,
        'name_en': 'Uniform Allowance',
        'name_am': 'ተወው ልብስ ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 190,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.OTHER.value,
        'name_en': 'Other Allowance',
        'name_am': 'ሌላ ስያፍ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 195,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    # --- Deductions (standard set) ---
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.ADVANCE.value,
        'name_en': 'Salary Advance',
        'name_am': 'ቅድመ ክፍያ',
        'classification': PayItemClassification.DEDUCTION,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 500,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.LOAN.value,
        'name_en': 'Staff Loan',
        'name_am': 'ቤት መቀመጫ/የመሰብ ክፍያ',
        'classification': PayItemClassification.DEDUCTION,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 510,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.COST_SHARING.value,
        'name_en': 'Cost Sharing',
        'name_am': 'ካፒታል ክፍያ',
        'classification': PayItemClassification.DEDUCTION,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 520,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.COURT_ORDER.value,
        'name_en': 'Court Order Deduction',
        'name_am': 'ብረት መፍፍፍያ',
        'classification': PayItemClassification.DEDUCTION,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 530,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
        # Legal ceiling, read by the route instead of the old hardcoded
        # `deduction_type == 'court_order' and amount > 50` warning.
        'max_percent_of_net': Decimal('50'),
        'regulation_reference': 'Ethiopian labor law: garnishment capped at 1/3 of net, 1/2 for child support',
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.OTHER_DEDUCTION.value,
        'name_en': 'Other Deduction',
        'name_am': 'ሌላ ክፍያ',
        'classification': PayItemClassification.DEDUCTION,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 540,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        'rate': Decimal('0'),
        'percent_of_item_key': None,
        'exempt_cap_amount': None,
        'exempt_cap_percent': None,
        'exempt_cap_basis': None,
    },
]


def _norm(value):
    """Normalise a nullable numeric field to None or Decimal."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def seed_system_items() -> dict[str, int]:
    """Seed the system catalog (company_id IS NULL, is_system=True).

    Idempotent: skips items whose key already exists in the system catalog.
    Returns counts per action: {'created': N, 'skipped': M}.
    """
    created = 0
    skipped = 0

    for spec in SYSTEM_ITEMS:
        existing = PayItemType.query.filter_by(
            company_id=None,
            key=spec['key'],
        ).first()

        if existing:
            skipped += 1
            continue

        item = PayItemType(
            company_id=None,
            key=spec['key'],
            name_en=spec['name_en'],
            name_am=spec['name_am'],
            classification=spec['classification'],
            calculation_method=spec['calculation_method'],
            sort_order=spec['sort_order'],
            tax_treatment=spec['tax_treatment'],
            rate=_norm(spec.get('rate')),
            percent_of_item_key=spec.get('percent_of_item_key'),
            exempt_cap_amount=_norm(spec.get('exempt_cap_amount')),
            exempt_cap_percent=_norm(spec.get('exempt_cap_percent')),
            exempt_cap_basis=spec.get('exempt_cap_basis'),
            regulation_reference=spec.get('regulation_reference'),
            is_active=True,
            is_system=True,
        )
        db.session.add(item)
        created += 1

    db.session.commit()
    return {'created': created, 'skipped': skipped}


def seed_company_templates(company_id: int) -> dict[str, int]:
    """Seed the standard company template catalog for one company.

    Idempotent: skips items whose (company_id, key) already exists.
    Always skips if company_id is None (system items are seeded separately).
    Returns counts per action: {'created': N, 'skipped': M}.
    """
    if company_id is None:
        return {'created': 0, 'skipped': 0}

    created = 0
    skipped = 0

    for spec in COMPANY_TEMPLATE_ITEMS:
        existing = PayItemType.query.filter_by(
            company_id=company_id,
            key=spec['key'],
        ).first()

        if existing:
            skipped += 1
            continue

        item = PayItemType(
            company_id=company_id,
            key=spec['key'],
            name_en=spec['name_en'],
            name_am=spec['name_am'],
            classification=spec['classification'],
            calculation_method=spec['calculation_method'],
            sort_order=spec['sort_order'],
            tax_treatment=spec['tax_treatment'],
            rate=_norm(spec.get('rate')),
            percent_of_item_key=spec.get('percent_of_item_key'),
            exempt_cap_amount=_norm(spec.get('exempt_cap_amount')),
            exempt_cap_percent=_norm(spec.get('exempt_cap_percent')),
            exempt_cap_basis=spec.get('exempt_cap_basis'),
            max_percent_of_net=_norm(spec.get('max_percent_of_net')),
            regulation_reference=spec.get('regulation_reference'),
            is_active=True,
            is_system=False,
        )
        db.session.add(item)
        created += 1

    db.session.commit()
    return {'created': created, 'skipped': skipped}


def migrate_pay_items() -> dict[str, int]:
    """Backfill the company template catalog for ALL existing companies.

    Idempotent: only creates items that don't already exist for each company.
    Does NOT touch system catalog items (company_id IS NULL) — those are
    seeded separately by seed_system_items() and are shared across all companies.

    Returns aggregate counts: {'companies': N, 'items_created': M, 'items_skipped': K}.
    """
    from payroll_engine.models import Company

    companies = Company.query.all()
    total_created = 0
    total_skipped = 0

    for company in companies:
        result = seed_company_templates(company.id)
        total_created += result['created']
        total_skipped += result['skipped']

    return {
        'companies': len(companies),
        'items_created': total_created,
        'items_skipped': total_skipped,
    }
