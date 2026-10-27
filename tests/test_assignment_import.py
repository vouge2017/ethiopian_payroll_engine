"""Bulk import of employee pay-item assignments (catalog PR 5).

Dry-run preview writes nothing; apply is all-or-nothing and re-validates;
re-importing the same file is a no-op; row-level errors; employee ID
matching that rejects ambiguous rows (0001 vs 1, numeric Excel cells,
duplicates, deleted employees); CSV and .xlsx; the JSON bulk employee import
mapping per-item allowances to catalog assignments.
"""

import io
import json
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
    User,
    UserCompany,
)
from payroll_engine.services import assignment_import as ai
from payroll_engine.services import employee_assignments as ea

PASSWORD = 'Test1234!'
HEADER = 'employee_id,item_key,amount,start_date,end_date,amount_type,label\n'


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


def _employee(company_id, code, salary='10000', allowances='0', deleted=False):
    emp = Employee(
        company_id=company_id,
        employee_id=code,
        name=f'Emp {code}',
        phone='0912345670',
        basic_salary=Decimal(salary),
        allowances=Decimal(allowances),
        is_deleted=deleted,
    )
    db.session.add(emp)
    db.session.commit()
    return emp


@pytest.fixture
def world(app):
    a = _company('Import A PLC')
    b = _company('Import B PLC')
    w = {
        'a': a.id,
        'b': b.id,
        'owner': _user(a, '911300001', 'owner'),
        'accountant': _user(a, '911300002', 'accountant'),
    }
    w['employee_user'] = _user(a, '911300003', 'employee')
    for code in ('EMP001', 'EMP002', '0007', 'X9'):
        w[code] = _employee(a.id, code)
    _employee(b.id, 'EMP001')
    return w


def _login(app, user):
    client = app.test_client()
    resp = client.post('/auth/login', data={'login_id': user.phone, 'password': PASSWORD})
    assert resp.status_code == 302
    return client


def _csv(body):
    return (io.BytesIO((HEADER + body).encode('utf-8')), 'assignments.csv')


def _rows(company_id, body, *, confirm_legacy=False):
    class _Upload:
        filename = 'a.csv'

        def __init__(self, text):
            self._text = text

        def read(self):
            return self._text.encode('utf-8')

    headers, rows = ai.read_rows(_Upload(HEADER + body))
    return headers, rows


def _plan(company_id, body, **kw):
    headers, rows = _rows(company_id, body)
    return ai.plan_import(company_id, headers, rows, **kw)


def _count(company_id):
    return PayrollItemAssignment.query.filter_by(company_id=company_id).count()


GOOD = (
    'EMP001,transport,1500,2026-11-01,,fixed,\n'
    'EMP001,loan,1000.50,2026-11-01,2027-04-30,,Staff loan\n'
    'EMP002,housing,12.5,2026-11-01,,percent_of_basic,\n'
    '0007,cost_sharing,10,,,percent_of_net,MoE\n'
)


def test_preview_writes_nothing_then_apply_then_reimport_is_noop(app, world):
    client = _login(app, world['owner'])
    resp = client.post('/employees/pay-items/import', data={'file': _csv(GOOD)}, content_type='multipart/form-data')
    assert resp.status_code == 200
    assert b'data-testid="import-preview"' in resp.data and b'4 to add' in resp.data
    assert _count(world['a']) == 0
    payload = ai.rows_to_payload(_rows(world['a'], GOOD)[1])
    resp = client.post('/employees/pay-items/import', data={'action': 'apply', 'payload': json.dumps(payload)})
    assert resp.status_code == 302
    assert _count(world['a']) == 4
    rows = {
        (a.employee.employee_id, a.item_type.key): a
        for a in PayrollItemAssignment.query.filter_by(company_id=world['a'])
    }
    assert rows[('EMP001', 'loan')].fixed_amount == Decimal('1000.50')
    assert rows[('EMP001', 'loan')].end_date == date(2027, 4, 30)
    assert rows[('EMP002', 'housing')].percent_of_basic == Decimal('12.50')
    assert rows[('0007', 'cost_sharing')].percent_of_net == Decimal('10.00')
    assert rows[('0007', 'cost_sharing')].effective_date is None
    created = AuditLog.query.filter_by(company_id=world['a'], action='pay_item_assignment_created').all()
    assert len(created) == 4 and {log.details['source'] for log in created} == {'import'}
    assert AuditLog.query.filter_by(company_id=world['a'], action='pay_item_assignments_imported').count() == 1
    # Same file again: everything unchanged, nothing to apply.
    plan = _plan(world['a'], GOOD)
    assert plan.counts == {'create': 0, 'update': 0, 'unchanged': 4, 'error': 0}
    assert not plan.can_apply
    headers, again = _rows(world['a'], GOOD)
    ai.apply_import(world['a'], None, headers, again)
    db.session.commit()
    assert _count(world['a']) == 4


