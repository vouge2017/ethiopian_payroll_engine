import importlib.util
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, EmployeeDeduction, FinalSettlement, TenantQuery, User
from payroll_engine.services.settlement_service import (
    SettlementDeductionChangedError,
    calculate_settlement,
    create_settlement_record,
)
from payroll_engine.severance import TerminationReason

END = date(2026, 7, 31)
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:')
    with app.app_context():
        db.create_all()
        from helpers import seed_synthetic_payroll_rule

        seed_synthetic_payroll_rule()
        for model in (Employee, EmployeeDeduction):
            TenantQuery.register_model(model)
        yield app
        db.drop_all()


@pytest.fixture
def settlement_context(app):
    company = Company(
        name='Synthetic Deduction Cap Co',
        leave_rate_basis='basic_only',
        leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0),
    )
    db.session.add(company)
    db.session.flush()
    employee = Employee(
        employee_id='SYN-CAP-1',
        name='Synthetic Cap Worker',
        basic_salary=Decimal('9000.00'),
        allowances=Decimal('3000.00'),
        company_id=company.id,
        start_date=date(2024, 1, 1),
    )
    db.session.add(employee)
    db.session.flush()
    return company, employee


def _deduction(employee, company, balance, *, consent=False, consent_amount=None):
    deduction = EmployeeDeduction(
        employee_id=employee.id,
        company_id=company.id,
        deduction_type='advance',
        label=f'Synthetic advance {balance}',
        amount=Decimal(balance),
        remaining_balance=Decimal(balance),
        start_date=date(2024, 1, 1),
        is_active=True,
    )
    db.session.add(deduction)
    db.session.flush()
    deduction.written_consent_recorded = consent
    deduction.written_consent_amount = None if consent_amount is None else Decimal(consent_amount)
    return deduction


def _calculate(company, employee):
    return calculate_settlement(
        employee,
        TerminationReason.RESIGNATION,
        END,
        company.id,
        db.session,
    )


def test_pending_deductions_are_capped_at_one_third_of_monthly_wage(settlement_context):
    company, employee = settlement_context
    _deduction(employee, company, '6000.00')

    result = _calculate(company, employee)

    assert result['pending_deductions'] == Decimal('4000.00')
    recovery = result['calculation_details']['deduction_recovery']
    assert recovery['cap_base'] == '12000.00'
    assert recovery['cap_amount'] == '4000.00'
    assert recovery['collected_under_cap'] == '4000.00'
    assert recovery['previous_remaining_balance_total'] == '6000.00'
    assert recovery['collected_total'] == '4000.00'
    assert recovery['still_owed_total'] == '2000.00'
    detail = result['deduction_details'][0]
    assert detail['type'] == 'advance'
    assert detail['label'] == 'Synthetic advance 6000.00'
    assert detail['previous_remaining_balance'] == '6000.00'
    assert detail['collected'] == '4000.00'
    assert detail['still_owed'] == '2000.00'
    assert detail['consent_exempt'] is False


def test_recorded_full_consent_is_exempt_from_the_cap(settlement_context):
    company, employee = settlement_context
    _deduction(employee, company, '6000.00', consent=True)

    result = _calculate(company, employee)

    assert result['pending_deductions'] == Decimal('6000.00')
    assert result['deduction_details'][0]['collected'] == '6000.00'
    assert result['deduction_details'][0]['still_owed'] == '0.00'
    assert result['deduction_details'][0]['consent_exempt'] is True
    assert result['calculation_details']['deduction_recovery']['collected_under_cap'] == '0.00'


def test_partial_collection_reconciles_to_previous_balance(settlement_context):
    company, employee = settlement_context
    deduction = _deduction(employee, company, '6000.00')

    result = _calculate(company, employee)
    detail = result['deduction_details'][0]

    assert Decimal(detail['collected']) + Decimal(detail['still_owed']) == Decimal(detail['previous_remaining_balance'])
    assert detail['still_owed'] == '2000.00'
    assert deduction.remaining_balance == Decimal('6000.00')


