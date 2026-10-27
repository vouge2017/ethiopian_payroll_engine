"""Versioned pay-item settings with effective dates (catalog PR 4b).

Every PayItemType has one or more ``PayItemTypeVersion`` rows. The PayItemType
row always holds the settings of its newest version
(``PayItemType.current_version_no``); older versions keep what the settings
were before, each with the date it took effect (``effective_from``).

Writing versions
----------------
* A new item gets version 1 automatically when it is flushed (``before_flush``
  below), whatever created it (seeder, settings page, backfill, demo). The
  settings page records it explicitly so it carries the owner's user id.
* The settings page records a new version for every change of a versioned
  setting (``record_version``), effective on the date the owner chose.
* Any other code that changes a versioned setting on the ORM row gets a
  version too (``source='direct'``). It takes the effective date of the
  version it replaces, so it applies to every date that version covered:
  exactly what overwriting the row did before versions existed.
* Raw SQL that edits ``pay_item_type`` (a future data migration) must write
  its own version; otherwise the row simply differs from its newest version
  and the engine keeps using the row for the dates that version covers.

Reading versions
----------------
``resolve_item_types(items, for_date)`` returns, per item, the version that
was effective on ``for_date`` when that is NOT the current one. The payroll
engine wraps such items in ``ResolvedItemType`` / ``ResolvedAssignment``
(read-through views that override only the versioned settings). Items with a
single version, and dates covered by the current version, use the live row
unchanged, so nothing is calculated differently until an owner records a
dated change.

Effective version for a date: the latest ``(effective_from, version_no)``
with ``effective_from <= date``; for a date before every version, the newest
version among those with the earliest ``effective_from`` (version 1 unless a
direct change replaced it), i.e. the item as it was first known.

Approved and locked runs never resolve versions: their payslip amounts are
stored, and their item settings are frozen in ``PayrollRunItemSnapshot``
(catalog PR 4a), which records the settings resolved for the approval's
calculation date.
"""

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Session

#: Settings that are versioned. Key and classification are immutable, and
#: ``sort_order`` is display order only, so they are not versioned.
VERSIONED_FIELDS = (
    'name_en',
    'name_am',
    'name_om',
    'calculation_method',
    'percent_of_item_key',
    'rate',
    'tax_treatment',
    'exempt_cap_amount',
    'exempt_cap_percent',
    'exempt_cap_basis',
    'max_percent_of_net',
    'regulation_reference',
    'pensionable',
    'counts_as_art53_wage',
    'is_active',
)

#: Defaults for a pending row whose column default has not been applied yet.
_FIELD_DEFAULTS = {
    'calculation_method': 'fixed',
    'tax_treatment': 'taxable',
    'pensionable': False,
    'counts_as_art53_wage': False,
    'is_active': True,
}

SOURCE_MIGRATION = 'migration'
SOURCE_CREATED = 'created'
SOURCE_SETTINGS = 'settings'
SOURCE_DIRECT = 'direct'