def test_unused_row_updated_used_row_refused(app, world):
    from payroll_engine.models import PayrollRun, Payslip

    cid = world['a']
    headers, rows = _rows(cid, 'EMP001,transport,1500,2026-11-01,,,\nEMP002,transport,900,2026-11-01,,,\n')
    ai.apply_import(cid, None, headers, rows)
    db.session.commit()
    used = PayrollItemAssignment.query.filter_by(company_id=cid, employee_id=world['EMP002'].id).one()
    run = PayrollRun(company_id=cid, run_date=date(2026, 11, 1), status='completed', source='spreadsheet')
    db.session.add(run)
    db.session.flush()
    db.session.add(
        Payslip(
            payroll_run_id=run.id,
            employee_id=world['EMP002'].id,
            company_id=cid,
            gross_salary=Decimal('900'),
            tax=Decimal('0'),
            employee_pension=Decimal('0'),
            employer_pension=Decimal('0'),
            net_pay=Decimal('900'),
            line_items=[{'item_key': 'transport', 'assignment_id': used.id, 'earned_amount': '900.00'}],
        )
    )
    db.session.commit()
    plan = _plan(cid, 'EMP001,transport,1600,2026-11-01,,,\nEMP002,transport,950,2026-11-01,,,\n')
    by_row = {r.number: r for r in plan.rows}
    assert by_row[2].action == 'update' and by_row[2].ok
    assert 'already used in approved payroll' in by_row[3].errors[0]
    assert not plan.can_apply
    # All or nothing: the valid update is not written either.
    headers, rows = _rows(cid, 'EMP001,transport,1600,2026-11-01,,,\nEMP002,transport,950,2026-11-01,,,\n')
    ai.apply_import(cid, None, headers, rows)
    db.session.rollback()
    emp1 = PayrollItemAssignment.query.filter_by(company_id=cid, employee_id=world['EMP001'].id).one()
    assert emp1.fixed_amount == Decimal('1500.00')
    # Only the unused one: updated in place.
    headers, rows = _rows(cid, 'EMP001,transport,1600,2026-11-01,,,\n')
    plan = ai.apply_import(cid, None, headers, rows)
    db.session.commit()
    assert plan.counts['update'] == 1
    db.session.refresh(emp1)
    assert emp1.fixed_amount == Decimal('1600.00')


