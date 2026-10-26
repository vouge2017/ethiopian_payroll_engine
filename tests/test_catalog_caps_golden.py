"""Golden equivalence: centralising the exemption caps changed no amount (catalog PR 3).

``tests/golden/catalog_caps_golden.json`` was generated from ``origin/main`` @
``62682e6`` (before the caps moved into ``payroll_engine.exemption_caps``) by
running this file with ``GOLDEN_REGENERATE=1``. Every test below recomputes the
same matrix with the current code and requires byte-identical results (all
money compared as ``str(Decimal)``, so even a changed exponent fails).

Matrix:
  * elements engine (``calculate_payroll_from_assignments``): 13 basic
    salaries (0, 0.01, edge values around the 2,000 / 8,800 transport
    cross-over, rounding cases) x 7 transport amounts (0, below, at and above
    the ETB 2,200 cap) with hardship, per diem, medical and housing items, with
    and without overtime (day / night / rest day / holiday);
  * legacy engine (``calculate_payroll`` with ``EmployeeAllowance`` records
    built by ``allowance_service.add_allowance_for_employee``, including the
    unreviewed legacy per diem cap) for the same matrix;
  * ``calculate_transport_exempt_amount`` and the EmployeeAllowance /
    elements cap helpers directly;
  * what-if previews (new hire, allowance change), catalog and legacy paths;
  * final settlement (severance, notice pay, leave encashment) for several
    salaries and reasons.

Regenerate ONLY when an amount change is intended and reviewed; a diff in the
JSON is the reviewable record of that change.
"""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from payroll_engine import create_app, db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeAllowance,
    EmployeeDeduction,
    FinalSettlement,
    LeaveBalance,
    TenantQuery,
)

GOLDEN = Path(__file__).resolve().parent / 'golden' / 'catalog_caps_golden.json'
REGENERATE = os.environ.get('GOLDEN_REGENERATE') == '1'
FOR_DATE = date(2026, 10, 15)

BASICS = [
    '0',
    '0.01',
    '1000.01',
    '1999.99',
    '2000',
    '3333.33',
    '5000',
    '8799.99',
    '8800',
    '8800.01',
    '10000',
    '18000',
    '100000',
]
TRANSPORTS = ['0', '500', '2199.99', '2200', '2200.01', '3000', '25000']
OVERTIME = [
    {'hours': 10, 'type': 'day'},
    {'hours': 4, 'type': 'night'},
    {'hours': 3, 'type': 'rest_day_holiday'},
    {'hours': 2, 'type': 'holiday'},
]


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        for model in [Employee, EmployeeAllowance, EmployeeDeduction, LeaveBalance, FinalSettlement, AuditLog]:
            TenantQuery.register_model(model)
        company = Company(name='Golden Caps Co', leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0))
        db.session.add(company)
        db.session.flush()
        seed_company_catalog(company.id, commit=True)
        app.config['_golden_company_id'] = company.id
        yield app
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

#: Keys whose value depends on the run (today's date, row ids), not on the rules.
_VOLATILE = {'effective_date', 'item_id', 'assignment_id', 'id'}


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


def _digest(value):
    """Top-level scalars verbatim (readable diff) plus a SHA-256 of the whole payload.

    Line items, allowance details and the overtime breakdown are covered by the
    hash, so any change anywhere in the result still fails the comparison.
    """
    import hashlib

    plain = _plain(value)
    out = {k: v for k, v in plain.items() if not isinstance(v, (dict, list))}
    nested = {k: v for k, v in plain.items() if isinstance(v, dict)}
    for name, sub in nested.items():
        out.update({f'{name}.{k}': v for k, v in sub.items() if not isinstance(v, (dict, list))})
    out['sha256'] = hashlib.sha256(json.dumps(plain, sort_keys=True).encode()).hexdigest()
    return out


# ---------------------------------------------------------------------------
# Scenario builders (identical before and after the refactor)
# ---------------------------------------------------------------------------


