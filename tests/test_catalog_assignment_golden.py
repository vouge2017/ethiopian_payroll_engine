"""Golden equivalence for catalog PR 5 (employee assignments) and PR 6 (overtime + deduction cap).

``tests/golden/catalog_assignment_golden.json`` was generated from
``origin/main`` @ ``b2847fa`` (before catalog PR 5) by running this file with
``GOLDEN_REGENERATE=1``. Every test recomputes the same scenarios with the
current code and requires identical results (money compared as
``str(Decimal)``).

Scenarios (all synthetic):
  * persisted company data in every state existing companies can be in today:
    no assignments + ``Employee.allowances``; legacy ``EmployeeAllowance``
    records; catalog assignments written the way the existing employee routes
    write them (allowances, fixed / percent-of-net / declining deductions,
    court order); legacy ``EmployeeDeduction`` rows; overtime entries;
    ended and future assignments. Computed through the worksheet review
    (``calculate_rows``) and the elements engine directly, for two months.
  * overtime: every overtime type x hours x basic salary through the elements
    engine, the legacy engine and ``overtime.calculate_total_overtime``, with
    the code defaults and with a TaxRule overtime override (the shape
    ``seed_tax_rules.py`` writes).
  * deductions above one third of the wage (fixed, percent of net, declining,
    court order): the amounts deducted today. Catalog PR 6 adds an approval
    check; it must never change these amounts.

Regenerate ONLY when an amount change is intended and reviewed.
"""

import hashlib
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from payroll_engine import create_app, db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeDeduction,
    OvertimeEntry,
    PayItemType,
    PayrollItemAssignment,
    TaxRule,
)

GOLDEN = Path(__file__).resolve().parent / 'golden' / 'catalog_assignment_golden.json'
REGENERATE = os.environ.get('GOLDEN_REGENERATE') == '1'
MONTHS = (date(2026, 9, 1), date(2026, 10, 1))

OT_TYPES = ('day', 'night', 'holiday', 'rest_day_holiday')
OT_HOURS = ('0.5', '1', '4', '7.25')
OT_BASICS = ('0.01', '2080', '5000', '10000', '33333.33', '100000')

#: The overtime override seed_tax_rules.py writes (day 1.25 / night 1.50).
TAX_RULE_OVERTIME = {
    'rates': {'day': 1.25, 'night': 1.50, 'holiday': 2.00, 'rest_day_holiday': 2.50},
    'max_hours_month': 20,
    'max_hours_year': 100,
    'monthly_hours': 208,
}


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        _invalidate()
        yield app
        _invalidate()
        db.session.remove()
        db.drop_all()


def _invalidate():
    from payroll_engine.overtime import invalidate_overtime_cache

    invalidate_overtime_cache()


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

_VOLATILE = {'effective_date', 'item_id', 'assignment_id', 'id', 'employee_pk', 'calculation_context'}


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0])) if k not in _VOLATILE}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(type(value).__name__)


_MONEY = (
    'gross',
    'taxable',
    'tax',
    'pension_employee',
    'pension_employer',
    'net',
    'net_before_deductions',
    'total_deductions',
    'exempt_allowances',
    'taxable_allowances',
    'overtime_pay',
    'sick_leave_reduction',
    'unpaid_leave_reduction',
)


def _digest(result):
    """Money fields verbatim (readable diff), line amounts, plus a hash of the whole payload."""
    plain = _plain(result)
    out = {k: plain[k] for k in _MONEY if k in plain}
    out['lines'] = sorted(
        f'{li.get("item_key")}={li.get("earned_amount")}'
        for li in plain.get('line_items') or []
        if isinstance(li, dict)
    )
    out['deductions'] = sorted(
        f'{d.get("type")}:{d.get("label")}={d.get("amount")}'
        for d in plain.get('deduction_details') or []
        if isinstance(d, dict)
    )
    out['sha256'] = hashlib.sha256(json.dumps(plain, sort_keys=True).encode()).hexdigest()
    return out


# ---------------------------------------------------------------------------
# Persisted company data (the states existing companies can be in)
# ---------------------------------------------------------------------------


def _company(name='Golden Assignments PLC'):
    co = Company(
        name=name,
        billing_status='active',
        plan_code='standard',
        paid_until=date(2027, 1, 1),
        leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0),
    )
    db.session.add(co)
    db.session.flush()
    seed_company_catalog(co.id, commit=False)
    db.session.commit()
    return co


def _emp(company, code, basic, allowances='0'):
    emp = Employee(
        company_id=company.id,
        employee_id=code,
        name=f'Golden {code}',
        phone='0912345670',
        basic_salary=Decimal(basic),
        allowances=Decimal(allowances),
        start_date=date(2024, 1, 1),
    )
    db.session.add(emp)
    db.session.flush()
    return emp


def _item(company, key):
    row = PayItemType.query.filter_by(company_id=company.id, key=key).first()
    return row or PayItemType.query.filter_by(company_id=None, key=key).one()