@pytest.mark.parametrize(
    ('body', 'message'),
    [
        ('7,transport,100,,,,\n', 'Did you mean 0007'),
        ('emp001,transport,100,,,,\n', 'Did you mean EMP001'),
        ('EMP1,transport,100,,,,\n', 'Did you mean EMP001'),
        ('NOPE,transport,100,,,,\n', 'No employee has the ID "NOPE"'),
        ('GONE,transport,100,,,,\n', 'is deleted'),
        (',transport,100,,,,\n', 'employee_id is empty'),
        ('EMP001,,100,,,,\n', 'item_key is empty'),
        ('EMP001,nonexistent,100,,,,\n', 'not a pay item in your company catalog'),
        ('EMP001,income_tax,100,,,,\n', 'calculated by the system'),
        ('EMP001,basic_salary,100,,,,\n', 'calculated by the system'),
        ('EMP001,transport,,,,,\n', 'Amount is required'),
        ('EMP001,transport,1e3x,,,,\n', 'not a number'),
        ('EMP001,transport,-4,,,,\n', 'more than zero'),
        ('EMP001,transport,100,2026-13-01,,,\n', 'YYYY-MM-DD'),
        ('EMP001,transport,100,2026-11-01,2026-10-01,,\n', 'before the start'),
        ('EMP001,transport,100,,,percent_of_net,\n', 'not an amount type'),
        ('EMP001,loan,100,,,,\n', 'needs a label'),
        ('EMP001,transport,100,,,,\nEMP001,transport,200,,,,\n', 'Same employee, item and start date as row'),
        ('EMP001,transport,100,2026-01-01,2026-12-31,,\nEMP001,transport,200,2026-06-01,,,\n', 'Dates overlap row'),
    ],
)
def test_row_errors(app, world, body, message):
    _employee(world['a'], 'GONE', deleted=True)
    plan = _plan(world['a'], body)
    errors = [e for r in plan.rows for e in r.errors]
    assert any(message in e for e in errors), errors
    assert not plan.can_apply


def test_other_company_ids_and_items_never_match(app, world):
    # Company B's EMP001 exists; importing as company A only ever touches A's EMP001.
    headers, rows = _rows(world['a'], 'EMP001,transport,100,,,,\n')
    ai.apply_import(world['a'], None, headers, rows)
    db.session.commit()
    [a] = PayrollItemAssignment.query.filter_by(company_id=world['a']).all()
    assert a.employee.company_id == world['a'] and a.item_type.company_id == world['a']
    assert _count(world['b']) == 0


def test_numeric_excel_cell_with_colliding_ids_is_ambiguous(app, world):
    openpyxl = pytest.importorskip('openpyxl')
    _employee(world['a'], '7')  # now "7" and "0007" both exist
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Employee ID', 'Item Key', 'Amount', 'Start Date'])
    ws.append([7, 'transport', 1500, date(2026, 11, 1)])  # numeric cell: zeros may be lost
    ws.append(['7', 'housing', '800', '2026-11-01'])  # text cell: exact match is fine
    ws.append(['0007', 'housing', 800.5, '2026-11-01'])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    class _Upload:
        filename = 'a.xlsx'
        stream = buf

    headers, rows = ai.read_rows(_Upload())
    assert rows[0].numeric_id and not rows[1].numeric_id
    plan = ai.plan_import(world['a'], headers, rows)
    by_row = {r.number: r for r in plan.rows}
    assert 'more than one employee matches it (0007, 7)' in by_row[2].errors[0]
    assert by_row[3].ok and by_row[3].employee.employee_id == '7'
    assert by_row[4].ok and by_row[4].employee.employee_id == '0007' and by_row[4].value == Decimal('800.50')


def test_legacy_allowance_rows_need_confirmation(app, world):
    legacy = _employee(world['a'], 'LEG', allowances='2500')
    assert legacy.allowances == Decimal('2500')
    plan = _plan(world['a'], 'LEG,transport,1000,,,,\nLEG,housing,1500,,,,\n')
    assert 'legacy allowances of ETB 2,500.00' in plan.rows[0].errors[0]
    assert plan.rows[1].ok  # one message per employee
    plan = _plan(world['a'], 'LEG,transport,1000,,,,\nLEG,housing,1500,,,,\n', confirm_legacy=True)
    assert plan.can_apply