def _elements_cases(company_id):
    from payroll_engine.impact import _what_if_employee, virtual_assignment
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    out = {}
    for basic in BASICS:
        for transport in TRANSPORTS:
            for with_ot in (False, True):
                emp = _what_if_employee(Decimal(basic), company_id)
                extras = [virtual_assignment(company_id, 'basic_salary', Decimal(basic), for_date=FOR_DATE)]
                if Decimal(transport) > 0:
                    extras.append(virtual_assignment(company_id, 'transport', Decimal(transport), for_date=FOR_DATE))
                for key, amount in (('hardship', '700'), ('per_diem', '1000'), ('medical', '400'), ('housing', '1500')):
                    extras.append(virtual_assignment(company_id, key, Decimal(amount), for_date=FOR_DATE))
                result = calculate_payroll_from_assignments(
                    emp,
                    company_id,
                    FOR_DATE,
                    extra_items=extras,
                    overtime_entries=OVERTIME if with_ot else None,
                    consume_balances=False,
                )
                out[f'b={basic}|t={transport}|ot={int(with_ot)}'] = _digest(result)
    return out


def _legacy_cases(company_id):
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.services.allowance_service import add_allowance_for_employee

    out = {}
    for basic in BASICS:
        for transport in TRANSPORTS:
            emp = Employee(employee_id='GOLD', name='Gold', basic_salary=Decimal(basic), allowances=Decimal('0'))
            records = []
            if Decimal(transport) > 0:
                records.append(add_allowance_for_employee(emp, company_id, 'transport', Decimal(transport)))
            records.append(add_allowance_for_employee(emp, company_id, 'per_diem', Decimal('9000')))
            records.append(add_allowance_for_employee(emp, company_id, 'per_diem', Decimal('150')))
            records.append(add_allowance_for_employee(emp, company_id, 'hardship', Decimal('700')))
            records.append(add_allowance_for_employee(emp, company_id, 'medical', Decimal('400')))
            records.append(add_allowance_for_employee(emp, company_id, 'housing', Decimal('1500')))
            for record in records:
                record.employee = emp
            caps = [
                {
                    'type': r.allowance_type,
                    'treatment': r.tax_treatment,
                    'cap_amount': r.exempt_cap_amount,
                    'cap_percent': r.exempt_cap_percent,
                    'exempt': r.calculated_exempt_amount,
                    'taxable': r.taxable_amount,
                    'reference': r.regulation_reference,
                }
                for r in records
            ]
            result = calculate_payroll(
                basic_salary=Decimal(basic),
                allowances=Decimal('0'),
                allowance_records=records,
                overtime_entries=OVERTIME,
                for_date=FOR_DATE,
            )
            out[f'b={basic}|t={transport}'] = {'records': _plain(caps), 'result': _digest(result)}
            # Never persist: these rows only exist to exercise the cap code.
            for record in records:
                if record in db.session:
                    db.session.expunge(record)
            if emp in db.session:
                db.session.expunge(emp)
    return out


def _direct_cases():
    from types import SimpleNamespace

    from payroll_engine.payroll_elements import _apply_exempt_cap
    from payroll_engine.services.allowance_service import calculate_transport_exempt_amount

    out = {}
    cap_shapes = {
        'both': (Decimal('2200'), Decimal('25')),
        'amount_only': (Decimal('2200'), None),
        'percent_only': (None, Decimal('25')),
        'none': (None, None),
    }
    for basic in BASICS:
        for transport in TRANSPORTS:
            b, t = Decimal(basic), Decimal(transport)
            row = {'transport_exempt': calculate_transport_exempt_amount(b, t)}
            for shape, (cap_amount, cap_percent) in cap_shapes.items():
                item = SimpleNamespace(exempt_cap_amount=cap_amount, exempt_cap_percent=cap_percent)
                row[f'engine_{shape}'] = _apply_exempt_cap(item, t, b)
                emp = Employee(employee_id='D', name='D', basic_salary=b)
                allowance = EmployeeAllowance(
                    allowance_type='transport',
                    amount=t,
                    tax_treatment=EmployeeAllowance.TAX_PARTIAL,
                    exempt_cap_amount=cap_amount,
                    exempt_cap_percent=cap_percent,
                    exempt_cap_basis='basic_salary',
                )
                allowance.employee = emp
                row[f'model_{shape}'] = allowance.calculated_exempt_amount
                if allowance in db.session:
                    db.session.expunge(allowance)
                if emp in db.session:
                    db.session.expunge(emp)
            out[f'b={basic}|t={transport}'] = _plain(row)
    return out


