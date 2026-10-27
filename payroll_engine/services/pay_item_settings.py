"""Company pay-item settings: list, add, rename, reorder, deactivate/reactivate, delete.

The rules live here so the routes stay thin and every rule is unit-testable:

* **System items are locked.** Rows with ``company_id IS NULL`` (basic salary,
  income tax, employee and employer pension) are the shared statutory catalog
  of every tenant. No settings action may change them; a company can only see
  them.
* **Keys are immutable.** A key is how the engine, imports and payslip
  snapshots refer to an item. Rename changes the labels (English, Amharic,
  Afaan Oromoo) only.
* **No legal attributes are edited here.** New custom items are always
  ``calculation_method='fixed'`` and ``tax_treatment='taxable'`` with no
  exemption caps (Ethiopian employment income is taxable unless a law exempts
  it), ``pensionable=False`` and ``counts_as_art53_wage=False``. The page
  shows every earning's tax treatment, cap and legal flags read-only
  (:func:`legal_view`); the flags are not read by any calculation yet and
  are pending legal confirmation, so they are not editable for any item.
* **Used items are never deleted.** An item referenced by any assignment
  (active, ended or soft-deleted) or by any payslip snapshot can only be
  deactivated. Only unused *custom* items can be deleted; the standard
  template items are re-seeded on demand, so they are deactivated instead.
* **Deactivation never silently stops pay.** The payroll engine skips
  assignments whose item is inactive, so an item with assignments that are
  still running cannot be deactivated until those assignments are ended.
  Items the app writes automatically during imports (general allowance,
  salary advance) cannot be deactivated at all.
* **Order is display order.** ``sort_order`` decides where an item is listed
  and printed. It does not change any amount: percent-of-net deductions use a
  fixed net-before-deductions base.

* **Changes are versioned, never overwritten (catalog PR 4b).** Renaming,
  deactivating and reactivating an item records the next
  ``PayItemTypeVersion`` (who, when, what changed, effective date) through
  ``item_versions.record_version``. A rename takes effect on the date the
  owner picks (today by default, never in the future, never before the
  current version's date); deactivation and reactivation take effect today.
  Unlocked periods before that date keep calculating with the earlier
  version; approved and locked runs keep their frozen snapshot.

Every successful change writes an audit-log row through ``create_audit_log``.
Callers commit.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from payroll_engine import db
from payroll_engine.constants import COMPANY_TEMPLATE_ITEM_KEYS, SYSTEM_ITEM_KEYS
from payroll_engine.exemption_caps import PENDING_LEGAL_CONFIRMATION_LABEL
from payroll_engine.item_versions import (
    SOURCE_CREATED,
    SOURCE_SETTINGS,
    current_version,
    diff_settings,
    record_version,
    settings_of,
)
from payroll_engine.models import Payslip
from payroll_engine.models_payroll_elements import (
    PayItemCalcMethod,
    PayItemClassification,
    PayItemTaxTreatment,
    PayItemType,
    PayrollItemAssignment,
)
from payroll_engine.shared import create_audit_log

KEY_PATTERN = re.compile(r'^[a-z][a-z0-9_]{1,29}$')
LABEL_MAX_LENGTH = 100

#: Kinds a company may create. Statutory kinds (tax, employer charge) are
#: system-only.
CUSTOM_KINDS = {
    'earning': PayItemClassification.EARNING,
    'deduction': PayItemClassification.DEDUCTION,
}

#: Display groups, in page order: (group id, i18n key).
GROUPS = (
    ('earnings', 'earnings'),
    ('allowances', 'allowances'),
    ('deductions', 'deductions'),
    ('employer_contributions', 'employer_contributions'),
    ('tax', 'tax'),
)

#: Company items the app itself writes assignments for during spreadsheet
#: imports (payroll_bp._annotate_general_allowance, set_advance_assignment).
#: Deactivating them would make those imports write assignments the engine
#: then ignores, so they stay active.
IMPORT_MANAGED_KEYS = frozenset(
    {COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value, COMPANY_TEMPLATE_ITEM_KEYS.ADVANCE.value}
)

#: Engine-owned keys that must never exist as company items.
ENGINE_KEYS = frozenset({'income_tax', 'employee_pension', 'employer_pension'})

TEMPLATE_KEYS = frozenset(k.value for k in COMPANY_TEMPLATE_ITEM_KEYS)
SYSTEM_KEYS = frozenset(k.value for k in SYSTEM_ITEM_KEYS)

#: Keys a custom item may not take: shared system keys (the engine prefers a
#: company row over the system row for some of them, so a company
#: 'basic_salary' would hijack the salary line), engine keys and the standard
#: template keys (re-seeded on demand).
RESERVED_KEYS = SYSTEM_KEYS | ENGINE_KEYS | TEMPLATE_KEYS


class PayItemSettingsError(ValueError):
    """A settings change was refused; the message is safe to show the user."""


@dataclass(frozen=True)
class Usage:
    active_assignments: int = 0
    total_assignments: int = 0

    @property
    def used(self):
        return self.total_assignments > 0


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def group_of(item):
    """Display group id for a PayItemType."""
    c = item.classification
    if c == PayItemClassification.EARNING:
        return 'earnings' if item.company_id is None else 'allowances'
    if c == PayItemClassification.DEDUCTION:
        return 'deductions'
    if c == PayItemClassification.EMPLOYER_CHARGE:
        return 'employer_contributions'
    return 'tax'


def get_company_item(company_id, item_id):
    """The company's own item with this id, or None (system and foreign ids included)."""
    return PayItemType.query.filter_by(id=item_id, company_id=company_id).first()


