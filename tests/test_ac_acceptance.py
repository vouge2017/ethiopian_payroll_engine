"""AC1-AC11: the Phase 2 acceptance criteria, executed as written.

Each test is named for its AC and asserts the criterion's own numbers. Nothing
here is inferred or softened: where the engine cannot do what a criterion
asks, the test says so rather than faking it.
"""
from datetime import date
from decimal import Decimal

import pytest
from payroll_engine import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        from payroll_engine.catalog import seed_system_items

        seed_system_items()
        yield app
        db.session.remove()


@pytest.fixture
def ctx(app):
    with app.app_context():
        db.session.rollback()
        yield
        db.session.rollback()
        db.session.remove()


def _company(name):
    from payroll_engine.catalog import seed_company_templates
    from payroll_engine.models import Company, User

    co = Company(name=name)
    db.session.add(co)
    db.session.commit()
    seed_company_templates(co.id)
    db.session.commit()
    u = User(phone=f'0912000{co.id:04d}', company_id=co.id, role='owner')
    u.set_password('Test1234!')
    db.session.add(u)
    db.session.commit()
    return co, u


def _employee(co, eid='EMP001', basic=Decimal('10000'), start=date(2020, 1, 1)):
    from payroll_engine.models import Employee

    e = Employee(employee_id=eid, name=f'Person {eid}', basic_salary=basic,
                 allowances=Decimal('0'), company_id=co.id, start_date=start)
    db.session.add(e)
    db.session.commit()
    return e


def _item(co, key, name_en, classification, method, tax_treatment, **kw):
    from payroll_engine.models import PayItemType

    it = PayItemType(
        company_id=co.id, key=key, name_en=name_en, classification=classification,
        calculation_method=method, tax_treatment=tax_treatment, is_system=False, **kw
    )
    db.session.add(it)
    db.session.flush()
    return it


def _assign(co, emp, item, **kw):
    from payroll_engine.models import PayrollItemAssignment

    a = PayrollItemAssignment(
        company_id=co.id, employee_id=emp.id, pay_item_type_id=item.id,
        is_active=True, **kw
    )
    db.session.add(a)
    db.session.flush()
    return a


def _basic_assignment(co, emp, amount=None):
    """The engine assembles gross FROM assignments, so every AC fixture needs
    the employee's basic salary represented as one."""
    from payroll_engine.models import PayItemType

    it = PayItemType.query.filter_by(company_id=None, key='basic_salary').first()
    return _assign(co, emp, it,
                    fixed_amount=amount if amount is not None else emp.basic_salary)


def _calc(emp, co, for_date=date(2026, 9, 1), **kw):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    return calculate_payroll_from_assignments(emp, co.id, for_date, **kw)


# =====================================================================
# AC1 -- per-company pay item type isolation
# =====================================================================


def test_ac1_company_b_cannot_see_company_a_type(ctx):
    from payroll_engine.models import PayItemType

    a, _ = _company('CoA')
    b, _ = _company('CoB')

    before_b = PayItemType.query.filter_by(company_id=b.id).count()

    _item(a, 'night_shift', 'Night Shift Allowance', 'earning',
          'rate_x_units', 'taxable')

    assert PayItemType.query.filter_by(company_id=b.id, key='night_shift').first() is None, (
        'Company B must not see Company A\'s night_shift type'
    )
    # Company A's own catalog gained exactly one row.
    assert PayItemType.query.filter_by(company_id=a.id, key='night_shift').count() == 1
    # Company B's catalog is unchanged.
    assert PayItemType.query.filter_by(company_id=b.id).count() == before_b


# =====================================================================
# AC2 -- new allowance type with no code change or redeploy
# =====================================================================


def test_ac2_new_type_purely_through_data(ctx):
    from payroll_engine.models import PayItemType

    a, _ = _company('CoA')
    emp = _employee(a)

    # Created as DATA, exactly as an admin would through the API/UI.
    _item(a, 'night_shift', 'Night Shift Allowance', 'earning',
          'rate_x_units', 'taxable', rate=Decimal('150'))
    db.session.commit()

    it = PayItemType.query.filter_by(company_id=a.id, key='night_shift').first()
    _basic_assignment(a, emp)
    _assign(a, emp, it, rate_per_unit=Decimal('150'), units_field='night_units')

    r = _calc(emp, a, units_input={'night_units': 16})

    night = [li for li in r['line_items'] if li['item_key'] == 'night_shift']
    assert len(night) == 1, 'night_shift must appear on the payslip'
    assert night[0]['earned_amount'] == Decimal('2400'), '150 x 16 = 2400'
    assert night[0]['item_label'] == 'Night Shift Allowance', (
        'the payslip must carry the catalog label'
    )
    assert Decimal(str(r['gross'])) == Decimal('12400'), 'gross = 10000 + 2400'