def _impact_cases(company_id):
    from payroll_engine.impact import preview_allowance_change, preview_new_hire

    out = {}
    for basic in ('2000', '5000', '8800', '10000', '18000'):
        for transport in ('0', '1000', '2200', '3000'):
            for cid in (None, company_id):
                tag = 'catalog' if cid else 'legacy'
                out[f'new_hire|{tag}|b={basic}|t={transport}'] = _digest(
                    preview_new_hire(Decimal(basic), Decimal('500'), Decimal(transport), company_id=cid)
                )
                out[f'allowance_change|{tag}|b={basic}|t={transport}'] = _digest(
                    preview_allowance_change(Decimal(transport), Decimal('2500'), Decimal(basic), company_id=cid)
                )
    return out


def _settlement_cases(company_id):
    from payroll_engine.services.settlement_service import calculate_settlement
    from payroll_engine.severance import TerminationReason

    out = {}
    end = date(2026, 7, 31)
    for i, (basic, allowances) in enumerate((('2000', '0'), ('8800', '1500'), ('10000', '0'), ('18000', '3000'))):
        emp = Employee(
            employee_id=f'SET-{i}',
            name=f'Settle {i}',
            basic_salary=Decimal(basic),
            allowances=Decimal(allowances),
            company_id=company_id,
            start_date=date(2021, 3, 15),
        )
        db.session.add(emp)
        db.session.flush()
        for reason in (TerminationReason.REDUNDANCY, TerminationReason.RESIGNATION):
            for days, notice in ((None, None), (Decimal('7.5'), Decimal('4000'))):
                r = calculate_settlement(
                    emp, reason, end, company_id, db.session, unused_leave_days=days, notice_pay=notice
                )
                out[f'b={basic}|a={allowances}|{reason}|d={days}|n={notice}'] = _plain(r)
    db.session.rollback()
    return out


SECTIONS = {
    'elements': _elements_cases,
    'legacy': _legacy_cases,
    'direct': lambda _cid: _direct_cases(),
    'impact': _impact_cases,
    'settlement': _settlement_cases,
}


def _compute(section, company_id):
    return SECTIONS[section](company_id)


def _load():
    with GOLDEN.open() as fh:
        return json.load(fh)


@pytest.mark.parametrize('section', list(SECTIONS))
def test_golden_amounts_unchanged(app, section):
    company_id = app.config['_golden_company_id']
    actual = _compute(section, company_id)
    if REGENERATE:
        data = _load() if GOLDEN.exists() else {}
        data[section] = actual
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(data, indent=0, sort_keys=True, ensure_ascii=False) + '\n')
        pytest.skip('golden file regenerated')
    expected = _load()[section]
    assert sorted(actual) == sorted(expected), 'scenario set changed'
    mismatched = [key for key in expected if actual[key] != expected[key]]
    assert not mismatched, f'{len(mismatched)} {section} scenario(s) changed, first: {mismatched[:3]}'


def test_golden_matrix_covers_cap_edges():
    """The matrix really straddles the transport cap and its cross-over salary."""
    assert {'2199.99', '2200', '2200.01'} <= set(TRANSPORTS)
    assert {'8799.99', '8800', '8800.01'} <= set(BASICS)  # 25 % of 8,800 = 2,200
    assert {'0', '0.01'} <= set(BASICS)
