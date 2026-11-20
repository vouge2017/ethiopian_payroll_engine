import importlib.util
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from payroll_engine import create_app, db
from payroll_engine.backfill import backfill_company
from payroll_engine.models import AuditLog, Company, Employee, EmployeeDeduction, FinalSettlement, TenantQuery, User
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment
from payroll_engine.services.settlement_service import calculate_settlement, create_settlement_record
from payroll_engine.severance import TerminationReason

END = date(2026, 7, 31)
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        from helpers import seed_synthetic_payroll_rule

        seed_synthetic_payroll_rule()
        for model in (Employee, EmployeeDeduction):
            TenantQuery.register_model(model)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def settlement_context(app):
    company = Company(
        name='Synthetic Assignment Settlement Co',
        leave_rate_basis='basic_only',
        leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0),
    )
    db.session.add(company)
    db.session.flush()
    employee = Employee(
        employee_id='SYN-ASSIGN-1',
        name='Synthetic Assignment Worker',
        basic_salary=Decimal('9000.00'),
        allowances=Decimal('3000.00'),
        company_id=company.id,
        start_date=date(2024, 1, 1),
    )
    item = PayItemType(
        company_id=company.id,
        key='test_advance',
        name_en='Test advance',
        classification='deduction',
        calculation_method='fixed',
        tax_treatment='taxable',
    )
    db.session.add_all([employee, item])
    db.session.flush()
    return company, employee, item


def _assignment(employee, company, item, balance='6000.00', **kwargs):
    assignment = PayrollItemAssignment(
        company_id=company.id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        fixed_amount=Decimal(balance),
        custom_label='Synthetic assignment advance',
        tracking_mode='declining',
        total_to_recover=Decimal(balance),
        remaining_balance=Decimal(balance),
        effective_date=date(2024, 1, 1),
        is_active=True,
        **kwargs,
    )
    db.session.add(assignment)
    db.session.flush()
    return assignment


def _legacy_deduction(employee, company, balance='6000.00', **kwargs):
    deduction = EmployeeDeduction(
        employee_id=employee.id,
        company_id=company.id,
        deduction_type='advance',
        label='Synthetic legacy advance',
        amount=Decimal(balance),
        remaining_balance=Decimal(balance),
        total_to_recover=Decimal(balance),
        start_date=date(2024, 1, 1),
        is_active=True,
        **kwargs,
    )
    db.session.add(deduction)
    db.session.flush()
    return deduction