def _assign(company, emp, key, **values):
    """An assignment shaped exactly like the existing employee routes write it."""
    a = PayrollItemAssignment(
        company_id=company.id,
        employee_id=emp.id,
        pay_item_type_id=_item(company, key).id,
        is_active=values.pop('is_active', True),
        **values,
    )
    db.session.add(a)
    db.session.flush()
    return a


def _build_world():
    from payroll_engine.services.allowance_service import add_allowance_for_employee

    co = _company()
    # 1. No assignments, only the legacy Employee.allowances figure.
    _emp(co, 'G01', '8000', allowances='2000')
    # 2. Legacy EmployeeAllowance records (no catalog assignment).
    e2 = _emp(co, 'G02', '12000')
    for key, amount in (('transport', '3000'), ('hardship', '700'), ('housing', '1500')):
        rec = add_allowance_for_employee(e2, co.id, key, Decimal(amount))
        rec.employee = e2
        db.session.add(rec)
    # 3. Catalog earnings as add_allowance writes them (no basic assignment).
    e3 = _emp(co, 'G03', '15000')
    _assign(co, e3, 'transport', fixed_amount=Decimal('2500'))
    _assign(co, e3, 'housing', fixed_amount=Decimal('4000'))
    _assign(co, e3, 'per_diem', fixed_amount=Decimal('1200'))
    _assign(co, e3, 'medical', fixed_amount=Decimal('300'))
    # 4. Basic as an assignment + deductions as add_deduction writes them.
    e4 = _emp(co, 'G04', '9000')
    _assign(co, e4, 'basic_salary', fixed_amount=Decimal('9000'))
    _assign(co, e4, 'communication', fixed_amount=Decimal('500'))
    _assign(
        co,
        e4,
        'loan',
        fixed_amount=Decimal('1500'),
        custom_label='Staff loan',
        tracking_mode='declining',
        total_to_recover=Decimal('10000'),
        remaining_balance=Decimal('10000'),
        effective_date=date(2026, 1, 1),
    )
    _assign(
        co,
        e4,
        'court_order',
        percent_of_net=Decimal('20'),
        custom_label='Case 12/2026',
        tracking_mode='date_bounded',
        effective_date=date(2026, 1, 1),
    )
    # 5. Legacy EmployeeDeduction rows + an allowance assignment.
    e5 = _emp(co, 'G05', '6000')
    _assign(co, e5, 'general_allowance', fixed_amount=Decimal('1000'))
    db.session.add(
        EmployeeDeduction(
            company_id=co.id,
            employee_id=e5.id,
            deduction_type='cost_sharing',
            label='MoE batch 2024',
            amount=Decimal('10'),
            amount_mode='percentage',
            tracking_mode='date_bounded',
            start_date=date(2026, 1, 1),
            is_active=True,
        )
    )
    # 6. Ended, future and inactive assignments + overtime entries.
    e6 = _emp(co, 'G06', '20800')
    _assign(co, e6, 'transport', fixed_amount=Decimal('2200'), end_date=date(2026, 9, 15))
    _assign(co, e6, 'transport', fixed_amount=Decimal('2400'), effective_date=date(2026, 9, 16))
    _assign(co, e6, 'education', fixed_amount=Decimal('900'), effective_date=date(2026, 10, 10))
    _assign(co, e6, 'uniform', fixed_amount=Decimal('250'), is_active=False)
    for month in MONTHS:
        for day, hours, kind in (
            (3, '2', 'day'),
            (4, '3.5', 'night'),
            (6, '4', 'holiday'),
            (11, '1.25', 'rest_day_holiday'),
        ):
            db.session.add(
                OvertimeEntry(
                    company_id=co.id,
                    employee_id=e6.id,
                    date=month.replace(day=day),
                    hours=Decimal(hours),
                    overtime_type=kind,
                )
            )
    # 7. Deductions far above one third of the wage (cap scenario, PR 6).
    e7 = _emp(co, 'G07', '6000')
    _assign(co, e7, 'basic_salary', fixed_amount=Decimal('6000'))
    _assign(
        co,
        e7,
        'advance',
        fixed_amount=Decimal('2500'),
        custom_label='Salary advance',
        tracking_mode='date_bounded',
        effective_date=date(2026, 9, 1),
        end_date=date(2026, 10, 31),
    )
    _assign(co, e7, 'other_deduction', fixed_amount=Decimal('400'), custom_label='Canteen')
    _assign(co, e7, 'court_order', percent_of_net=Decimal('30'), custom_label='Case 7/2026')
    # 8. Percent-of-net deduction alone above a third.
    e8 = _emp(co, 'G08', '4000', allowances='0')
    _assign(co, e8, 'basic_salary', fixed_amount=Decimal('4000'))
    _assign(co, e8, 'cost_sharing', percent_of_net=Decimal('45'), custom_label='Cost sharing')
    db.session.commit()
    return co