def get_visible_item(company_id, item_id):
    """The item if this company may see it (its own or a shared system item), else None."""
    return PayItemType.query.filter(
        PayItemType.id == item_id,
        db.or_(PayItemType.company_id == company_id, PayItemType.company_id.is_(None)),
    ).first()


def _active_assignment_condition(today):
    return db.and_(
        PayrollItemAssignment.is_active.is_(True),
        db.or_(PayrollItemAssignment.end_date.is_(None), PayrollItemAssignment.end_date >= today),
    )


def usage_by_item(company_id, item_ids=None, today=None):
    """{pay_item_type_id: Usage} for this company's assignments (one grouped query)."""
    today = today or date.today()
    q = db.session.query(
        PayrollItemAssignment.pay_item_type_id,
        func.count(PayrollItemAssignment.id),
        func.sum(case((_active_assignment_condition(today), 1), else_=0)),
    ).filter(PayrollItemAssignment.company_id == company_id)
    if item_ids is not None:
        q = q.filter(PayrollItemAssignment.pay_item_type_id.in_(list(item_ids)))
    rows = q.group_by(PayrollItemAssignment.pay_item_type_id).all()
    return {
        item_id: Usage(active_assignments=int(active or 0), total_assignments=int(total))
        for item_id, total, active in rows
    }


def item_in_payslips(company_id, item):
    """True when any payslip snapshot of this company has a line for this item."""
    rows = (
        db.session.query(Payslip.line_items)
        .filter(Payslip.company_id == company_id, Payslip.line_items.isnot(None))
        .yield_per(500)
    )
    for (line_items,) in rows:
        for line in line_items or ():
            if not isinstance(line, dict):
                continue
            if line.get('item_id') == item.id or line.get('item_key') == item.key:
                return True
    return False


def permissions(item, usage):
    """What the settings page may offer for this item, plus why things are locked."""
    if item.company_id is None:
        return {
            'locked': True,
            'can_rename': False,
            'can_move': False,
            'can_deactivate': False,
            'can_reactivate': False,
            'can_delete': False,
            'reason': 'Statutory system item, shared by every company. It cannot be changed here.',
        }
    reason = None
    can_deactivate = bool(item.is_active)
    if item.is_active and item.key in IMPORT_MANAGED_KEYS:
        can_deactivate = False
        reason = 'Used automatically by payroll imports, so it stays active.'
    elif item.is_active and usage.active_assignments:
        can_deactivate = False
        reason = f'{usage.active_assignments} employee assignment(s) still running. End them first.'
    can_delete = item.key not in TEMPLATE_KEYS and not usage.used and item.key not in IMPORT_MANAGED_KEYS
    return {
        'locked': False,
        'can_rename': True,
        'can_move': True,
        'can_deactivate': can_deactivate,
        'can_reactivate': not item.is_active,
        'can_delete': can_delete,
        'reason': reason,
    }


