"""Employee pay-item assignments from the company catalog (catalog PR 5).

Covers the employee page (list / add / edit / end / delete), the rules in
``services.employee_assignments`` (used assignments are never deleted or
rewritten, overlaps, deduction labels, legacy-allowance confirmation),
role scoping (owner / accountant edit; employee read-only, own record only,
through the portal), tenant isolation, the company default amount and
per-employee override, audit rows, and that none of it changes a payroll
amount (assignments written here calculate exactly like the ones the
existing routes write; approved months never change).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from flask import g

from payroll_engine import create_app, db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeAllowance,
    PayItemType,
    PayrollItemAssignment,
    Payslip,
    User,
    UserCompany,
)
from payroll_engine.services import employee_assignments as ea

PASSWORD = 'Test1234!'
RUN_DATE = date(2026, 9, 1)


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False
    )

    @app.before_request
    def _fresh_login_user():
        g.pop('_login_user', None)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _company(name):
    co = Company(name=name, billing_status='active', plan_code='standard', paid_until=date.today() + timedelta(days=60))
    db.session.add(co)
    db.session.flush()
    seed_company_catalog(co.id, commit=False)
    db.session.commit()
    return co


def _user(company, phone, role):
    user = User(phone=phone, company_id=company.id, role=role, first_name='Synthetic', last_name='User')
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(UserCompany(user_id=user.id, company_id=company.id, role=role))
    db.session.commit()
    return user


def _employee(company_id, code='E1', salary='10000', allowances='0', user=None):
    emp = Employee(
        company_id=company_id,
        employee_id=code,
        name=f'Emp {code}',
        phone='0912345670',
        basic_salary=Decimal(salary),
        allowances=Decimal(allowances),
        user_id=user.id if user else None,
    )
    db.session.add(emp)
    db.session.commit()
    return emp


@pytest.fixture
def world(app):
    a = _company('Assign A PLC')
    b = _company('Assign B PLC')
    emp_user = _user(a, '911200003', 'employee')
    w = {
        'a': a.id,
        'b': b.id,
        'owner': _user(a, '911200001', 'owner'),
        'accountant': _user(a, '911200002', 'accountant'),
        'employee_user': emp_user,
        'owner_b': _user(b, '911200004', 'owner'),
    }
    w['e1'] = _employee(a.id, 'E1', user=emp_user)
    w['e2'] = _employee(a.id, 'E2', salary='12000')
    w['eb'] = _employee(b.id, 'B1')
    return w


def _login(app, user):
    client = app.test_client()
    resp = client.post('/auth/login', data={'login_id': user.phone, 'password': PASSWORD})
    assert resp.status_code == 302, resp.data[:300]
    return client


def _item(company_id, key):
    return PayItemType.query.filter_by(company_id=company_id, key=key).one()


def _audit(company_id, action):
    return AuditLog.query.filter_by(company_id=company_id, action=action).order_by(AuditLog.id).all()


def _add(client, emp, item, follow_redirects=False, **form):
    data = {'pay_item_type_id': item.id, 'amount': '1500', 'start_date': '2026-09-01'}
    data.update(form)
    return client.post(f'/employees/{emp.id}/pay-items', data=data, follow_redirects=follow_redirects)


def _assignments(emp):
    return (
        PayrollItemAssignment.query.filter_by(company_id=emp.company_id, employee_id=emp.id)
        .order_by(PayrollItemAssignment.id)
        .all()
    )


def _approve_month(company_id, user_id, start=RUN_DATE):
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.services.worksheet_review import create_review

    run = create_review(company_id, user_id, start)
    db.session.commit()
    result = process_payroll(run, company_id, user_id, 'owner@test.example', '127.0.0.1')
    assert result.success, result.message or result.error
    return run


# ---------------------------------------------------------------------------
# Adding and listing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('role', ['owner', 'accountant'])
def test_owner_and_accountant_add_assignment(app, world, role):
    client = _login(app, world[role])
    item = _item(world['a'], 'transport')
    resp = _add(client, world['e1'], item, amount='1,500.00')
    assert resp.status_code == 302
    rows = _assignments(world['e1'])
    assert len(rows) == 1
    a = rows[0]
    assert (a.pay_item_type_id, a.fixed_amount, a.effective_date, a.end_date) == (
        item.id,
        Decimal('1500.00'),
        date(2026, 9, 1),
        None,
    )
    assert a.created_by == world[role].id
    [log] = _audit(world['a'], 'pay_item_assignment_created')
    assert log.details['item_key'] == 'transport' and log.details['value'] == '1500.00'
    page = client.get(f'/employees/{world["e1"].id}')
    assert page.status_code == 200
    assert b'data-assignment-id="%d"' % a.id in page.data


def test_employee_role_cannot_use_employee_pages(app, world):
    client = _login(app, world['employee_user'])
    item = _item(world['a'], 'transport')
    assert _add(client, world['e1'], item).status_code == 403
    assert client.get(f'/employees/{world["e1"].id}').status_code == 403
    assert client.get('/employees/pay-items/import').status_code == 403
    assert _assignments(world['e1']) == []


def test_other_company_employee_and_item_rejected(app, world):
    client = _login(app, world['owner'])
    # Another company's employee: 404.
    assert _add(client, world['eb'], _item(world['a'], 'transport')).status_code == 404
    # Another company's item id: refused, nothing written.
    resp = _add(client, world['e1'], _item(world['b'], 'transport'), follow_redirects=False)
    assert resp.status_code == 302
    assert _assignments(world['e1']) == []
    # System items (basic salary, pension, tax) are never assignable here.
    for key in ('basic_salary', 'employee_pension', 'income_tax'):
        sys_item = PayItemType.query.filter_by(company_id=None, key=key).one()
        _add(client, world['e1'], sys_item)
        with pytest.raises(ea.AssignmentError):
            ea.assignable_item(world['a'], key=key)
    assert _assignments(world['e1']) == []


def test_validation_messages(app, world):
    e1 = world['e1']
    transport = _item(world['a'], 'transport')
    loan = _item(world['a'], 'loan')
    cases = [
        (transport, {'value': '0'}, 'more than zero'),
        (transport, {'value': '-5'}, 'more than zero'),
        (transport, {'value': 'abc'}, 'not a number'),
        (transport, {'value': '10.005'}, 'two decimal places'),
        (transport, {'value': '101', 'mode': 'percent_of_basic'}, 'more than 100'),
        (transport, {'value': '5', 'mode': 'percent_of_net'}, 'not an amount type'),
        (loan, {'value': '5', 'mode': 'percent_of_basic', 'label': 'x'}, 'not an amount type'),
        (loan, {'value': '500'}, 'needs a label'),
        (transport, {'value': '500', 'start': '2026-10-01', 'end': '2026-09-01'}, 'before the start'),
        (transport, {'value': '500', 'start': '01/10/2026'}, 'YYYY-MM-DD'),
    ]
    for item, kw, message in cases:
        with pytest.raises(ea.AssignmentError, match=message):
            ea.create_assignment(world['a'], None, e1, item, **kw)
        db.session.rollback()
    assert _assignments(e1) == []


def test_percent_modes_and_existing_route_rows_are_listed(app, world):
    client = _login(app, world['owner'])
    e1 = world['e1']
    _add(client, e1, _item(world['a'], 'housing'), amount_type='percent_of_basic', amount='12.5')
    _add(client, e1, _item(world['a'], 'cost_sharing'), amount_type='percent_of_net', amount='10', label='MoE')
    # A deduction written by the pre-existing route (it never showed on the page before).
    client.post(
        f'/employees/{e1.id}/deductions/add',
        data={'deduction_type': 'loan', 'label': 'Old route loan', 'amount': '300', 'tracking_mode': 'date_bounded'},
    )
    rows = {r.label: r for r in ea.employee_view(world['a'], e1)}
    assert rows['Housing Allowance'].mode == 'percent_of_basic' if 'Housing Allowance' in rows else True
    modes = sorted((r.item.key, r.mode, str(r.value)) for r in rows.values())
    assert ('cost_sharing', 'percent_of_net', '10.00') in modes
    assert ('loan', 'fixed', '300.00') in modes
    assert any(k == 'housing' and m == 'percent_of_basic' and v == '12.50' for k, m, v in modes)
    page = client.get(f'/employees/{e1.id}').data
    assert b'Old route loan' in page and b'12.50% of basic' in page and b'10.00% of net' in page


def test_earning_overlap_rejected_deduction_overlap_needs_distinct_label(app, world):
    e1, cid = world['e1'], world['a']
    transport, loan = _item(cid, 'transport'), _item(cid, 'loan')
    ea.create_assignment(cid, None, e1, transport, value='1000', start='2026-09-01', end='2026-12-31')
    db.session.commit()
    with pytest.raises(ea.AssignmentError, match='already runs'):
        ea.create_assignment(cid, None, e1, transport, value='1200', start='2026-12-01')
    db.session.rollback()
    ea.create_assignment(cid, None, e1, transport, value='1200', start='2027-01-01')
    ea.create_assignment(cid, None, e1, loan, value='500', label='Loan A')
    ea.create_assignment(cid, None, e1, loan, value='700', label='Loan B')
    db.session.commit()
    with pytest.raises(ea.AssignmentError, match='already runs'):
        ea.create_assignment(cid, None, e1, loan, value='900', label='Loan A')
    db.session.rollback()
    assert len(_assignments(e1)) == 4


def test_legacy_allowance_needs_confirmation(app, world):
    cid = world['a']
    legacy = _employee(cid, 'L1', allowances='2000')
    client = _login(app, world['owner'])
    page = client.get(f'/employees/{legacy.id}').data
    assert b'legacy allowances of ETB 2,000.00' in page
    resp = _add(client, legacy, _item(cid, 'transport'), follow_redirects=True)
    assert b'legacy allowances of ETB 2,000.00' in resp.data
    assert _assignments(legacy) == []
    # A deduction does not change which allowances payroll pays: no confirmation needed.
    _add(client, legacy, _item(cid, 'loan'), label='Loan')
    assert len(_assignments(legacy)) == 1
    _add(client, legacy, _item(cid, 'transport'), confirm_legacy='1')
    assert len(_assignments(legacy)) == 2
    # Legacy EmployeeAllowance records count too.
    rec_emp = _employee(cid, 'L2')
    db.session.add(
        EmployeeAllowance(
            company_id=cid, employee_id=rec_emp.id, allowance_type='housing', amount=Decimal('800'), is_active=True
        )
    )
    db.session.commit()
    with pytest.raises(ea.LegacyAllowanceConfirmationError):
        ea.create_assignment(cid, None, rec_emp, _item(cid, 'housing'), value='800')


# ---------------------------------------------------------------------------
# Editing, ending, deleting: never rewrite approved months
# ---------------------------------------------------------------------------


def test_unused_assignment_edited_in_place_and_deleted(app, world):
    client = _login(app, world['accountant'])
    e1 = world['e1']
    _add(client, e1, _item(world['a'], 'transport'), amount='1000')
    [a] = _assignments(e1)
    resp = client.post(
        f'/employees/{e1.id}/pay-items/{a.id}/edit',
        data={'amount_type': 'fixed', 'amount': '1100', 'start_date': '2026-08-01', 'end_date': '', 'label': ''},
    )
    assert resp.status_code == 302
    db.session.refresh(a)
    assert (a.fixed_amount, a.effective_date) == (Decimal('1100.00'), date(2026, 8, 1))
    assert _audit(world['a'], 'pay_item_assignment_updated')[-1].details['before']['value'] == '1000.00'
    assert client.post(f'/employees/{e1.id}/pay-items/{a.id}/delete').status_code == 302
    assert _assignments(e1) == []
    assert _audit(world['a'], 'pay_item_assignment_deleted')


def test_used_assignment_never_deleted_or_rewritten(app, world):
    cid, owner = world['a'], world['owner']
    e1 = world['e1']
    a = ea.create_assignment(cid, owner.id, e1, _item(cid, 'transport'), value='1500', start='2026-08-01')
    db.session.commit()
    _approve_month(cid, owner.id)
    payslip = Payslip.query.filter_by(company_id=cid, employee_id=e1.id).one()
    approved = (payslip.gross_salary, payslip.net_pay, payslip.tax)
    assert any(li.get('assignment_id') == a.id for li in payslip.line_items)
    assert ea.usage(cid, e1.id) == {a.id: RUN_DATE}

    client = _login(app, world['owner'])
    page = client.get(f'/employees/{e1.id}').data
    assert b'Used in approved payroll up to Sep 2026' in page
    # Delete refused; the row stays.
    resp = client.post(f'/employees/{e1.id}/pay-items/{a.id}/delete', follow_redirects=True)
    assert b'cannot be deleted' in resp.data
    assert db.session.get(PayrollItemAssignment, a.id) is not None
    # End inside the paid month refused; end at month end or later allowed.
    resp = client.post(
        f'/employees/{e1.id}/pay-items/{a.id}/end', data={'end_date': '2026-09-15'}, follow_redirects=True
    )
    assert b'End it on 2026-09-30 or later' in resp.data
    # Start date cannot move.
    with pytest.raises(ea.AssignmentError, match='start date cannot change'):
        ea.update_assignment(cid, None, a, value='1500', start='2026-07-01')
    db.session.rollback()
    # Amount change needs a date after the last approved month.
    with pytest.raises(ea.AssignmentError, match='Change from is required'):
        ea.update_assignment(cid, None, a, value='1800')
    db.session.rollback()
    with pytest.raises(ea.AssignmentError, match='2026-10-01 or later'):
        ea.update_assignment(cid, None, a, value='1800', change_from='2026-09-20')
    db.session.rollback()
    resp = client.post(
        f'/employees/{e1.id}/pay-items/{a.id}/edit',
        data={'amount_type': 'fixed', 'amount': '1800', 'end_date': '', 'label': '', 'change_from': '2026-10-01'},
    )
    assert resp.status_code == 302
    rows = _assignments(e1)
    old, new = rows
    assert old.id == a.id and old.end_date == date(2026, 9, 30) and old.fixed_amount == Decimal('1500.00')
    assert new.effective_date == date(2026, 10, 1) and new.fixed_amount == Decimal('1800.00') and new.end_date is None
    [log] = _audit(cid, 'pay_item_assignment_revised')
    assert log.details['replaces_assignment_id'] == a.id
    # The approved month is untouched.
    db.session.refresh(payslip)
    assert (payslip.gross_salary, payslip.net_pay, payslip.tax) == approved
    # Label and end date of a used row change in place.
    ea.update_assignment(cid, None, new, value='1800', end='2027-06-30', label='Bus')
    db.session.commit()
    assert (new.end_date, new.custom_label) == (date(2027, 6, 30), 'Bus')


def test_next_month_uses_new_amount_and_old_month_unchanged(app, world):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    cid, owner, e1 = world['a'], world['owner'], world['e1']
    a = ea.create_assignment(cid, owner.id, e1, _item(cid, 'housing'), value='2000', start='2026-08-01')
    db.session.commit()
    _approve_month(cid, owner.id)
    ea.update_assignment(cid, owner.id, a, value='2500', change_from='2026-10-01')
    db.session.commit()
    sep = calculate_payroll_from_assignments(e1, cid, date(2026, 9, 30), consume_balances=False)
    octo = calculate_payroll_from_assignments(e1, cid, date(2026, 10, 31), consume_balances=False)
    assert sep['gross'] == Decimal('2000.00')  # no basic assignment on this employee: allowances only
    assert octo['gross'] == Decimal('2500.00')


# ---------------------------------------------------------------------------
# Equivalence with the existing writers (behaviour preserved)
# ---------------------------------------------------------------------------


def test_service_rows_calculate_like_existing_route_rows(app, world):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments
    from payroll_engine.services.worksheet_review import calculate_rows

    cid = world['a']
    client = _login(app, world['owner'])
    old_emp = _employee(cid, 'OLD', salary='9000')
    new_emp = _employee(cid, 'NEW', salary='9000')
    # Old routes.
    for key, amount in (('transport', '2500'), ('hardship', '700'), ('housing', '1500')):
        client.post(f'/employees/{old_emp.id}/allowances/add', data={'allowance_type': key, 'amount': amount})
    client.post(
        f'/employees/{old_emp.id}/deductions/add',
        data={
            'deduction_type': 'loan',
            'label': 'Loan',
            'amount': '400',
            'tracking_mode': 'date_bounded',
            'start_date': '2026-01-01',
        },
    )
    # New page.
    for key, amount in (('transport', '2500'), ('hardship', '700'), ('housing', '1500')):
        _add(client, new_emp, _item(cid, key), amount=amount, start_date='')
    _add(client, new_emp, _item(cid, 'loan'), amount='400', label='Loan', start_date='2026-01-01')
    for d in (date(2026, 9, 30), date(2026, 10, 31)):
        a = calculate_payroll_from_assignments(old_emp, cid, d, consume_balances=False)
        b = calculate_payroll_from_assignments(new_emp, cid, d, consume_balances=False)
        for key in ('gross', 'taxable', 'tax', 'pension_employee', 'net', 'total_deductions', 'exempt_allowances'):
            assert a[key] == b[key], key
    rows = {r['id']: r for r in calculate_rows(cid, date(2026, 10, 1))}
    for key in ('gross', 'taxable', 'tax', 'net', 'total_deductions'):
        assert rows['OLD'][key] == rows['NEW'][key], key


def test_default_amount_prefills_and_marks_override_without_changing_amounts(app, world):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    cid = world['a']
    owner = _login(app, world['owner'])
    transport = _item(cid, 'transport')
    e1, e2 = world['e1'], world['e2']
    ea.create_assignment(cid, None, e1, transport, value='1000')
    db.session.commit()
    before = calculate_payroll_from_assignments(e1, cid, date(2026, 10, 31), consume_balances=False)
    # Owner sets the default; accountant cannot.
    acc = _login(app, world['accountant'])
    assert (
        acc.post(f'/settings/pay-items/{transport.id}/default-amount', data={'default_amount': '1200'}).status_code
        == 403
    )
    assert (
        owner.post(f'/settings/pay-items/{transport.id}/default-amount', data={'default_amount': '1,200'}).status_code
        == 302
    )
    db.session.refresh(transport)
    assert transport.default_amount == Decimal('1200.00')
    details = _audit(cid, 'pay_item_default_amount_changed')[-1].details
    assert {k: details[k] for k in ('pay_item_id', 'key', 'old', 'new')} == {
        'pay_item_id': transport.id,
        'key': 'transport',
        'old': None,
        'new': '1200.00',
    }
    after = calculate_payroll_from_assignments(e1, cid, date(2026, 10, 31), consume_balances=False)
    assert before['net'] == after['net'] and before['gross'] == after['gross']
    # Page pre-fills the default and marks e1's own amount as an override.
    page = owner.get(f'/employees/{e1.id}').data
    assert b'data-default="1200.00"' in page and b'Own Amount' in page
    ea.create_assignment(cid, None, e2, transport, value='1200')
    db.session.commit()
    [row] = ea.employee_view(cid, e2)
    assert not row.is_override
    # Refused for system items and bad values; cleared with an empty value.
    system = PayItemType.query.filter_by(company_id=None, key='basic_salary').one()
    assert (
        owner.post(f'/settings/pay-items/{system.id}/default-amount', data={'default_amount': '1'}).status_code == 403
    )
    with pytest.raises(ea.AssignmentError):
        ea.set_default_amount(transport, None, '-1')
    assert ea.set_default_amount(transport, None, '') is True
    assert transport.default_amount is None


# ---------------------------------------------------------------------------
# Employee portal: read-only, own record only
# ---------------------------------------------------------------------------


def test_employee_sees_only_own_pay_items_read_only(app, world):
    cid = world['a']
    ea.create_assignment(cid, None, world['e1'], _item(cid, 'transport'), value='1500', label='My bus')
    ea.create_assignment(cid, None, world['e2'], _item(cid, 'housing'), value='9999', label='Someone else')
    ea.create_assignment(
        cid, None, world['e1'], _item(cid, 'food'), value='300', start='2020-01-01', end='2020-12-31', label='Old food'
    )
    db.session.commit()
    client = _login(app, world['employee_user'])
    page = client.get('/my/profile')
    assert page.status_code == 200
    body = page.data
    assert b'data-testid="my-pay-items"' in body and b'My bus' in body and b'ETB 1,500.00' in body
    assert b'Someone else' not in body and b'9999' not in body
    assert b'Old food' not in body  # ended rows are not shown to the employee
    assert b'/pay-items' not in body  # no edit/end/delete links
    a = _assignments(world['e1'])[0]
    assert (
        client.post(f'/employees/{world["e1"].id}/pay-items/{a.id}/end', data={'end_date': '2026-12-31'}).status_code
        == 403
    )


def test_tenant_isolation_on_edit_routes(app, world):
    cid = world['a']
    a = ea.create_assignment(cid, None, world['e1'], _item(cid, 'transport'), value='1500')
    db.session.commit()
    other = _login(app, world['owner_b'])
    for path in ('edit', 'end', 'delete'):
        resp = other.post(f'/employees/{world["e1"].id}/pay-items/{a.id}/{path}', data={'end_date': '2026-12-31'})
        assert resp.status_code == 404
    # Mismatched employee id in the URL is also a 404.
    owner = _login(app, world['owner'])
    assert owner.post(f'/employees/{world["e2"].id}/pay-items/{a.id}/delete').status_code == 404
    assert db.session.get(PayrollItemAssignment, a.id) is not None


def test_basic_salary_row_is_shown_but_managed(app, world):
    from payroll_engine.services.payroll_service import _ensure_basic_assignment

    cid = world['a']
    _ensure_basic_assignment(world['e1'], cid, Decimal('10000'))
    db.session.commit()
    [row] = ea.employee_view(cid, world['e1'])
    assert row.managed and not row.can_delete
    client = _login(app, world['owner'])
    assert b'Managed by the system' in client.get(f'/employees/{world["e1"].id}').data
    with pytest.raises(ea.AssignmentError, match='managed by the system'):
        ea.delete_assignment(cid, None, row.assignment)