# =====================================================================
# AC3 / AC4 -- accumulation engine vs hand calculation
# =====================================================================


def _ac3_fixture(ctx):
    a, _ = _company('Ac3Co')
    emp = _employee(a, basic=Decimal('10000'))
    _basic_assignment(a, emp)

    t = _item(a, 'transport', 'Transport Allowance', 'earning', 'fixed',
              'partial', exempt_cap_amount=Decimal('600'))
    n = _item(a, 'night_shift', 'Night Shift Allowance', 'earning',
              'rate_x_units', 'taxable')
    h = _item(a, 'housing', 'Housing Allowance', 'earning',
              'percent_of_basic', 'taxable')

    _assign(a, emp, t, fixed_amount=Decimal('2000'))
    _assign(a, emp, n, rate_per_unit=Decimal('150'), units_field='night_units')
    _assign(a, emp, h, percent_of_basic=Decimal('30'))
    db.session.commit()
    return a, emp, t, n, h


def test_ac3_accumulation_matches_hand_calculation(ctx):
    from payroll_engine.tax import calculate_tax

    a, emp, *_ = _ac3_fixture(ctx)
    r = _calc(emp, a, units_input={'night_units': 16})

    # The spec's arithmetic, verbatim.
    assert r['gross'] == Decimal('17400'), '10000 + 2000 + 2400 + 3000'
    assert r['exempt_allowances'] == Decimal('600')
    assert r['pension_employee'] == Decimal('700'), '7% of 10000'
    assert r['taxable'] == Decimal('16100'), '17400 - 700 - 600'
    assert r['tax'] == calculate_tax(Decimal('16100')) == Decimal('3585')
    assert r['net'] == Decimal('13115'), '17400 - 700 - 3585'


def test_ac4_tax_treatment_per_item(ctx):
    """Exempt 600 on transport only; every other bir fully taxable."""
    a, emp, *_ = _ac3_fixture(ctx)
    r = _calc(emp, a, units_input={'night_units': 16})

    details = {li['item_key']: li for li in r['line_items']}
    assert details['transport']['earned_amount'] == Decimal('2000')
    assert details['night_shift']['earned_amount'] == Decimal('2400')
    assert details['housing']['earned_amount'] == Decimal('3000')

    # taxable earnings = 10000 + (2000-600) + 2400 + 3000 = 16800
    assert r['taxable'] == Decimal('16100'), (
        'taxable earnings 16800 minus pension 700'
    )
    assert r['pension_employee'] == Decimal('700')


# =====================================================================
# AC5 -- system items are not user-assignable
# =====================================================================


def test_ac5_system_items_rejected_but_still_calculated(ctx):
    from payroll_engine.models import PayItemType
    from payroll_engine.models_payroll_elements import PayrollItemAssignment
    from payroll_engine.payroll_elements import AC5Error, assert_not_system_item

    a, _ = _company('Ac5Co')
    emp = _employee(a)
    _basic_assignment(a, emp)

    for key in ('employee_pension', 'income_tax'):
        sysitem = PayItemType.query.filter_by(company_id=None, key=key).first()
        assert sysitem is not None, f'{key} must exist as a system item'
        assert sysitem.is_system is True
        with pytest.raises(AC5Error):
            assert_not_system_item(sysitem)

    # The ENGINE must refuse to evaluate a hand-built assignment to a system
    # item, not merely the route layer.
    pension_item = PayItemType.query.filter_by(
        company_id=None, key='employee_pension'
    ).first()
    probe = PayrollItemAssignment(
        company_id=a.id, employee_id=emp.id,
        pay_item_type_id=pension_item.id, fixed_amount=Decimal('999'),
        is_active=True,
    )
    db.session.add(probe)
    db.session.commit()
    assert probe.id is not None, 'the AC5 probe row must actually be persisted'

    with pytest.raises(AC5Error):
        _calc(emp, a)

    # Remove ONLY the illegal probe row (a blanket delete would also drop the
    # basic_salary assignment and leave gross at 0).
    db.session.delete(probe)
    db.session.commit()

    r = _calc(emp, a)
    assert 'employee_pension' in {li['item_key'] for li in r['line_items']}, (
        'employee_pension must be in line_items'
    )
    assert r['pension_employee'] == Decimal('700')
    assert r['tax'] > 0


# =====================================================================
# AC6 -- effective dates gate assignments
# =====================================================================