def _money_label(value):
    value = Decimal(value)
    return f'ETB {value:,.0f}' if value == value.to_integral_value() else f'ETB {value:,.2f}'


def _percent_label(value):
    value = Decimal(value).normalize()
    return f'{value:f}%'


def tax_label(item):
    """Plain-English tax treatment of an item, with its exemption cap as stored on the row.

    Describes what the payroll engine does with the row today; it is not a
    legal opinion. A partial item with no cap is fully exempt in the elements
    engine, and the label says so.
    """
    if item.classification != PayItemClassification.EARNING:
        return None
    tt = item.tax_treatment
    if tt == PayItemTaxTreatment.EXEMPT:
        return 'Tax-exempt'
    if tt != PayItemTaxTreatment.PARTIAL:
        return 'Taxable'
    caps = []
    if item.exempt_cap_amount is not None:
        caps.append(_money_label(item.exempt_cap_amount))
    if item.exempt_cap_percent is not None:
        caps.append(f'{_percent_label(item.exempt_cap_percent)} of basic salary')
    if not caps:
        return 'Partly exempt: no cap is set, so payroll treats the full amount as exempt'
    if len(caps) == 1:
        return f'Exempt up to {caps[0]}; the rest is taxable'
    return f'Exempt up to the lower of {caps[0]} or {caps[1]}; the rest is taxable'


def legal_view(item):
    """Read-only legal attributes for the settings page (None for non-earnings).

    The flags are informational in this release: pension is calculated on
    basic salary only and leave pay uses the company leave setting, whatever
    the flags say. They are shown, never editable, and marked pending legal
    confirmation (see exemption_caps / PLAN.md catalog PR 3).
    """
    if item.classification != PayItemClassification.EARNING:
        return None
    return {
        'tax': tax_label(item),
        'pensionable': bool(item.pensionable),
        'counts_as_art53_wage': bool(item.counts_as_art53_wage),
        'pending_note': PENDING_LEGAL_CONFIRMATION_LABEL,
    }


def catalog_view(company_id, today=None):
    """Grouped rows for the settings page: [(group id, i18n key, [(item, usage, perms)])]."""
    items = (
        PayItemType.query.filter(db.or_(PayItemType.company_id == company_id, PayItemType.company_id.is_(None)))
        .order_by(PayItemType.sort_order, PayItemType.id)
        .all()
    )
    usage = usage_by_item(company_id, today=today)
    grouped = {gid: [] for gid, _ in GROUPS}
    for item in items:
        u = usage.get(item.id, Usage())
        grouped[group_of(item)].append((item, u, permissions(item, u)))
    return [(gid, label, grouped[gid]) for gid, label in GROUPS]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def clean_labels(name_en, name_am=None, name_om=None):
    """Strip and validate the three labels. English is required."""
    out = {}
    for field, value, label, required in (
        ('name_en', name_en, 'English name', True),
        ('name_am', name_am, 'Amharic name', False),
        ('name_om', name_om, 'Afaan Oromoo name', False),
    ):
        value = (value or '').strip()
        if any(ord(ch) < 32 for ch in value):
            raise PayItemSettingsError(f'{label} contains invalid characters.')
        if required and not value:
            raise PayItemSettingsError(f'{label} is required.')
        if len(value) > LABEL_MAX_LENGTH:
            raise PayItemSettingsError(f'{label} must be {LABEL_MAX_LENGTH} characters or fewer.')
        out[field] = value or None
    return out


def clean_key(company_id, key):
    key = (key or '').strip().lower()
    if not KEY_PATTERN.match(key):
        raise PayItemSettingsError(
            'Code must be 2-30 characters: lowercase letters, digits and underscores, starting with a letter.'
        )
    if key in RESERVED_KEYS:
        raise PayItemSettingsError(f'"{key}" is reserved for a standard or statutory item. Choose another code.')
    if PayItemType.query.filter_by(company_id=company_id, key=key).first() is not None:
        raise PayItemSettingsError(f'Your company already has an item with code "{key}".')
    return key


def _require_company_item(item):
    if item is None or item.company_id is None:
        raise PayItemSettingsError('Statutory system items are locked and cannot be changed.')


