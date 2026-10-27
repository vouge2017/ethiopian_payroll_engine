"""
Per-company pay-item catalog seed.

Defines the standard catalog (system items: company_id IS NULL) and the
company-template catalog (company_id-scoped copies seeded at company creation
by seed_company_catalog(), backfilled for existing companies by the
b7c1d2e3f4a5 data migration, and re-seeded on demand when a route finds a
company without its catalog). ``flask migrate-pay-items`` remains available
for the legacy-row data backfill.

System items are NEVER company-scoped — they are the shared definitions that
every company inherits. Company templates are per-company copies that an admin
can customise (rename, re-order, change rates) without affecting other companies.

Spec reference: Phase 2 section 2b (system catalog seed) and 2c (per-company
catalog seeding + flask migrate-pay-items CLI).
"""

from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from payroll_engine.constants import (
    COMPANY_TEMPLATE_ITEM_KEYS,
    SYSTEM_ITEM_KEYS,
)
from payroll_engine.exemption_caps import TRANSPORT as TRANSPORT_CAP
from payroll_engine.models import PayItemCalcMethod, PayItemClassification, PayItemTaxTreatment, PayItemType, db

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
        'name_am': 'መሠረታዊ ደመወዝ',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 100,
        'tax_treatment': PayItemTaxTreatment.TAXABLE,
        # FIXED items store their default amount in rate (paid per unit or flat);
        # basic salary is rate × 1 unit by default (units_field = 'working_days').
        'rate': Decimal('0'),  # placeholder; real amount set per-company
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
        'name_am': 'የሠራተኛ የጡረታ መዋጮ 7%',
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
        'name_am': 'የአሠሪ የጡረታ መዋጮ 11%',
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
        'name_am': 'የገቢ ግብር',
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


# Overtime rate items (catalog PR 6): one shared system item per overtime
# type code, rate = Art. 68 multiplier. Read by overtime._get_overtime_rules,
# never assigned and never loaded as a monthly earning.
def _overtime_specs():
    from payroll_engine.overtime_catalog import specs

    return specs()


SYSTEM_ITEMS.extend(_overtime_specs())