def _login(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True


def test_assignment_deduction_is_in_settlement_preview_and_capped(settlement_context):
    company, employee, item = settlement_context
    assignment = _assignment(employee, company, item)

    result = calculate_settlement(employee, TerminationReason.RESIGNATION, END, company.id, db.session)

    assert result['pending_deductions'] == Decimal('4000.00')
    detail = result['deduction_details'][0]
    assert detail['source'] == 'assignment'
    assert detail['id'] == assignment.id
    assert detail['deduction_id'] == assignment.id
    assert detail['previous_remaining_balance'] == '6000.00'
    assert detail['collected'] == '4000.00'
    assert detail['still_owed'] == '2000.00'
    recovery = result['calculation_details']['deduction_recovery']
    assert recovery['cap_base'] == '12000.00'
    assert recovery['cap_amount'] == '4000.00'


def test_finalization_updates_assignment_and_legacy_rows_by_source_and_reconciles(settlement_context):
    company, employee, item = settlement_context
    legacy = _legacy_deduction(employee, company)
    assignment = _assignment(
        employee, company, item, written_consent_recorded=True, written_consent_amount=Decimal('1000.00')
    )
    assert legacy.id == assignment.id

    user = User(phone='911000879', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.flush()

    settlement = create_settlement_record(employee, TerminationReason.RESIGNATION, END, company.id, user.id, db.session)
    db.session.flush()

    assert legacy.remaining_balance == Decimal('2000.00')
    assert assignment.remaining_balance == Decimal('5000.00')
    assert len(settlement.deduction_details) == 2
    assert [detail['source'] for detail in settlement.deduction_details] == ['legacy', 'assignment']
    assert {(detail['source'], detail['deduction_id']) for detail in settlement.deduction_details} == {
        ('legacy', legacy.id),
        ('assignment', assignment.id),
    }
    for detail in settlement.deduction_details:
        assert Decimal(detail['collected']) + Decimal(detail['still_owed']) == Decimal(
            detail['previous_remaining_balance']
        )
    assert sum(Decimal(detail['collected']) for detail in settlement.deduction_details) == Decimal('5000.00')
    assert sum(Decimal(detail['still_owed']) for detail in settlement.deduction_details) == Decimal('7000.00')
    assert settlement.pending_deductions == Decimal('5000.00')
    assert db.session.query(FinalSettlement).filter_by(company_id=company.id).count() == 1


def test_backfilled_legacy_deduction_is_counted_once(settlement_context):
    company, employee, item = settlement_context
    legacy = _legacy_deduction(employee, company)
    assignment = _assignment(employee, company, item, legacy_source=f'legacy_deduction:{legacy.id}')

    result = calculate_settlement(employee, TerminationReason.RESIGNATION, END, company.id, db.session)

    assert result['pending_deductions'] == Decimal('4000.00')
    assert len(result['deduction_details']) == 1
    assert result['deduction_details'][0]['source'] == 'assignment'
    assert result['deduction_details'][0]['id'] == assignment.id


def test_finalization_rejects_a_concurrently_changed_assignment_balance(settlement_context, monkeypatch):
    from payroll_engine.services import settlement_service

    company, employee, item = settlement_context
    assignment = _assignment(employee, company, item)
    user = User(phone='911000881', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.flush()
    assignment_id = assignment.id
    db.session.commit()
    original_calculate = settlement_service.calculate_settlement

    def changed_balance(*args, **kwargs):
        result = original_calculate(*args, **kwargs)
        assignment.remaining_balance = Decimal('5500.00')
        return result

    monkeypatch.setattr(settlement_service, 'calculate_settlement', changed_balance)
    with pytest.raises(settlement_service.SettlementDeductionChangedError):
        create_settlement_record(employee, TerminationReason.RESIGNATION, END, company.id, user.id, db.session)

    db.session.rollback()
    saved = db.session.query(PayrollItemAssignment).filter_by(id=assignment_id, company_id=company.id).one()
    assert saved.remaining_balance == Decimal('6000.00')
    assert db.session.query(FinalSettlement).filter_by(company_id=company.id).count() == 0


def test_assignment_consent_route_and_employee_deduction_list(settlement_context, app):
    company, employee, item = settlement_context
    assignment = _assignment(employee, company, item)
    user = User(phone='911000880', company_id=company.id, role='accountant')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()

    client = app.test_client()
    _login(client, user)
    page = client.get(f'/employees/{employee.id}')
    assert page.status_code == 200
    assert f'/assignments/{assignment.id}/deduction-consent' in page.get_data(as_text=True)
    assert 'Written consent recorded' in page.get_data(as_text=True)

    response = client.post(
        f'/assignments/{assignment.id}/deduction-consent',
        data={
            'written_consent_recorded': 'on',
            'written_consent_date': '2026-11-19',
            'written_consent_reference': 'Synthetic signed consent TEST-78',
            'written_consent_amount': '2000.00',
        },
    )

    assert response.status_code == 302
    db.session.refresh(assignment)
    assert assignment.written_consent_recorded is True
    assert assignment.written_consent_date == date(2026, 11, 19)
    assert assignment.written_consent_reference == 'Synthetic signed consent TEST-78'
    assert assignment.written_consent_amount == Decimal('2000.00')
    assert assignment.written_consent_recorded_by == user.id
    log = AuditLog.query.filter_by(
        company_id=company.id,
        user_id=user.id,
        action='assignment_deduction_written_consent_updated',
    ).one()
    assert log.details['assignment_id'] == assignment.id
    assert log.details['previous']['recorded'] is False
    assert log.details['current']['reference'] == 'Synthetic signed consent TEST-78'

    result = calculate_settlement(employee, TerminationReason.RESIGNATION, END, company.id, db.session)
    detail = result['deduction_details'][0]
    assert detail['consent_exempt'] is True
    assert detail['consent_collected'] == '2000.00'
    assert detail['collected'] == '6000.00'
    assert detail['still_owed'] == '0.00'

    preview = client.post(
        f'/employees/{employee.id}/terminate',
        data={
            'action': 'preview',
            'termination_reason': 'resignation',
            'end_date': END.isoformat(),
        },
    )
    preview_html = preview.get_data(as_text=True)
    assert preview.status_code == 200
    assert 'assignment #1' in preview_html
    assert 'collected ETB 6000.00' in preview_html
    assert 'One-third cap ETB 4000.00' in preview_html
    assert 'wage basis pending adviser confirmation' in preview_html


def test_assignment_consent_fields_have_safe_defaults_and_money_precision():
    columns = PayrollItemAssignment.__table__.columns

    assert columns['written_consent_recorded'].nullable is False
    assert columns['written_consent_recorded'].default.arg is False
    assert str(columns['written_consent_recorded'].server_default.arg).lower() in {'false', '0'}
    assert columns['written_consent_date'].nullable is True
    assert columns['written_consent_reference'].type.length == 200
    assert (columns['written_consent_amount'].type.precision, columns['written_consent_amount'].type.scale) == (12, 2)
    assert columns['written_consent_recorded_by'].nullable is True


def test_backfill_copies_existing_legacy_consent_to_assignment(settlement_context):
    company, employee, _item = settlement_context
    legacy = _legacy_deduction(
        employee,
        company,
        written_consent_recorded=True,
        written_consent_date=date(2026, 11, 18),
        written_consent_reference='Synthetic prior consent TEST-78',
        written_consent_amount=Decimal('2500.00'),
    )

    result = backfill_company(company.id)

    assert result['deductions_created'] == 1
    assignment = PayrollItemAssignment.query.filter_by(
        company_id=company.id,
        legacy_source=f'legacy_deduction:{legacy.id}',
    ).one()
    assert assignment.written_consent_recorded is True
    assert assignment.written_consent_date == date(2026, 11, 18)
    assert assignment.written_consent_reference == 'Synthetic prior consent TEST-78'
    assert assignment.written_consent_amount == Decimal('2500.00')
    assert EmployeeDeduction.query.filter_by(id=legacy.id, company_id=company.id).one() is legacy


def test_assignment_consent_migration_round_trips_and_copies_existing_legacy_consent_on_sqlite():
    migration_path = REPO / 'migrations/versions/l20261119a02_assignment_deduction_consent.py'
    spec = importlib.util.spec_from_file_location('assignment_deduction_consent_migration', migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        metadata = sa.MetaData()
        sa.Table('user', metadata, sa.Column('id', sa.Integer, primary_key=True))
        sa.Table(
            'employee_deduction',
            metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('written_consent_recorded', sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column('written_consent_date', sa.Date),
            sa.Column('written_consent_reference', sa.String(200)),
            sa.Column('written_consent_amount', sa.Numeric(12, 2)),
            sa.Column('written_consent_recorded_by', sa.Integer, sa.ForeignKey('user.id', ondelete='SET NULL')),
        )
        sa.Table(
            'payroll_item_assignment',
            metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('legacy_source', sa.String(60)),
        )
        metadata.create_all(connection)
        connection.execute(sa.text('INSERT INTO user (id) VALUES (9)'))
        connection.execute(
            sa.text(
                """
                INSERT INTO employee_deduction
                    (id, written_consent_recorded, written_consent_date,
                     written_consent_reference, written_consent_amount,
                     written_consent_recorded_by)
                VALUES (1, 1, '2026-11-18', 'Synthetic prior consent TEST-78', 2500.00, 9)
                """
            )
        )
        connection.execute(
            sa.text(
                'INSERT INTO payroll_item_assignment (id, legacy_source) '
                "VALUES (1, 'legacy_deduction:1'), (2, 'manual-assignment')"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.upgrade()

        columns = {column['name'] for column in sa.inspect(connection).get_columns('payroll_item_assignment')}
        assert {
            'written_consent_recorded',
            'written_consent_date',
            'written_consent_reference',
            'written_consent_amount',
            'written_consent_recorded_by',
        } <= columns
        copied = connection.execute(
            sa.text(
                """
                SELECT written_consent_recorded, written_consent_date,
                       written_consent_reference, written_consent_amount,
                       written_consent_recorded_by
                FROM payroll_item_assignment WHERE id = 1
                """
            )
        ).one()
        assert bool(copied[0]) is True
        assert str(copied[1]) == '2026-11-18'
        assert copied[2] == 'Synthetic prior consent TEST-78'
        assert Decimal(str(copied[3])) == Decimal('2500.00')
        assert copied[4] == 9
        assert connection.execute(
            sa.text('SELECT written_consent_recorded FROM payroll_item_assignment WHERE id = 2')
        ).scalar() in (False, 0)

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        columns = {column['name'] for column in sa.inspect(connection).get_columns('payroll_item_assignment')}
        assert columns == {'id', 'legacy_source'}
        assert (
            connection.execute(
                sa.text('SELECT written_consent_reference FROM employee_deduction WHERE id = 1')
            ).scalar()
            == 'Synthetic prior consent TEST-78'
        )
    engine.dispose()