def _labels(item):
    return {'name_en': item.name_en, 'name_am': item.name_am, 'name_om': item.name_om}


def earliest_effective_from(item):
    """The first date a new version of ``item`` may take effect (its current version's date)."""
    version = current_version(item)
    return version.effective_from if version is not None else None


def clean_effective_from(item, value, today=None):
    """Parse and check the effective date of a change. Empty means today."""
    today = today or date.today()
    if value in (None, ''):
        chosen = today
    elif isinstance(value, date):
        chosen = value
    else:
        try:
            chosen = date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise PayItemSettingsError('Effective date must be a date (YYYY-MM-DD).') from exc
    if chosen > today:
        raise PayItemSettingsError('Effective date cannot be in the future.')
    earliest = earliest_effective_from(item)
    if earliest is not None and chosen < earliest:
        raise PayItemSettingsError(
            f'Effective date cannot be before {earliest.isoformat()}, the date the current version took effect.'
        )
    return chosen


def _new_version(item, user_id, old_settings, effective_from):
    """Record the settings page's change of ``item`` as its next version."""
    changes = diff_settings(old_settings, settings_of(item))
    return record_version(item, effective_from=effective_from, source=SOURCE_SETTINGS, user_id=user_id, changes=changes)


# ---------------------------------------------------------------------------
# Changes (each writes one audit row; the caller commits)
# ---------------------------------------------------------------------------


def create_item(company_id, user_id, *, key, kind, name_en, name_am=None, name_om=None):
    if kind not in CUSTOM_KINDS:
        raise PayItemSettingsError('Choose whether the item is an allowance (earning) or a deduction.')
    classification = CUSTOM_KINDS[kind]
    key = clean_key(company_id, key)
    labels = clean_labels(name_en, name_am, name_om)

    top = (
        db.session.query(func.max(PayItemType.sort_order))
        .filter(PayItemType.company_id == company_id, PayItemType.classification == classification)
        .scalar()
    )
    default = 200 if classification == PayItemClassification.EARNING else 600
    item = PayItemType(
        company_id=company_id,
        key=key,
        classification=classification,
        calculation_method=PayItemCalcMethod.FIXED,
        tax_treatment=PayItemTaxTreatment.TAXABLE,
        # Custom items are never pensionable or Art. 53 wage until the engine
        # honours the flags and the legal reading is confirmed (catalog PR 4).
        pensionable=False,
        counts_as_art53_wage=False,
        sort_order=(top + 10) if top is not None else default,
        is_system=False,
        is_active=True,
        **labels,
    )
    record_version(item, effective_from=date.today(), source=SOURCE_CREATED, user_id=user_id)
    try:
        with db.session.begin_nested():
            db.session.add(item)
            db.session.flush()
    except IntegrityError as exc:  # lost a race with a concurrent create of the same key
        raise PayItemSettingsError(f'Your company already has an item with code "{key}".') from exc

    create_audit_log(
        company_id=company_id,
        user_id=user_id,
        action='pay_item_created',
        details={
            'pay_item_id': item.id,
            'key': key,
            'classification': classification,
            'calculation_method': item.calculation_method,
            'tax_treatment': item.tax_treatment,
            'pensionable': item.pensionable,
            'counts_as_art53_wage': item.counts_as_art53_wage,
            'sort_order': item.sort_order,
            **labels,
        },
    )
    return item


def rename_item(item, user_id, *, name_en, name_am=None, name_om=None, effective_from=None, today=None):
    """Change labels only, as a new version effective on ``effective_from``.

    Returns True if anything changed.
    """
    _require_company_item(item)
    new = clean_labels(name_en, name_am, name_om)
    old = _labels(item)
    if new == old:
        return False
    when = clean_effective_from(item, effective_from, today=today)
    before = settings_of(item)
    for field, value in new.items():
        setattr(item, field, value)
    version = _new_version(item, user_id, before, when)
    create_audit_log(
        company_id=item.company_id,
        user_id=user_id,
        action='pay_item_renamed',
        details={
            'pay_item_id': item.id,
            'key': item.key,
            'old': old,
            'new': new,
            'version_no': version.version_no,
            'effective_from': when.isoformat(),
        },
    )
    return True