# ---------------------------------------------------------------------------
# Company template catalog.
# These are the per-company items seeded at company creation and backfilled
# for existing companies by the b7c1d2e3f4a5 data migration.
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
        'name_am': 'አጠቃላይ አበል',
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
        'name_am': 'የትራንስፖርት አበል',
        'classification': PayItemClassification.EARNING,
        'calculation_method': PayItemCalcMethod.FIXED,
        'sort_order': 150,
        # Exempt up to the lower of ETB 2,200 or 25% of basic. The numbers
        # live in exemption_caps.TRANSPORT (one source of truth); the seeded
        # row then carries them so the engine reads the company's own row.
        'tax_treatment': PayItemTaxTreatment.PARTIAL,
        'rate': Decimal('0'),  # placeholder; admin sets per-company
        'percent_of_item_key': None,
        'exempt_cap_amount': TRANSPORT_CAP.cap_amount,
        'exempt_cap_percent': TRANSPORT_CAP.cap_percent,
        'exempt_cap_basis': TRANSPORT_CAP.cap_basis,
        'regulation_reference': TRANSPORT_CAP.regulation_reference,
        'max_percent_of_net': None,
    },
    {
        'key': COMPANY_TEMPLATE_ITEM_KEYS.HARDSHIP.value,
        'name_en': 'Hardship Allowance',
        'name_am': 'የአስቸጋሪ ቦታ አበል',
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
        'name_am': 'የቤት አበል',
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
        'name_am': 'የኮሙኒኬሽን አበል',
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
        'name_am': 'የውሎ አበል',
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
        'name_am': 'የሕክምና አበል',
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
        'name_am': 'የምግብ አበል',
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
        'name_am': 'የትምህርት አበል',
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
        'name_am': 'የደንብ ልብስ አበል',
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
        'name_am': 'ሌላ አበል',
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
        'name_am': 'የሠራተኛ ብድር',
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
        'name_am': 'የወጪ መጋራት',
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
        'name_am': 'የፍርድ ቤት ትዕዛዝ ተቀናሽ',
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
        'name_am': 'ሌላ ተቀናሽ',
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


# ---------------------------------------------------------------------------
# Legal attributes (catalog PR 3). INFORMATIONAL: no calculation reads them.
# ---------------------------------------------------------------------------
#
# (pensionable, counts_as_art53_wage) per standard key. Every key not listed
# (deductions, tax, employer charges, company custom items) is (False, False).
#
# pensionable mirrors what the engines do today: pension is 7 % / 11 % of
# basic salary only (pension.py), which matches Directive 1087/2025 Art. 2(13)
# ("salary" excludes overtime and allowances).
#
# counts_as_art53_wage follows the text of Labour Proc. 1156/2019 Art. 53(2):
# transport, hardship and per diem are expressly excluded; the other
# allowances are not listed there, so they are marked True. Leave pay does NOT
# use this flag yet (it uses Company.leave_rate_basis); switching it on is
# catalog PR 4 and changes amounts, so it needs the adviser's answer first.
#
# All values are pending legal confirmation (PLAN.md, catalog PR 3). The same
# lists are frozen in migration d1e2f3a4b5c6; a test keeps them equal.
PENSIONABLE_KEYS = frozenset({SYSTEM_ITEM_KEYS.BASIC_SALARY.value})
ART53_WAGE_KEYS = frozenset(
    {
        SYSTEM_ITEM_KEYS.BASIC_SALARY.value,
        COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value,
        COMPANY_TEMPLATE_ITEM_KEYS.HOUSING.value,
        COMPANY_TEMPLATE_ITEM_KEYS.COMMUNICATION.value,
        COMPANY_TEMPLATE_ITEM_KEYS.MEDICAL.value,
        COMPANY_TEMPLATE_ITEM_KEYS.FOOD.value,
        COMPANY_TEMPLATE_ITEM_KEYS.EDUCATION.value,
        COMPANY_TEMPLATE_ITEM_KEYS.UNIFORM.value,
        COMPANY_TEMPLATE_ITEM_KEYS.OTHER.value,
    }
)
#: Excluded from Art. 53 wage by the text of Art. 53(2).
ART53_EXCLUDED_KEYS = frozenset(
    {
        COMPANY_TEMPLATE_ITEM_KEYS.TRANSPORT.value,
        COMPANY_TEMPLATE_ITEM_KEYS.HARDSHIP.value,
        COMPANY_TEMPLATE_ITEM_KEYS.PER_DIEM.value,
    }
)


def legal_attribute_defaults(key: str, classification: str) -> dict:
    """Seeded legal flags for an item. Only earnings can be pensionable or wage."""
    if classification != PayItemClassification.EARNING:
        return {'pensionable': False, 'counts_as_art53_wage': False}
    return {'pensionable': key in PENSIONABLE_KEYS, 'counts_as_art53_wage': key in ART53_WAGE_KEYS}


def _norm(value):
    """Normalise a nullable numeric field to None or Decimal."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def item_from_spec(spec: dict, company_id: int | None, *, is_system: bool) -> PayItemType:
    """Build an (unsaved) PayItemType from a catalog spec dict.

    The one place a catalog spec becomes a row, shared by the seeders below,
    the legacy backfill and any on-demand creation, so a template is never
    materialised two different ways.
    """
    return PayItemType(
        company_id=company_id,
        key=spec['key'],
        name_en=spec['name_en'],
        name_am=spec.get('name_am'),
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
        is_system=is_system,
        **legal_attribute_defaults(spec['key'], spec['classification']),
    )


def _existing_keys(company_id: int | None) -> set[str]:
    """Keys already present in ``company_id``'s catalog (None = system catalog)."""
    if company_id is None:
        scope = PayItemType.company_id.is_(None)
    else:
        scope = PayItemType.company_id == company_id
    return {k for (k,) in db.session.query(PayItemType.key).filter(scope).all()}


def _seed(company_id: int | None, specs: list[dict], *, is_system: bool, commit: bool) -> dict[str, int]:
    """Create the rows of ``specs`` that ``company_id`` lacks (None = system catalog).

    Idempotent: existing (company_id, key) rows are never touched, so a
    company's customisations survive re-seeding. Inserts run inside a
    SAVEPOINT; if a concurrent request seeded the same company first, the
    partial unique index rejects our insert, the savepoint rolls back and the
    call reports everything as skipped instead of failing the caller.
    """
    existing = _existing_keys(company_id)
    missing = [spec for spec in specs if spec['key'] not in existing]

    created = 0
    if missing:
        try:
            with db.session.begin_nested():
                for spec in missing:
                    db.session.add(item_from_spec(spec, company_id, is_system=is_system))
                db.session.flush()
            created = len(missing)
        except IntegrityError:
            # Lost a race with a concurrent seeder; the rows now exist.
            created = 0

    if commit:
        db.session.commit()
    return {'created': created, 'skipped': len(specs) - created}


def seed_system_items(commit: bool = True) -> dict[str, int]:
    """Seed the system catalog (company_id IS NULL, is_system=True).

    Idempotent: skips items whose key already exists in the system catalog.
    Returns counts per action: {'created': N, 'skipped': M}.
    """
    return _seed(None, SYSTEM_ITEMS, is_system=True, commit=commit)


def seed_company_templates(company_id: int, commit: bool = True) -> dict[str, int]:
    """Seed the standard company template catalog for one company.

    Idempotent: skips items whose (company_id, key) already exists.
    Always skips if company_id is None (system items are seeded separately).
    Returns counts per action: {'created': N, 'skipped': M}.
    """
    if company_id is None:
        return {'created': 0, 'skipped': 0}
    return _seed(company_id, COMPANY_TEMPLATE_ITEMS, is_system=False, commit=commit)


def seed_company_catalog(company_id: int, commit: bool = True) -> dict[str, int]:
    """Give one company its full catalog: the shared system items plus its templates.

    THE seeder every company-creation path calls (signup, Google signup,
    setup-company, demo, staging seed) and the on-demand fallback used when a
    route finds a company without its catalog. Idempotent and cheap when the
    catalog is already complete (two SELECTs, no writes).

    Pass ``commit=False`` inside a larger unit of work; rows are flushed so
    they are visible to the rest of the transaction.
    """
    system = seed_system_items(commit=False)
    templates = seed_company_templates(company_id, commit=False)
    if commit:
        db.session.commit()
    return {
        'system_created': system['created'],
        'created': templates['created'],
        'skipped': templates['skipped'],
    }


def migrate_pay_items() -> dict[str, int]:
    """Backfill the catalog for ALL existing companies (system items + templates).

    Idempotent: only creates items that don't already exist for each company.
    Existing rows, system or company, are never modified.

    Returns aggregate counts: {'companies': N, 'items_created': M, 'items_skipped': K}.
    """
    from payroll_engine.models import Company

    companies = Company.query.all()
    seed_system_items(commit=False)
    total_created = 0
    total_skipped = 0

    for company in companies:
        result = seed_company_templates(company.id, commit=False)
        total_created += result['created']
        total_skipped += result['skipped']

    db.session.commit()
    return {
        'companies': len(companies),
        'items_created': total_created,
        'items_skipped': total_skipped,
    }