def _plain(value):
    """JSON-safe, comparable form of a setting value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return str(value.normalize()) if value == value.to_integral_value() else str(value)
    if isinstance(value, float):
        return _plain(Decimal(str(value)))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value) if isinstance(value, str) else value


def _same(a, b):
    if isinstance(a, (Decimal, float, int)) and isinstance(b, (Decimal, float, int)) and not isinstance(a, bool):
        return Decimal(str(a)) == Decimal(str(b))
    return _plain(a) == _plain(b)


def settings_of(obj):
    """{field: value} of the versioned settings of a PayItemType or version row."""
    out = {}
    for field in VERSIONED_FIELDS:
        value = getattr(obj, field, None)
        if value is None and field in _FIELD_DEFAULTS:
            value = _FIELD_DEFAULTS[field]
        # PostgreSQL native enums can come back as str subclasses.
        if field in ('calculation_method', 'tax_treatment') and value is not None:
            value = str(value)
        out[field] = value
    return out


def diff_settings(old, new):
    """{field: {'old': .., 'new': ..}} for the versioned settings that differ."""
    return {
        field: {'old': _plain(old.get(field)), 'new': _plain(new.get(field))}
        for field in VERSIONED_FIELDS
        if not _same(old.get(field), new.get(field))
    }


def _today():
    return date.today()


def record_version(item, *, effective_from, source, user_id=None, changes=None):
    """Append the next version of ``item`` holding its current settings.

    ``item`` must already carry the new settings. Sets
    ``item.current_version_no``. The caller flushes / commits.
    """
    from payroll_engine.models_payroll_elements import PayItemTypeVersion

    # Loading the versions must not autoflush: that would flush the pending
    # setting change first and version it a second time as a direct change.
    session = sa.orm.object_session(item)
    if session is not None:
        with session.no_autoflush:
            existing = list(item.versions)
    else:
        existing = list(item.versions)
    number = max((v.version_no for v in existing), default=0) + 1
    version = PayItemTypeVersion(
        company_id=item.company_id,
        version_no=number,
        effective_from=effective_from,
        source=source,
        changed_by_user_id=user_id,
        changes=changes if number > 1 else None,
        **settings_of(item),
    )
    item.versions.append(version)
    item.current_version_no = number
    return version


def current_version(item):
    """The version row matching ``item.current_version_no`` (None if missing)."""
    session = sa.orm.object_session(item)
    if session is not None:
        with session.no_autoflush:
            versions = list(item.versions)
    else:
        versions = list(item.versions)
    for v in versions:
        if v.version_no == item.current_version_no:
            return v
    return None


def effective_version(versions, for_date):
    """The version effective on ``for_date`` (rules in the module docstring)."""
    ordered = sorted(versions, key=lambda v: (v.effective_from, v.version_no))
    if not ordered:
        return None
    chosen = None
    for v in ordered:
        if v.effective_from <= for_date:
            chosen = v
    if chosen is None:
        first = ordered[0].effective_from
        chosen = [v for v in ordered if v.effective_from == first][-1]
    return chosen


def _as_date(for_date):
    if isinstance(for_date, datetime):
        return for_date.date()
    if isinstance(for_date, date):
        return for_date
    if isinstance(for_date, str):
        return date.fromisoformat(for_date[:10])
    return _today()


def resolve_item_types(items, for_date):
    """{item id: PayItemTypeVersion} for items whose effective version is not the current one.

    Items with a single version are skipped without a query, so the common
    case costs nothing.
    """
    from payroll_engine import db
    from payroll_engine.models_payroll_elements import PayItemTypeVersion

    candidates = {}
    for item in items:
        if item is None or getattr(item, 'id', None) is None:
            continue
        if (getattr(item, 'current_version_no', None) or 1) > 1:
            candidates[item.id] = item
    if not candidates:
        return {}
    company_ids = {item.company_id for item in candidates.values()}
    company_filter = [PayItemTypeVersion.company_id == c for c in company_ids if c is not None]
    if None in company_ids:
        company_filter.append(PayItemTypeVersion.company_id.is_(None))
    rows = (
        db.session.query(PayItemTypeVersion)
        .filter(PayItemTypeVersion.pay_item_type_id.in_(list(candidates)), db.or_(*company_filter))
        .all()
    )
    by_item = {}
    for row in rows:
        by_item.setdefault(row.pay_item_type_id, []).append(row)
    d = _as_date(for_date)
    out = {}
    for item_id, versions in by_item.items():
        chosen = effective_version(versions, d)
        if chosen is not None and chosen.version_no != candidates[item_id].current_version_no:
            out[item_id] = chosen
    return out


class ResolvedItemType:
    """Read-through view of a PayItemType with an older version's settings.

    Only the versioned settings come from the version; everything else
    (id, key, classification, sort order, company) is the live row's.
    Never added to a session.
    """

    __slots__ = ('_row', '_settings', 'effective_from', 'version_no')

    def __init__(self, row, version):
        object.__setattr__(self, '_row', row)
        object.__setattr__(self, '_settings', settings_of(version))
        object.__setattr__(self, 'version_no', version.version_no)
        object.__setattr__(self, 'effective_from', version.effective_from)

    def __getattr__(self, name):
        settings = object.__getattribute__(self, '_settings')
        if name in settings:
            return settings[name]
        return getattr(object.__getattribute__(self, '_row'), name)

    def __setattr__(self, name, value):
        raise AttributeError('A resolved pay-item version is read-only.')

    @property
    def row(self):
        return self._row

    @property
    def is_system_item(self):
        return self.is_system or self.company_id is None

    def label(self, language='en'):
        if language == 'am' and self.name_am:
            return self.name_am
        if language == 'om' and self.name_om:
            return self.name_om
        return self.name_en

    def __repr__(self):
        return f'<ResolvedItemType {self._row.key} v{self.version_no}>'


class ResolvedAssignment:
    """Read-through view of a PayrollItemAssignment whose item resolves to an older version.

    ``item_type`` is the ResolvedItemType; every other attribute (and every
    write, e.g. a declining balance) goes to the real assignment.
    """

    __slots__ = ('_assignment', '_item_type')

    def __init__(self, assignment, item_type):
        object.__setattr__(self, '_assignment', assignment)
        object.__setattr__(self, '_item_type', item_type)

    @property
    def item_type(self):
        return self._item_type

    @property
    def assignment(self):
        return self._assignment

    @property
    def label(self):
        if self._assignment.custom_label:
            return self._assignment.custom_label
        if self._item_type.name_en:
            return self._item_type.name_en
        return self._item_type.key

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_assignment'), name)

    def __setattr__(self, name, value):
        setattr(self._assignment, name, value)

    def __repr__(self):
        return f'<ResolvedAssignment {self._assignment!r} v{self._item_type.version_no}>'


def unwrap(obj):
    """The ORM object behind a resolved view (or the object itself)."""
    if isinstance(obj, ResolvedAssignment):
        return obj.assignment
    if isinstance(obj, ResolvedItemType):
        return obj.row
    return obj


def resolve_rows(item_types, for_date):
    """[row or ResolvedItemType] for PayItemType rows, in the same order."""
    versions = resolve_item_types(item_types, for_date)
    return [ResolvedItemType(row, versions[row.id]) if row.id in versions else row for row in item_types]


def resolve_assignments(assignments, for_date):
    """[assignment or ResolvedAssignment], in the same order."""
    types = {a.item_type.id: a.item_type for a in assignments if getattr(a, 'item_type', None) is not None}
    versions = resolve_item_types(list(types.values()), for_date)
    if not versions:
        return list(assignments)
    out = []
    views = {}
    for a in assignments:
        it = getattr(a, 'item_type', None)
        if it is not None and it.id in versions:
            view = views.get(it.id)
            if view is None:
                view = views[it.id] = ResolvedItemType(it, versions[it.id])
            out.append(ResolvedAssignment(a, view))
        else:
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# History (settings page)
# ---------------------------------------------------------------------------

FIELD_LABELS = {
    'name_en': 'English name',
    'name_am': 'Amharic name',
    'name_om': 'Afaan Oromoo name',
    'calculation_method': 'Calculation method',
    'percent_of_item_key': 'Percent of item',
    'rate': 'Rate',
    'tax_treatment': 'Tax treatment',
    'exempt_cap_amount': 'Exemption cap (ETB)',
    'exempt_cap_percent': 'Exemption cap (% of basic)',
    'exempt_cap_basis': 'Exemption cap basis',
    'max_percent_of_net': 'Maximum % of net',
    'regulation_reference': 'Regulation reference',
    'pensionable': 'Pensionable',
    'counts_as_art53_wage': 'Art. 53 wage',
    'is_active': 'Active',
}

SOURCE_LABELS = {
    SOURCE_MIGRATION: 'Recorded when versioning was introduced',
    SOURCE_CREATED: 'Created',
    SOURCE_SETTINGS: 'Changed on this settings page',
    SOURCE_DIRECT: 'Changed outside the settings page',
}


def history(item):
    """Newest-first version rows for the history page: list of dicts."""
    from payroll_engine.models import User

    versions = sorted(item.versions, key=lambda v: v.version_no, reverse=True)
    user_ids = {v.changed_by_user_id for v in versions if v.changed_by_user_id}
    users = {}
    if user_ids:
        for u in User.query.filter(User.id.in_(user_ids)).all():
            name = ' '.join(p for p in (u.first_name, u.last_name) if p)
            users[u.id] = name or u.email or u.phone or f'User {u.id}'
    out = []
    for v in versions:
        changes = []
        for field, delta in (v.changes or {}).items():
            changes.append(
                {
                    'field': field,
                    'label': FIELD_LABELS.get(field, field),
                    'old': delta.get('old'),
                    'new': delta.get('new'),
                }
            )
        out.append(
            {
                'version_no': v.version_no,
                'effective_from': v.effective_from,
                'created_at': v.created_at,
                'source': v.source,
                'source_label': SOURCE_LABELS.get(v.source, v.source),
                'changed_by': users.get(v.changed_by_user_id),
                'changes': changes,
                'is_current': v.version_no == item.current_version_no,
                'is_active': v.is_active,
                'name_en': v.name_en,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Automatic versions (any ORM writer)
# ---------------------------------------------------------------------------


def _versioned_attrs_touched(item):
    state = sa.inspect(item)
    return any(state.attrs[field].history.has_changes() for field in VERSIONED_FIELDS)


@sa.event.listens_for(Session, 'before_flush')
def _version_pay_items(session, flush_context, instances):
    from payroll_engine.models_payroll_elements import PayItemType

    for obj in list(session.new):
        if isinstance(obj, PayItemType) and not obj.versions:
            record_version(
                obj,
                effective_from=obj.effective_date or _today(),
                source=SOURCE_CREATED,
            )
    for obj in list(session.dirty):
        if not isinstance(obj, PayItemType) or obj in session.deleted:
            continue
        state = sa.inspect(obj)
        if state.attrs['current_version_no'].history.has_changes():
            continue  # the settings page recorded this change itself
        if not _versioned_attrs_touched(obj):
            continue
        previous = current_version(obj)
        if previous is not None:
            changes = diff_settings(settings_of(previous), settings_of(obj))
            if not changes:
                continue
        else:
            changes = None
        record_version(
            obj,
            effective_from=previous.effective_from if previous is not None else _today(),
            source=SOURCE_DIRECT,
            changes=changes,
        )