def move_item(item, user_id, direction):
    """Move a company item one place up or down within its display group.

    The group's existing sort_order values are re-dealt to the new order (made
    strictly increasing if they had ties), so only that group's rows change and
    their position relative to other groups is kept. Returns True if moved.
    """
    _require_company_item(item)
    if direction not in ('up', 'down'):
        raise PayItemSettingsError('Unknown direction.')
    group = group_of(item)
    siblings = [
        s
        for s in PayItemType.query.filter(PayItemType.company_id == item.company_id)
        .order_by(PayItemType.sort_order, PayItemType.id)
        .all()
        if group_of(s) == group
    ]
    idx = next(i for i, s in enumerate(siblings) if s.id == item.id)
    target = idx - 1 if direction == 'up' else idx + 1
    if target < 0 or target >= len(siblings):
        return False

    values = [s.sort_order for s in siblings]
    reordered = list(siblings)
    reordered[idx], reordered[target] = reordered[target], reordered[idx]
    new_values = []
    for v in values:
        new_values.append(v if not new_values or v > new_values[-1] else new_values[-1] + 1)

    changes = {}
    for row, value in zip(reordered, new_values, strict=True):
        if row.sort_order != value:
            changes[row.key] = {'old': row.sort_order, 'new': value}
            row.sort_order = value
    create_audit_log(
        company_id=item.company_id,
        user_id=user_id,
        action='pay_item_reordered',
        details={'pay_item_id': item.id, 'key': item.key, 'direction': direction, 'changes': changes},
    )
    return True


def deactivate_item(item, user_id, today=None):
    _require_company_item(item)
    if not item.is_active:
        raise PayItemSettingsError('This item is already inactive.')
    usage = usage_by_item(item.company_id, [item.id], today=today).get(item.id, Usage())
    perms = permissions(item, usage)
    if not perms['can_deactivate']:
        raise PayItemSettingsError(perms['reason'] or 'This item cannot be deactivated.')
    when = today or date.today()
    when = max(when, earliest_effective_from(item) or when)
    before = settings_of(item)
    item.is_active = False
    version = _new_version(item, user_id, before, when)
    create_audit_log(
        company_id=item.company_id,
        user_id=user_id,
        action='pay_item_deactivated',
        details={
            'pay_item_id': item.id,
            'key': item.key,
            'assignments_kept': usage.total_assignments,
            'version_no': version.version_no,
            'effective_from': version.effective_from.isoformat(),
        },
    )


def reactivate_item(item, user_id, today=None):
    _require_company_item(item)
    if item.is_active:
        raise PayItemSettingsError('This item is already active.')
    when = today or date.today()
    when = max(when, earliest_effective_from(item) or when)
    before = settings_of(item)
    item.is_active = True
    version = _new_version(item, user_id, before, when)
    create_audit_log(
        company_id=item.company_id,
        user_id=user_id,
        action='pay_item_reactivated',
        details={
            'pay_item_id': item.id,
            'key': item.key,
            'version_no': version.version_no,
            'effective_from': version.effective_from.isoformat(),
        },
    )


def delete_item(item, user_id):
    """Hard-delete an unused custom item. Anything used is refused (deactivate instead)."""
    _require_company_item(item)
    if item.key in TEMPLATE_KEYS or item.key in IMPORT_MANAGED_KEYS:
        raise PayItemSettingsError('Standard items cannot be deleted. Deactivate it instead.')
    usage = usage_by_item(item.company_id, [item.id]).get(item.id, Usage())
    if usage.used:
        raise PayItemSettingsError(
            f'This item is used by {usage.total_assignments} employee assignment(s), so it is kept for history. '
            'Deactivate it instead.'
        )
    if item_in_payslips(item.company_id, item):
        raise PayItemSettingsError('This item appears on payslips, so it is kept for history. Deactivate it instead.')
    snapshot = {
        'pay_item_id': item.id,
        'key': item.key,
        'classification': item.classification,
        'sort_order': item.sort_order,
        'is_active': item.is_active,
        'versions': len(item.versions),
        **_labels(item),
    }
    company_id = item.company_id
    db.session.delete(item)
    db.session.flush()
    create_audit_log(company_id=company_id, user_id=user_id, action='pay_item_deleted', details=snapshot)
