"""Company pay-item settings page (catalog PR 2).

Covers: owner-only access, tenant isolation (another company's item is a 404),
locked statutory items, add / rename / reorder / deactivate / reactivate /
delete with their rules, deactivated items hidden from new-assignment pickers
but kept for history, audit rows for every change, CSRF, Amharic / Afaan Oromoo
label rendering, and that reordering never changes payroll amounts.
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
    PayItemType,
    PayrollItemAssignment,
    PayrollRun,
    Payslip,
    User,
    UserCompany,
)
from payroll_engine.services import pay_item_settings as svc

PASSWORD = 'Test1234!'


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
    )

    @app.before_request
    def _fresh_login_user():
        # The fixture keeps one app context open for direct DB access, so
        # flask.g (where Flask-Login caches current_user) would otherwise leak
        # between requests from different test clients.
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


@pytest.fixture
def world(app):
    a = _company('Settings A PLC')
    b = _company('Settings B PLC')
    return {
        'a': a.id,
        'b': b.id,
        'owner': _user(a, '911100001', 'owner').phone,
        'accountant': _user(a, '911100002', 'accountant').phone,
        'employee': _user(a, '911100003', 'employee').phone,
        'owner_b': _user(b, '911100004', 'owner').phone,
    }


def _login(app, phone):
    client = app.test_client()
    resp = client.post('/auth/login', data={'login_id': phone, 'password': PASSWORD})
    assert resp.status_code == 302, resp.data[:300]
    return client


@pytest.fixture
def owner(app, world):
    return _login(app, world['owner'])


def _item(company_id, key):
    return PayItemType.query.filter_by(company_id=company_id, key=key).one()


def _system(key):
    return PayItemType.query.filter_by(company_id=None, key=key).one()


def _audit(company_id, action):
    return AuditLog.query.filter_by(company_id=company_id, action=action).order_by(AuditLog.id).all()


def _employee(company_id, code='E1', salary=10000):
    emp = Employee(company_id=company_id, employee_id=code, name=f'Emp {code}', phone='0912345670', basic_salary=salary)
    db.session.add(emp)
    db.session.commit()
    return emp


def _assign(company_id, emp, item, amount=500, **kw):
    row = PayrollItemAssignment(
        company_id=company_id,
        employee_id=emp.id,
        pay_item_type_id=item.id,
        fixed_amount=None if amount is None else Decimal(amount),
        **kw,
    )
    db.session.add(row)
    db.session.commit()
    return row


def _create(client, **data):
    form = {'kind': 'earning', 'key': 'fuel_allowance', 'name_en': 'Fuel Allowance', 'name_am': '', 'name_om': ''}
    form.update(data)
    return client.post('/settings/pay-items', data=form)


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


def test_owner_sees_grouped_catalog_with_locked_system_items(owner, world):
    resp = owner.get('/settings/pay-items')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for heading in ('Earnings', 'Allowances', 'Deductions', 'Employer Contributions', 'Tax'):
        assert heading in html
    assert 'Basic Salary' in html and 'Income Tax' in html and 'Employer Pension (11%)' in html
    assert 'Transport Allowance' in html and 'Court Order Deduction' in html
    # System rows are marked locked and offer no change controls.
    basic = _system('basic_salary')
    row = html.split(f'id="item-{basic.id}"')[1].split('</tr>')[0]
    assert 'Locked' in row and 'Statutory system item' in row
    assert '/move' not in row and '/deactivate' not in row and '/edit' not in row
    # Company template rows can be edited.
    transport = _item(world['a'], 'transport')
    row = html.split(f'id="item-{transport.id}"')[1].split('</tr>')[0]
    assert f'/settings/pay-items/{transport.id}/edit' in row


@pytest.mark.parametrize('role', ['accountant', 'employee'])
def test_non_owner_roles_are_forbidden(app, world, role):
    client = _login(app, world[role])
    transport = _item(world['a'], 'transport')
    assert client.get('/settings/pay-items').status_code == 403
    assert (
        client.post('/settings/pay-items', data={'kind': 'earning', 'key': 'x_item', 'name_en': 'X'}).status_code == 403
    )
    assert client.get(f'/settings/pay-items/{transport.id}/edit').status_code == 403
    for action in ('move', 'deactivate', 'reactivate', 'delete'):
        assert client.post(f'/settings/pay-items/{transport.id}/{action}', data={'direction': 'up'}).status_code == 403
    assert PayItemType.query.filter_by(company_id=world['a'], key='x_item').first() is None
    assert _item(world['a'], 'transport').is_active


def test_anonymous_is_sent_to_login(app):
    resp = app.test_client().get('/settings/pay-items')
    assert resp.status_code == 302 and '/auth/login' in resp.headers['Location']


def test_settings_nav_link_for_owner_only(app, world, owner):
    assert '/settings/pay-items' in owner.get('/settings/team').get_data(as_text=True)
    assert '/settings/pay-items' in owner.get('/settings/company').get_data(as_text=True)
    accountant = _login(app, world['accountant'])
    assert '/settings/pay-items' not in accountant.get('/employees').get_data(as_text=True)


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


def test_other_company_items_are_404_on_every_route(owner, world):
    foreign = _item(world['b'], 'housing')
    before = (foreign.name_en, foreign.sort_order, foreign.is_active)
    assert owner.get(f'/settings/pay-items/{foreign.id}/edit').status_code == 404
    assert owner.post(f'/settings/pay-items/{foreign.id}/edit', data={'name_en': 'Hijacked'}).status_code == 404
    for action, data in (('move', {'direction': 'up'}), ('deactivate', {}), ('reactivate', {}), ('delete', {})):
        assert owner.post(f'/settings/pay-items/{foreign.id}/{action}', data=data).status_code == 404
    assert owner.get('/settings/pay-items/999999/edit').status_code == 404
    db.session.expire_all()
    foreign = PayItemType.query.filter_by(company_id=world['b'], key='housing').one()
    assert (foreign.name_en, foreign.sort_order, foreign.is_active) == before
    assert f'id="item-{foreign.id}"' not in owner.get('/settings/pay-items').get_data(as_text=True)
    assert _audit(world['a'], 'pay_item_renamed') == [] and _audit(world['b'], 'pay_item_renamed') == []


def test_same_code_allowed_in_another_company(app, world, owner):
    assert _create(owner, key='fuel_allowance').status_code == 302
    owner_b = _login(app, world['owner_b'])
    assert _create(owner_b, key='fuel_allowance').status_code == 302
    assert _item(world['a'], 'fuel_allowance').id != _item(world['b'], 'fuel_allowance').id


# ---------------------------------------------------------------------------
# Locked statutory items
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('key', ['basic_salary', 'income_tax', 'employee_pension', 'employer_pension'])
def test_system_items_are_read_only(owner, world, key):
    item = _system(key)
    before = (item.name_en, item.name_am, item.sort_order, item.is_active, item.tax_treatment)
    page = owner.get(f'/settings/pay-items/{item.id}/edit')
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'Statutory system item' in html and 'disabled' in html and 'Save Changes' not in html
    assert owner.post(f'/settings/pay-items/{item.id}/edit', data={'name_en': 'Changed'}).status_code == 403
    for action, data in (('move', {'direction': 'down'}), ('deactivate', {}), ('reactivate', {}), ('delete', {})):
        assert owner.post(f'/settings/pay-items/{item.id}/{action}', data=data).status_code == 403
    db.session.expire_all()
    item = _system(key)
    assert (item.name_en, item.name_am, item.sort_order, item.is_active, item.tax_treatment) == before


def test_service_refuses_system_items_directly(world):
    for fn, kwargs in (
        (svc.rename_item, {'name_en': 'X'}),
        (svc.move_item, {'direction': 'up'}),
    ):
        with pytest.raises(svc.PayItemSettingsError, match='locked'):
            fn(_system('income_tax'), 1, **kwargs)
    for fn in (svc.deactivate_item, svc.reactivate_item, svc.delete_item):
        with pytest.raises(svc.PayItemSettingsError, match='locked'):
            fn(_system('employee_pension'), 1)


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------


def test_add_custom_item(owner, world):
    resp = _create(
        owner, key='Fuel_Allowance ', name_en=' Fuel Allowance ', name_am='የነዳጅ አበል', name_om='Abbaltii Boba’aa'
    )
    assert resp.status_code == 302
    item = _item(world['a'], 'fuel_allowance')
    assert (item.name_en, item.name_am, item.name_om) == ('Fuel Allowance', 'የነዳጅ አበል', 'Abbaltii Boba’aa')
    assert item.classification == 'earning' and item.calculation_method == 'fixed'
    assert item.tax_treatment == 'taxable' and item.exempt_cap_amount is None and item.exempt_cap_percent is None
    assert item.is_system is False and item.is_active is True
    top = max(i.sort_order for i in PayItemType.query.filter_by(company_id=world['a'], classification='earning'))
    assert item.sort_order == top
    (log,) = _audit(world['a'], 'pay_item_created')
    assert log.details['key'] == 'fuel_allowance' and log.details['tax_treatment'] == 'taxable'
    assert log.details['pay_item_id'] == item.id


def test_add_deduction_lands_in_deductions(owner, world):
    assert _create(owner, kind='deduction', key='union_dues', name_en='Union Dues').status_code == 302
    item = _item(world['a'], 'union_dues')
    assert item.classification == 'deduction' and svc.group_of(item) == 'deductions'


def test_add_ignores_posted_legal_attributes(owner, world):
    resp = _create(
        owner, key='bonus_x', tax_treatment='exempt', exempt_cap_amount='9999', calculation_method='percent_of_basic'
    )
    assert resp.status_code == 302
    item = _item(world['a'], 'bonus_x')
    assert item.tax_treatment == 'taxable' and item.calculation_method == 'fixed' and item.exempt_cap_amount is None


@pytest.mark.parametrize(
    'data,message',
    [
        ({'key': ''}, 'Code must be'),
        ({'key': '1abc'}, 'Code must be'),
        ({'key': 'has space'}, 'Code must be'),
        ({'key': 'a' * 31}, 'Code must be'),
        ({'key': 'basic_salary'}, 'reserved'),
        ({'key': 'income_tax'}, 'reserved'),
        ({'key': 'employer_pension'}, 'reserved'),
        ({'key': 'transport'}, 'reserved'),
        ({'name_en': '   '}, 'English name is required'),
        ({'name_en': 'x' * 101}, '100 characters'),
        ({'name_am': 'ሀ' * 101}, '100 characters'),
        ({'name_om': 'y' * 101}, '100 characters'),
        ({'name_en': 'Bad\x00name'}, 'invalid characters'),
        ({'kind': 'tax'}, 'allowance (earning) or a deduction'),
        ({'kind': 'employer_charge'}, 'allowance (earning) or a deduction'),
    ],
)
def test_add_validation(owner, world, data, message):
    count = PayItemType.query.filter_by(company_id=world['a']).count()
    resp = _create(owner, **data)
    assert resp.status_code == 400
    assert message in resp.get_data(as_text=True)
    assert PayItemType.query.filter_by(company_id=world['a']).count() == count
    assert _audit(world['a'], 'pay_item_created') == []


def test_add_duplicate_code_rejected(owner, world):
    assert _create(owner).status_code == 302
    resp = _create(owner, name_en='Again')
    assert resp.status_code == 400 and 'already has an item with code' in resp.get_data(as_text=True)
    assert PayItemType.query.filter_by(company_id=world['a'], key='fuel_allowance').count() == 1


def test_add_failure_keeps_entered_values(owner):
    html = _create(owner, key='basic_salary', name_en='Keep Me').get_data(as_text=True)
    assert 'value="Keep Me"' in html


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------


def test_rename_changes_labels_only(owner, world):
    item = _item(world['a'], 'transport')
    before = (item.key, item.tax_treatment, item.exempt_cap_amount, item.exempt_cap_percent, item.sort_order)
    resp = owner.post(
        f'/settings/pay-items/{item.id}/edit',
        data={
            'name_en': 'Commute Allowance',
            'name_am': 'የመጓጓዣ አበል',
            'name_om': 'Abbaltii Geejjibaa',
            'key': 'hijacked_key',
            'tax_treatment': 'exempt',
            'exempt_cap_amount': '99999',
        },
    )
    assert resp.status_code == 302
    db.session.expire_all()
    item = _item(world['a'], 'transport')
    assert (item.name_en, item.name_am, item.name_om) == ('Commute Allowance', 'የመጓጓዣ አበል', 'Abbaltii Geejjibaa')
    assert (item.key, item.tax_treatment, item.exempt_cap_amount, item.exempt_cap_percent, item.sort_order) == before
    (log,) = _audit(world['a'], 'pay_item_renamed')
    assert log.details['old']['name_en'] == 'Transport Allowance'
    assert log.details['new'] == {
        'name_en': 'Commute Allowance',
        'name_am': 'የመጓጓዣ አበል',
        'name_om': 'Abbaltii Geejjibaa',
    }


def test_rename_validation_and_noop(owner, world):
    item = _item(world['a'], 'housing')
    resp = owner.post(f'/settings/pay-items/{item.id}/edit', data={'name_en': ''})
    assert resp.status_code == 400 and 'English name is required' in resp.get_data(as_text=True)
    resp = owner.post(f'/settings/pay-items/{item.id}/edit', data={'name_en': item.name_en, 'name_am': item.name_am})
    assert resp.status_code == 302
    assert _audit(world['a'], 'pay_item_renamed') == []
    db.session.expire_all()
    assert _item(world['a'], 'housing').name_en == 'Housing Allowance'


# ---------------------------------------------------------------------------
# Reorder
# ---------------------------------------------------------------------------


def _allowance_order(company_id):
    items = PayItemType.query.filter_by(company_id=company_id).order_by(PayItemType.sort_order, PayItemType.id).all()
    return [i.key for i in items if svc.group_of(i) == 'allowances']


def test_move_up_and_down_within_group(owner, world):
    order = _allowance_order(world['a'])
    second = _item(world['a'], order[1])
    assert owner.post(f'/settings/pay-items/{second.id}/move', data={'direction': 'up'}).status_code == 302
    db.session.expire_all()
    expected = [order[1], order[0], *order[2:]]
    assert _allowance_order(world['a']) == expected
    (log,) = _audit(world['a'], 'pay_item_reordered')
    assert log.details['direction'] == 'up' and set(log.details['changes']) == {order[0], order[1]}

    assert owner.post(f'/settings/pay-items/{second.id}/move', data={'direction': 'down'}).status_code == 302
    db.session.expire_all()
    assert _allowance_order(world['a']) == order


def test_move_at_edge_is_noop_and_bad_direction_rejected(owner, world):
    order = _allowance_order(world['a'])
    first = _item(world['a'], order[0])
    assert owner.post(f'/settings/pay-items/{first.id}/move', data={'direction': 'up'}).status_code == 302
    assert owner.post(f'/settings/pay-items/{first.id}/move', data={'direction': 'sideways'}).status_code == 302
    db.session.expire_all()
    assert _allowance_order(world['a']) == order
    assert _audit(world['a'], 'pay_item_reordered') == []


def test_move_resolves_tied_sort_orders(world):
    order = _allowance_order(world['a'])
    for key in order[:3]:
        _item(world['a'], key).sort_order = 150
    db.session.commit()
    order = _allowance_order(world['a'])  # ties broken by id
    third = _item(world['a'], order[2])
    assert svc.move_item(third, 1, 'up') is True
    db.session.commit()
    new_order = _allowance_order(world['a'])
    assert new_order[:3] == [order[0], order[2], order[1]]
    values = [_item(world['a'], k).sort_order for k in new_order]
    assert values == sorted(values) and len(set(values)) == len(values)


def test_reorder_does_not_change_payroll_amounts(world):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    emp = _employee(world['a'], salary=20000)
    _assign(world['a'], emp, _item(world['a'], 'transport'), 1800)
    _assign(world['a'], emp, _item(world['a'], 'housing'), 3000)
    _assign(world['a'], emp, _item(world['a'], 'loan'), None, percent_of_net=Decimal('10'))
    _assign(world['a'], emp, _item(world['a'], 'cost_sharing'), 400)

    def totals():
        db.session.expire_all()
        r = calculate_payroll_from_assignments(
            Employee.query.filter_by(id=emp.id, company_id=world['a']).one(),
            world['a'],
            date.today(),
            consume_balances=False,
        )
        keys = ('gross', 'taxable', 'tax', 'pension_employee', 'net_before_deductions', 'total_deductions', 'net')
        out = {k: r[k] for k in (*keys, 'exempt_allowances')}
        out['lines'] = sorted((li['item_key'], li['earned_amount']) for li in r['line_items'])
        return out

    before = totals()
    assert before['total_deductions'] > 0 and before['net'] > 0 and before['exempt_allowances'] > 0
    for key, direction in (('housing', 'up'), ('housing', 'up'), ('cost_sharing', 'up'), ('transport', 'down')):
        svc.move_item(_item(world['a'], key), 1, direction)
        db.session.commit()
    assert totals() == before


# ---------------------------------------------------------------------------
# Deactivate / reactivate
# ---------------------------------------------------------------------------


def test_deactivate_hides_from_pickers_and_reactivate_restores(app, world, owner):
    item = _item(world['a'], 'communication')
    emp = _employee(world['a'])
    assert owner.post(f'/settings/pay-items/{item.id}/deactivate').status_code == 302
    db.session.expire_all()
    assert _item(world['a'], 'communication').is_active is False
    (log,) = _audit(world['a'], 'pay_item_deactivated')
    assert log.details['key'] == 'communication'

    # Hidden from the employee screen's allowance picker ...
    html = owner.get(f'/employees/{emp.id}').get_data(as_text=True)
    assert 'value="communication"' not in html and 'value="housing"' in html
    # ... and refused when posted anyway.
    resp = owner.post(f'/employees/{emp.id}/allowances/add', data={'allowance_type': 'communication', 'amount': '100'})
    assert resp.status_code == 302
    assert PayrollItemAssignment.query.filter_by(company_id=world['a'], employee_id=emp.id).count() == 0
    # Still listed on the settings page, marked inactive.
    page = owner.get('/settings/pay-items').get_data(as_text=True)
    row = page.split(f'id="item-{item.id}"')[1].split('</tr>')[0]
    assert 'Inactive' in row and '/reactivate' in row

    assert owner.post(f'/settings/pay-items/{item.id}/reactivate').status_code == 302
    db.session.expire_all()
    assert _item(world['a'], 'communication').is_active is True
    assert len(_audit(world['a'], 'pay_item_reactivated')) == 1
    assert 'value="communication"' in owner.get(f'/employees/{emp.id}').get_data(as_text=True)


def test_deactivate_blocked_while_assignment_running(owner, world):
    item = _item(world['a'], 'housing')
    emp = _employee(world['a'])
    _assign(world['a'], emp, item)
    resp = owner.post(f'/settings/pay-items/{item.id}/deactivate', follow_redirects=True)
    assert 'still running' in resp.get_data(as_text=True)
    db.session.expire_all()
    assert _item(world['a'], 'housing').is_active is True
    assert _audit(world['a'], 'pay_item_deactivated') == []


def test_deactivate_allowed_once_assignments_ended_and_history_kept(owner, world):
    item = _item(world['a'], 'housing')
    emp = _employee(world['a'])
    ended = _assign(world['a'], emp, item, end_date=date.today() - timedelta(days=1))
    retired = _assign(world['a'], emp, item, is_active=False)
    assert owner.post(f'/settings/pay-items/{item.id}/deactivate').status_code == 302
    db.session.expire_all()
    assert _item(world['a'], 'housing').is_active is False
    ids = {a.id for a in PayrollItemAssignment.query.filter_by(company_id=world['a'], pay_item_type_id=item.id)}
    assert ids == {ended.id, retired.id}
    (log,) = _audit(world['a'], 'pay_item_deactivated')
    assert log.details['assignments_kept'] == 2


@pytest.mark.parametrize('key', ['general_allowance', 'advance'])
def test_import_managed_items_cannot_be_deactivated(owner, world, key):
    item = _item(world['a'], key)
    resp = owner.post(f'/settings/pay-items/{item.id}/deactivate', follow_redirects=True)
    assert 'payroll imports' in resp.get_data(as_text=True)
    db.session.expire_all()
    assert _item(world['a'], key).is_active is True


def test_reactivate_active_item_is_refused(owner, world):
    item = _item(world['a'], 'food')
    resp = owner.post(f'/settings/pay-items/{item.id}/reactivate', follow_redirects=True)
    assert 'already active' in resp.get_data(as_text=True)
    assert _audit(world['a'], 'pay_item_reactivated') == []


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_unused_custom_item(owner, world):
    _create(owner, key='gym_fee', kind='deduction', name_en='Gym Fee')
    item = _item(world['a'], 'gym_fee')
    item_id = item.id
    assert owner.post(f'/settings/pay-items/{item_id}/delete').status_code == 302
    assert PayItemType.query.filter_by(company_id=world['a'], key='gym_fee').first() is None
    (log,) = _audit(world['a'], 'pay_item_deleted')
    assert log.details['key'] == 'gym_fee' and log.details['pay_item_id'] == item_id
    assert log.details['name_en'] == 'Gym Fee'


def test_delete_blocked_when_used_by_any_assignment(owner, world):
    _create(owner, key='gym_fee', kind='deduction', name_en='Gym Fee')
    item = _item(world['a'], 'gym_fee')
    emp = _employee(world['a'])
    _assign(world['a'], emp, item, is_active=False)  # even a retired assignment is history
    resp = owner.post(f'/settings/pay-items/{item.id}/delete', follow_redirects=True)
    assert 'Deactivate it instead' in resp.get_data(as_text=True)
    assert PayItemType.query.filter_by(company_id=world['a'], key='gym_fee').first() is not None
    assert _audit(world['a'], 'pay_item_deleted') == []


def test_delete_blocked_when_on_a_payslip(owner, world):
    _create(owner, key='gym_fee', kind='deduction', name_en='Gym Fee')
    item = _item(world['a'], 'gym_fee')
    emp = _employee(world['a'])
    run = PayrollRun(company_id=world['a'], status='approved', period='2019-01')
    db.session.add(run)
    db.session.flush()
    db.session.add(
        Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            company_id=world['a'],
            gross_salary=10000,
            tax=1000,
            employee_pension=700,
            employer_pension=1100,
            net_pay=8300,
            line_items=[{'item_key': 'gym_fee', 'item_id': item.id, 'earned_amount': '50'}],
        )
    )
    db.session.commit()
    resp = owner.post(f'/settings/pay-items/{item.id}/delete', follow_redirects=True)
    assert 'appears on payslips' in resp.get_data(as_text=True)
    assert PayItemType.query.filter_by(company_id=world['a'], key='gym_fee').first() is not None


def test_standard_template_items_cannot_be_deleted(owner, world):
    item = _item(world['a'], 'uniform')
    page = owner.get('/settings/pay-items').get_data(as_text=True)
    row = page.split(f'id="item-{item.id}"')[1].split('</tr>')[0]
    assert '/delete' not in row
    resp = owner.post(f'/settings/pay-items/{item.id}/delete', follow_redirects=True)
    assert 'Standard items cannot be deleted' in resp.get_data(as_text=True)
    assert PayItemType.query.filter_by(company_id=world['a'], key='uniform').first() is not None


# ---------------------------------------------------------------------------
# CSRF and i18n
# ---------------------------------------------------------------------------


def test_csrf_token_required(app, world):
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        client = app.test_client()
        # Log in through the form with a valid token, then post without one.
        login_page = client.get('/auth/login').get_data(as_text=True)
        token = login_page.split('name="csrf_token" value="')[1].split('"')[0]
        resp = client.post('/auth/login', data={'login_id': world['owner'], 'password': PASSWORD, 'csrf_token': token})
        assert resp.status_code == 302
        resp = client.post('/settings/pay-items', data={'kind': 'earning', 'key': 'no_token', 'name_en': 'No Token'})
        assert resp.status_code in (400, 302)
        assert PayItemType.query.filter_by(company_id=world['a'], key='no_token').first() is None
        # The page itself carries tokens on every form, and a posted token works.
        html = client.get('/settings/pay-items').get_data(as_text=True)
        assert html.count('name="csrf_token"') >= 2
        token = html.split('name="csrf_token" value="')[1].split('"')[0]
        resp = client.post(
            '/settings/pay-items',
            data={'kind': 'earning', 'key': 'with_token', 'name_en': 'With Token', 'csrf_token': token},
        )
        assert resp.status_code == 302
        assert PayItemType.query.filter_by(company_id=world['a'], key='with_token').first() is not None
    finally:
        app.config['WTF_CSRF_ENABLED'] = False


def test_amharic_labels_render(owner, world):
    owner.get('/auth/language/am')
    html = owner.get('/settings/pay-items').get_data(as_text=True)
    assert 'የክፍያ ዓይነቶች' in html  # page title
    assert 'የትራንስፖርት አበል' in html and 'መሠረታዊ ደመወዝ' in html
    assert 'Transport Allowance' in html  # English shown as the secondary line


def test_oromo_labels_render_with_english_fallback(owner, world):
    _create(owner, key='fuel_allowance', name_en='Fuel Allowance', name_om='Abbaltii Boba’aa')
    owner.get('/auth/language/om')
    html = owner.get('/settings/pay-items').get_data(as_text=True)
    assert 'Gosoota Kaffaltii' in html
    fuel = _item(world['a'], 'fuel_allowance')
    row = html.split(f'id="item-{fuel.id}"')[1].split('</tr>')[0]
    assert 'Abbaltii Boba’aa' in row
    housing = _item(world['a'], 'housing')  # no Oromo label: falls back to English
    row = html.split(f'id="item-{housing.id}"')[1].split('</tr>')[0]
    assert 'Housing Allowance' in row


def test_display_label_fallbacks(world):
    item = _item(world['a'], 'housing')
    item.name_om = None
    assert item.label('om') == item.name_en
    assert item.label('am') == item.name_am
    assert item.label('en') == item.name_en
    item.name_am = None
    assert item.label('am') == item.name_en