def test_missing_columns_and_bad_files(app, world):
    class _Upload:
        def __init__(self, name, data):
            self.filename = name
            self._data = data

        def read(self):
            return self._data

    headers, rows = ai.read_rows(_Upload('a.csv', b'employee,amount\nEMP001,5\n'))
    plan = ai.plan_import(world['a'], headers, rows)
    assert plan.header_errors and 'item_key' in plan.header_errors[0]
    with pytest.raises(ai.ImportFileError, match=r'\.csv or \.xlsx'):
        ai.read_rows(_Upload('a.txt', b''))
    with pytest.raises(ai.ImportFileError, match='UTF-8'):
        ai.read_rows(_Upload('a.csv', 'employee_id\n\xe9'.encode('latin-1')))
    big = HEADER + ''.join(f'EMP001,transport,1,{2000 + i}-01-01,{2000 + i}-01-02,,\n' for i in range(ai.MAX_ROWS + 1))
    with pytest.raises(ai.ImportFileError, match='limit'):
        ai.read_rows(_Upload('a.csv', big.encode()))


def test_import_page_roles_and_template(app, world):
    for role in ('owner', 'accountant'):
        client = _login(app, world[role])
        assert client.get('/employees/pay-items/import').status_code == 200
        tpl = client.get('/employees/pay-items/import/template.csv')
        assert tpl.status_code == 200 and b'employee_id,item_key,amount' in tpl.data
    emp_client = _login(app, world['employee_user'])
    assert emp_client.post('/employees/pay-items/import', data={'file': _csv(GOOD)}).status_code == 403
    assert _count(world['a']) == 0


def test_tampered_payload_is_revalidated(app, world):
    client = _login(app, world['owner'])
    payload = [{'n': 2, 'v': {'employee_id': 'EMP001', 'item_key': 'income_tax', 'amount': '5'}, 'num': False}]
    resp = client.post('/employees/pay-items/import', data={'action': 'apply', 'payload': json.dumps(payload)})
    assert resp.status_code == 400 and b'Nothing was imported' in resp.data
    assert _count(world['a']) == 0
    resp = client.post('/employees/pay-items/import', data={'action': 'apply', 'payload': '{"x": 1}'})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# JSON bulk employee import: per-item allowances become catalog assignments
# ---------------------------------------------------------------------------


def test_api_bulk_import_maps_pay_items_to_assignments(app, world):
    client = _login(app, world['owner'])
    body = {
        'employees': [
            {
                'employee_id': 'NEW1',
                'name': 'New One',
                'basic_salary': 9000,
                'pay_items': [
                    {'item_key': 'transport', 'amount': '1500', 'start_date': '2026-11-01'},
                    {'item_key': 'loan', 'amount': '300', 'label': 'Loan'},
                ],
            },
            {
                'employee_id': 'NEW2',
                'name': 'Bad Item',
                'basic_salary': 9000,
                'pay_items': [{'item_key': 'transport', 'amount': '1'}, {'item_key': 'income_tax', 'amount': '5'}],
            },
            {
                'employee_id': 'NEW3',
                'name': 'Both',
                'basic_salary': 9000,
                'allowances': 1000,
                'pay_items': [{'item_key': 'housing', 'amount': '500'}],
            },
            {'employee_id': 'NEW4', 'name': 'Plain', 'basic_salary': 9000},
        ]
    }
    resp = client.post('/api/v1/employees/bulk', json=body)
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data['imported'] == 2
    errors = {e['row']: e['error'] for e in data['errors']}
    assert 'pay_items[2]' in errors[2] and 'calculated by the system' in errors[2]
    assert 'not both' in errors[3]
    codes = {e.employee_id for e in Employee.query.filter_by(company_id=world['a']).all()}
    assert {'NEW1', 'NEW4'} <= codes and not {'NEW2', 'NEW3'} & codes
    new1 = Employee.query.filter_by(company_id=world['a'], employee_id='NEW1').one()
    rows = sorted((r.item.key, str(r.value)) for r in ea.employee_view(world['a'], new1))
    assert rows == [('loan', '300.00'), ('transport', '1500.00')]
    assert PayItemType.query.filter_by(company_id=None, key='income_tax').one()
