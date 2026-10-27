"""Overtime types in the pay-item catalog (catalog PR 6).

The four overtime rates of Labour Proclamation 1156/2019 Art. 68, as the
codebase applies them, are shared system catalog items (``company_id IS
NULL``), one per overtime-entry type code:

    overtime_day              -> 'day'               (code default 1.50x)
    overtime_night            -> 'night'             (code default 1.75x)
    overtime_holiday          -> 'holiday'           (code default 2.00x)
    overtime_rest_day_holiday -> 'rest_day_holiday'  (code default 2.50x)

``PayItemType.rate`` holds the multiplier and is versioned with effective
dates like every other item setting (catalog PR 4b). ``overtime.
_get_overtime_rules`` reads the multiplier from the version effective on the
calculation date, so every engine (elements, legacy CSV, Excel, what-if)
uses the catalog. Hours, the 208-hour divisor and the hour limits are not
item settings and still come from ``TaxRule.rules_json['overtime']`` or the
code defaults.

Migration b5c6d7e8f9a0 creates the four items and copies the rates the app
was really applying into versions: the code defaults before the first
active TaxRule, then the rates of each active TaxRule from its effective
date (``TaxRule.get_active_rule`` semantics). So no unlocked period changes
amount. After the migration, TaxRule overtime *rates* are no longer read
while the catalog items exist (they are the fallback only when an item is
missing or inactive).

The items are calculated by the overtime module, never assigned to an
employee and never loaded as monthly earnings by the elements engine.

Labels keep the wording the app already shows for each type code (see
``overtime.get_overtime_type_label``). Note for review: the module docstring
of ``overtime.py`` maps 'holiday' (2.0x) to the weekly rest day and
'rest_day_holiday' (2.5x) to public holidays, while the UI labels call
'holiday' "Public Holiday". The rates are unchanged here; which label is
right is a question for the owner/adviser (PLAN.md).
"""

from datetime import date
from decimal import Decimal

#: Item key -> overtime entry type code (OvertimeEntry.overtime_type).
OVERTIME_TYPE_BY_KEY = {
    'overtime_day': 'day',
    'overtime_night': 'night',
    'overtime_holiday': 'holiday',
    'overtime_rest_day_holiday': 'rest_day_holiday',
}
KEY_BY_OVERTIME_TYPE = {v: k for k, v in OVERTIME_TYPE_BY_KEY.items()}
OVERTIME_KEYS = frozenset(OVERTIME_TYPE_BY_KEY)

#: First version date written by the migration (the rates before any TaxRule).
EPOCH = date(2000, 1, 1)

REGULATION = 'Labour Proclamation No. 1156/2019, Art. 68'

#: (name_en, name_am DRAFT, name_om DRAFT, sort_order) per type code.
#: Amharic / Afaan Oromoo are drafts pending native-speaker review.
LABELS = {
    'day': (
        'Overtime: regular day (6am-10pm)',
        'የትርፍ ሰዓት ክፍያ (መደበኛ ቀን)',
        "Kaffaltii Sa'aatii Dabalataa (guyyaa idilee)",
        510,
    ),
    'night': ('Overtime: night (10pm-6am)', 'የትርፍ ሰዓት ክፍያ (ሌሊት)', "Kaffaltii Sa'aatii Dabalataa (halkan)", 520),
    'holiday': ('Overtime: public holiday', 'የትርፍ ሰዓት ክፍያ (በዓል)', "Kaffaltii Sa'aatii Dabalataa (ayyaana)", 530),
    'rest_day_holiday': (
        'Overtime: rest day + holiday',
        'የትርፍ ሰዓት ክፍያ (የዕረፍት ቀንና በዓል)',
        "Kaffaltii Sa'aatii Dabalataa (guyyaa boqonnaa fi ayyaana)",
        540,
    ),
}


def default_rates():
    from payroll_engine.overtime import DEFAULT_OVERTIME_RATES

    return {code: Decimal(str(rate)) for code, rate in DEFAULT_OVERTIME_RATES.items()}


def specs():
    """System catalog specs (catalog.SYSTEM_ITEMS format) with the code-default rates."""
    from payroll_engine.models_payroll_elements import PayItemCalcMethod, PayItemClassification, PayItemTaxTreatment

    rates = default_rates()
    out = []
    for key, code in OVERTIME_TYPE_BY_KEY.items():
        name_en, name_am, _name_om, sort_order = LABELS[code]
        out.append(
            {
                'key': key,
                'name_en': name_en,
                'name_am': name_am,
                'classification': PayItemClassification.EARNING,
                'calculation_method': PayItemCalcMethod.RATE_X_UNITS,
                'sort_order': sort_order,
                'tax_treatment': PayItemTaxTreatment.TAXABLE,
                'rate': rates[code],
                'percent_of_item_key': None,
                'exempt_cap_amount': None,
                'exempt_cap_percent': None,
                'exempt_cap_basis': None,
                'regulation_reference': REGULATION,
            }
        )
    return out