def test_ac6_effective_and_end_dates(ctx):
    """BOTH directions: a future earning is not paid early, and a deduction
    that has passed its end_date stops deducting."""
    a, _ = _company('Ac6Co')
    emp = _employee(a)
    basic = _basic_assignment(a, emp)

    earn = _item(a, 'shift', 'Shift Allowance', 'earning', 'fixed', 'taxable')
    ded = _item(a, 'stop', 'Expiring Loan', 'deduction', 'fixed', 'taxable')

    _assign(a, emp, earn, fixed_amount=Decimal('1000'),
            effective_date=date(2026, 10, 1))
    _assign(a, emp, ded, fixed_amount=Decimal('500'),
            effective_date=date(2026, 1, 1), end_date=date(2026, 9, 30))
    db.session.commit()

    # September: the future earning is EXCLUDED, the live deduction applies.
    sep = _calc(emp, a, for_date=date(2026, 9, 15))
    keys = {li['item_key'] for li in sep['line_items']}
    assert 'shift' not in keys, (
        'an assignment effective next month must NOT be paid this month'
    )
    assert 'stop' in keys, 'a live deduction must apply'
    assert sep['gross'] == Decimal('10000')
    assert sep['total_deductions'] == Decimal('500.00')

    # October: the earning starts.
    octo = _calc(emp, a, for_date=date(2026, 10, 15))
    assert 'shift' in {li['item_key'] for li in octo['line_items']}
    assert octo['gross'] == Decimal('11000')

    # November: the deduction has PASSED its end_date and must stop.
    nov = _calc(emp, a, for_date=date(2026, 11, 15))
    assert 'stop' not in {li['item_key'] for li in nov['line_items']}, (
        'a deduction past its end_date must STOP deducting'
    )
    assert nov['total_deductions'] == Decimal('0.00')


# =====================================================================
# AC9 -- CSV upload minimum bar
# =====================================================================


def test_ac9_legacy_csv_keeps_working(ctx):
    """Legacy basic_salary + allowances columns still produce a correct payroll.

    The itemized-columns half of AC9 is NOT APPLICABLE: the spec decided in
    this phase that there are no itemized CSV columns. Not tested, by decision.
    """
    a, user = _company('Ac9Co')
    from payroll_engine.payroll_bp import _annotate_general_allowance
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.models import PayrollDraft, PayrollRun, Payslip

    _employee(a)  # created exactly once; process_payroll reuses it

    rows = [{
        'id': 'EMP001', 'name': 'Person EMP001', 'basic': 10000.0,
        'allowances': 2500.0, 'gross': 12500.0, 'tax': 1500.0,
        'pension_employee': 700.0, 'pension_employer': 1100.0, 'net': 10300.0,
    }]
    _annotate_general_allowance(a.id, rows)

    run = PayrollRun(company_id=a.id, period='2026-09', status='review',
                     run_date=date(2026, 9, 1), approved_by=user.id)
    db.session.add(run)
    db.session.commit()
    db.session.add(PayrollDraft(payroll_run_id=run.id, company_id=a.id,
                                employee_data=rows))
    db.session.commit()

    res = process_payroll(run=run, company_id=a.id, user_id=user.id,
                          user_email='o@t.com', request_ip='127.0.0.1')
    assert res.success is True, getattr(res, 'error', None)

    ps = Payslip.query.filter_by(payroll_run_id=run.id, company_id=a.id).first()
    assert ps is not None
    assert ps.gross_salary == Decimal('12500'), (
        f'legacy CSV allowances must reach gross, got {ps.gross_salary}'
    )


# =====================================================================
# AC11 -- report templates show any pay item by key
# =====================================================================


def test_ac11_report_column_resolves_by_key_per_company(ctx):
    from payroll_engine.models import PayItemType
    from payroll_engine.report_templates import _pay_item_amount

    a, _ = _company('CoA')
    b, _ = _company('CoB')

    _item(a, 'night_shift', 'Night Shift Allowance', 'earning',
          'rate_x_units', 'taxable', rate=Decimal('150'))
    db.session.commit()

    class PS:
        company_id = a.id
        line_items = [
            {'item_key': 'night_shift', 'classification': 'earning',
             'earned_amount': Decimal('2400')},
        ]

    class PS_B:
        company_id = b.id
        line_items = []

    assert _pay_item_amount(PS(), 'night_shift') == 2400.0, (
        'the ERCA column must resolve night_shift for Company A'
    )
    assert _pay_item_amount(PS_B(), 'night_shift') == 0, (
        'Company B has no night_shift and must report 0'
    )
    assert PayItemType.query.filter_by(company_id=b.id, key='night_shift').first() is None