def test_finalization_sets_balance_to_uncollected_amount(settlement_context):
    company, employee = settlement_context
    deduction = _deduction(employee, company, '6000.00')
    user = User(phone='911000874', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.flush()

    settlement = create_settlement_record(
        employee,
        TerminationReason.RESIGNATION,
        END,
        company.id,
        user.id,
        db.session,
    )

    assert deduction.remaining_balance == Decimal('2000.00')
    detail = settlement.deduction_details[0]
    assert Decimal(detail['collected']) + Decimal(detail['still_owed']) == Decimal(detail['previous_remaining_balance'])


def test_finalization_rejects_a_concurrently_changed_balance(settlement_context, monkeypatch):
    from payroll_engine.services import settlement_service

    company, employee = settlement_context
    deduction = _deduction(employee, company, '6000.00')
    user = User(phone='911000875', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.flush()
    deduction_id = deduction.id
    db.session.commit()
    original_calculate = settlement_service.calculate_settlement

    def changed_balance(*args, **kwargs):
        result = original_calculate(*args, **kwargs)
        deduction.remaining_balance = Decimal('5500.00')
        return result

    monkeypatch.setattr(settlement_service, 'calculate_settlement', changed_balance)
    with pytest.raises(SettlementDeductionChangedError):
        create_settlement_record(
            employee,
            TerminationReason.RESIGNATION,
            END,
            company.id,
            user.id,
            db.session,
        )

    db.session.rollback()
    saved_deduction = db.session.query(EmployeeDeduction).filter_by(id=deduction_id).one()
    assert saved_deduction.remaining_balance == Decimal('6000.00')
    assert db.session.query(FinalSettlement).filter_by(company_id=company.id).count() == 0


def test_zero_wage_leaves_unconsented_deduction_fully_owed(settlement_context):
    company, employee = settlement_context
    employee.basic_salary = Decimal('0.00')
    employee.allowances = Decimal('0.00')
    _deduction(employee, company, '500.00')

    result = _calculate(company, employee)

    assert result['pending_deductions'] == Decimal('0.00')
    assert result['deduction_details'][0]['collected'] == '0.00'
    assert result['deduction_details'][0]['still_owed'] == '500.00'
    assert result['calculation_details']['deduction_recovery']['cap_base'] == '0.00'


def test_deductions_share_cap_in_order_and_crossing_deduction_is_partial(settlement_context):
    company, employee = settlement_context
    _deduction(employee, company, '2500.00')
    _deduction(employee, company, '2500.00')
    _deduction(employee, company, '5000.00')

    result = _calculate(company, employee)

    assert [detail['collected'] for detail in result['deduction_details']] == ['2500.00', '1500.00', '0.00']
    assert [detail['still_owed'] for detail in result['deduction_details']] == ['0.00', '1000.00', '5000.00']
    recovery = result['calculation_details']['deduction_recovery']
    assert recovery['collected_under_cap'] == '4000.00'
    assert recovery['previous_remaining_balance_total'] == '10000.00'
    assert recovery['collected_total'] == '4000.00'
    assert recovery['still_owed_total'] == '6000.00'


def test_partial_consent_exempts_only_its_amount_and_remainder_uses_cap(settlement_context):
    company, employee = settlement_context
    _deduction(employee, company, '6000.00', consent=True, consent_amount='2000.00')

    result = _calculate(company, employee)

    assert result['pending_deductions'] == Decimal('6000.00')
    detail = result['deduction_details'][0]
    assert detail['collected'] == '6000.00'
    assert detail['consent_exempt'] is True
    assert result['calculation_details']['deduction_recovery']['collected_under_cap'] == '4000.00'


def test_one_third_cap_rounds_once_half_up_to_cents(settlement_context):
    company, employee = settlement_context
    employee.basic_salary = Decimal('10000.01')
    employee.allowances = Decimal('0.00')
    _deduction(employee, company, '3333.35')

    result = _calculate(company, employee)

    assert result['deduction_details'][0]['collected'] == '3333.34'
    assert result['deduction_details'][0]['still_owed'] == '0.01'
    assert result['calculation_details']['deduction_recovery']['cap_amount'] == '3333.34'


def test_unconsented_recovery_cannot_make_net_settlement_negative(settlement_context):
    company, employee = settlement_context
    _deduction(employee, company, '6000.00')

    result = calculate_settlement(
        employee,
        TerminationReason.RESIGNATION,
        date(2026, 7, 5),
        company.id,
        db.session,
    )

    assert result['net_final_payment'] >= Decimal('0.00')


def test_consent_fields_are_mapped_and_have_safe_defaults():
    columns = EmployeeDeduction.__table__.columns

    assert columns['written_consent_recorded'].nullable is False
    assert columns['written_consent_recorded'].default.arg is False
    assert columns['written_consent_date'].nullable is True
    assert columns['written_consent_reference'].type.length == 200
    assert (columns['written_consent_amount'].type.precision, columns['written_consent_amount'].type.scale) == (12, 2)
    assert columns['written_consent_recorded_by'].nullable is True


def test_consent_editor_records_fields_and_logged_in_user(app, settlement_context):
    company, employee = settlement_context
    user = User(phone='911000873', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    deduction = _deduction(employee, company, '6000.00')
    db.session.commit()

    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    deduction_page = client.get(f'/employees/{employee.id}')
    assert deduction_page.status_code == 200
    assert 'Not recorded' in deduction_page.get_data(as_text=True)
    response = client.post(
        f'/deductions/{deduction.id}/consent',
        data={
            'written_consent_recorded': 'on',
            'written_consent_date': '2026-11-19',
            'written_consent_reference': 'Synthetic signed consent TEST-73',
            'written_consent_amount': '2000.00',
        },
    )

    assert response.status_code == 302
    db.session.refresh(deduction)
    assert deduction.written_consent_recorded is True
    assert deduction.written_consent_date == date(2026, 11, 19)
    assert deduction.written_consent_reference == 'Synthetic signed consent TEST-73'
    assert deduction.written_consent_amount == Decimal('2000.00')
    assert deduction.written_consent_recorded_by == user.id
    deduction_page = client.get(f'/employees/{employee.id}')
    assert 'Synthetic signed consent TEST-73' in deduction_page.get_data(as_text=True)


def test_consent_migration_round_trips_on_sqlite():
    migration_path = REPO / 'migrations/versions/l20261119a01_settlement_deduction_written_consent.py'
    spec = importlib.util.spec_from_file_location('settlement_consent_migration', migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        metadata = sa.MetaData()
        sa.Table('user', metadata, sa.Column('id', sa.Integer, primary_key=True))
        sa.Table('employee_deduction', metadata, sa.Column('id', sa.Integer, primary_key=True))
        metadata.create_all(connection)
        connection.execute(sa.text('INSERT INTO employee_deduction (id) VALUES (1)'))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            columns = {column['name'] for column in sa.inspect(connection).get_columns('employee_deduction')}
            assert {
                'written_consent_recorded',
                'written_consent_date',
                'written_consent_reference',
                'written_consent_amount',
                'written_consent_recorded_by',
            } <= columns
            assert connection.execute(
                sa.text('SELECT written_consent_recorded FROM employee_deduction WHERE id = 1')
            ).scalar() in (False, 0)
            migration.downgrade()
            columns = {column['name'] for column in sa.inspect(connection).get_columns('employee_deduction')}
            assert not any(name.startswith('written_consent_') for name in columns)
    engine.dispose()