def catalog_rates(for_date=None):
    """{type code: multiplier} from the system overtime items effective on ``for_date``.

    Only active items are returned; an empty dict means "no catalog items"
    (the caller falls back to TaxRule / code defaults).
    """
    from payroll_engine import db
    from payroll_engine.item_versions import resolve_rows
    from payroll_engine.models_payroll_elements import PayItemType

    d = for_date or date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    rows = (
        db.session.query(PayItemType)
        .filter(PayItemType.company_id.is_(None), PayItemType.key.in_(sorted(OVERTIME_KEYS)))
        .all()
    )
    out = {}
    for row in resolve_rows(rows, d):
        if row.is_active and row.rate is not None:
            out[OVERTIME_TYPE_BY_KEY[row.key]] = Decimal(str(row.rate))
    return out


# ---------------------------------------------------------------------------
# TaxRule history -> rate timeline (shared logic; migration b5c6d7e8f9a0 has
# a frozen copy that a test keeps equal)
# ---------------------------------------------------------------------------


def timeline_from_rules(rules):
    """[(effective_from, {code: rate})] from active TaxRule rows ``[(effective_date, rules_json)]``.

    Mirrors ``overtime._get_overtime_rules``: every date uses the code
    defaults overlaid with the rates of the latest active rule on or before
    it; dates before every rule use the code defaults.
    """
    defaults = default_rates()
    timeline = [(EPOCH, dict(defaults))]
    for effective_date, rules_json in sorted(rules, key=lambda r: r[0]):
        rates = dict(defaults)
        for code, value in ((rules_json or {}).get('overtime') or {}).get('rates', {}).items():
            if code in rates:
                rates[code] = Decimal(str(value))
        when = max(effective_date, EPOCH)
        if timeline and timeline[-1][0] == when:
            timeline[-1] = (when, rates)
        else:
            timeline.append((when, rates))
    return timeline


def code_timeline(timeline, code):
    """The timeline for one type code with consecutive equal rates merged."""
    out = []
    for when, rates in timeline:
        if out and out[-1][1] == rates[code]:
            continue
        out.append((when, rates[code]))
    return out


def active_tax_rules():
    from payroll_engine.models import TaxRule

    return [
        (r.effective_date, r.rules_json if isinstance(r.rules_json, dict) else {})
        for r in TaxRule.query.filter(TaxRule.status == 'active', TaxRule.country == 'ET')
        .order_by(TaxRule.effective_date)
        .all()
    ]


def sync_overtime_items_from_tax_rules():
    """ORM equivalent of migration b5c6d7e8f9a0's data step (used by tests and fresh setups).

    Creates the four system items if missing and appends versions so the rate
    effective on every date equals what ``overtime._get_overtime_rules``
    returned from TaxRule / code defaults before this change. Idempotent:
    items that already resolve to the TaxRule timeline get no new version.
    Caller commits.
    """
    from payroll_engine import db
    from payroll_engine.catalog import item_from_spec
    from payroll_engine.item_versions import SOURCE_MIGRATION, effective_version, record_version
    from payroll_engine.models_payroll_elements import PayItemType
    from payroll_engine.overtime import invalidate_overtime_cache

    timeline = timeline_from_rules(active_tax_rules())
    by_key = {
        row.key: row
        for row in PayItemType.query.filter(
            PayItemType.company_id.is_(None), PayItemType.key.in_(sorted(OVERTIME_KEYS))
        ).all()
    }
    for spec in specs():
        if spec['key'] not in by_key:
            row = item_from_spec(spec, None, is_system=True)
            db.session.add(row)
            db.session.flush()
            by_key[spec['key']] = row
    for key, row in by_key.items():
        wanted = code_timeline(timeline, OVERTIME_TYPE_BY_KEY[key])
        versions = list(row.versions)
        probe = sorted({w for w, _ in wanted} | {v.effective_from for v in versions})

        def wanted_on(d, wanted=wanted):
            rate = wanted[0][1]
            for when, value in wanted:
                if when <= d:
                    rate = value
            return rate

        if versions and all(Decimal(str(effective_version(versions, d).rate)) == wanted_on(d) for d in probe):
            continue
        latest_existing = max((v.effective_from for v in versions), default=EPOCH)
        for when, rate in wanted:
            row.rate = rate
            record_version(row, effective_from=when, source=SOURCE_MIGRATION, changes={'rate': {'new': str(rate)}})
        if latest_existing > wanted[-1][0]:
            row.rate = wanted[-1][1]
            record_version(
                row, effective_from=latest_existing, source=SOURCE_MIGRATION, changes={'rate': {'new': str(row.rate)}}
            )
    db.session.flush()
    invalidate_overtime_cache()