def _world_cases():
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments
    from payroll_engine.services.worksheet_review import calculate_rows, month_end

    co = _build_world()
    out = {}
    for start in MONTHS:
        rows = calculate_rows(co.id, start)
        for row in rows:
            out[f'worksheet|{start:%Y-%m}|{row["id"]}'] = _digest(row)
        for emp in Employee.query.filter_by(company_id=co.id).order_by(Employee.employee_id).all():
            ot = [
                {'hours': e.hours, 'type': e.overtime_type}
                for e in OvertimeEntry.query.filter(
                    OvertimeEntry.company_id == co.id,
                    OvertimeEntry.employee_id == emp.id,
                    OvertimeEntry.date >= start,
                    OvertimeEntry.date <= month_end(start),
                ).all()
            ]
            result = calculate_payroll_from_assignments(
                emp, co.id, month_end(start), overtime_entries=ot or None, consume_balances=False
            )
            out[f'engine|{start:%Y-%m}|{emp.employee_id}'] = _digest(result)
    return out


# ---------------------------------------------------------------------------
# Overtime matrix
# ---------------------------------------------------------------------------


def _overtime_cases(tag):
    from payroll_engine.impact import _what_if_employee, virtual_assignment
    from payroll_engine.overtime import calculate_total_overtime
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    co = Company.query.first() or _company('Golden Overtime PLC')
    for_date = date(2026, 10, 31)
    out = {}
    for basic in OT_BASICS:
        for kind in OT_TYPES:
            for hours in OT_HOURS:
                entries = [{'hours': Decimal(hours), 'type': kind}]
                key = f'{tag}|b={basic}|{kind}|h={hours}'
                out[f'module|{key}'] = _plain(calculate_total_overtime(Decimal(basic), entries, for_date=for_date))
                emp = _what_if_employee(Decimal(basic), co.id)
                extras = [virtual_assignment(co.id, 'basic_salary', Decimal(basic), for_date=for_date)]
                out[f'elements|{key}'] = _digest(
                    calculate_payroll_from_assignments(
                        emp, co.id, for_date, extra_items=extras, overtime_entries=entries, consume_balances=False
                    )
                )
                out[f'legacy|{key}'] = _digest(
                    calculate_payroll(
                        basic_salary=Decimal(basic),
                        allowances=Decimal('0'),
                        overtime_entries=entries,
                        for_date=for_date,
                    )
                )
        # All four types in one month.
        entries = [{'hours': Decimal('2'), 'type': kind} for kind in OT_TYPES]
        out[f'module|{tag}|b={basic}|all'] = _plain(
            calculate_total_overtime(Decimal(basic), entries, for_date=for_date)
        )
    return out


def _with_tax_rule_override():
    db.session.add(
        TaxRule(
            version_name='golden-ot',
            effective_date=date(2025, 7, 8),
            country='ET',
            status='active',
            rules_json={'overtime': TAX_RULE_OVERTIME},
        )
    )
    db.session.commit()
    _invalidate()


def _apply_overtime_migration_if_present():
    """After catalog PR 6, existing TaxRule overtime config is copied into the catalog by
    the migration; tests replay the same ORM step. Before PR 6 there is nothing to do."""
    try:
        from payroll_engine.overtime_catalog import sync_overtime_items_from_tax_rules
    except ImportError:
        return
    sync_overtime_items_from_tax_rules()
    db.session.commit()
    _invalidate()


# ---------------------------------------------------------------------------
# Golden file plumbing
# ---------------------------------------------------------------------------


def _load():
    return json.loads(GOLDEN.read_text(encoding='utf-8'))


def _check(section, actual):
    if REGENERATE:
        data = _load() if GOLDEN.exists() else {}
        data[section] = actual
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
        pytest.skip(f'regenerated {section}')
    expected = _load()[section]
    assert set(actual) == set(expected), sorted(set(actual) ^ set(expected))[:10]
    diffs = [k for k in expected if expected[k] != actual[k]]
    assert not diffs, {k: (expected[k], actual[k]) for k in diffs[:3]}


def test_golden_persisted_company_data(app):
    _check('world', _world_cases())


def test_golden_overtime_defaults(app):
    _company('Golden Overtime PLC')
    _apply_overtime_migration_if_present()
    _check('overtime_defaults', _overtime_cases('defaults'))


def test_golden_overtime_tax_rule_override(app):
    _company('Golden Overtime PLC')
    _with_tax_rule_override()
    _apply_overtime_migration_if_present()
    _check('overtime_tax_rule', _overtime_cases('taxrule'))


def test_golden_world_with_tax_rule_override(app):
    _with_tax_rule_override()
    _apply_overtime_migration_if_present()
    _check('world_tax_rule', _world_cases())


def test_golden_file_is_reviewable():
    data = _load()
    assert {'world', 'overtime_defaults', 'overtime_tax_rule', 'world_tax_rule'} <= set(data)
    assert len(data['overtime_defaults']) == len(OT_BASICS) * (len(OT_TYPES) * len(OT_HOURS) * 3 + 1)
