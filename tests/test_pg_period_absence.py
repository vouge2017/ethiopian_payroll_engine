"""Real migrated PostgreSQL evidence for absence month boundaries."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from test_pg_deduction_identity import PG_URL, approve

from payroll_engine import db
from payroll_engine.models import EmployeeDeduction, Leave
from payroll_engine.models_payroll_elements import PayrollItemAssignment

pytest_plugins = ('test_pg_deduction_identity',)

pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


@pytest.mark.parametrize(
    'approval_day,expected_days',
    [(date(2026, 10, 1), 0), (date(2026, 10, 2), 1), (date(2026, 10, 3), 2), (date(2026, 9, 15), 2)],
)
def test_absence_month_boundary_persists_once(dataset, monkeypatch, approval_day, expected_days):
    app, ids, engine = dataset

    class ApprovalDate(date):
        @classmethod
        def today(cls):
            return approval_day

    monkeypatch.setattr('payroll_engine.services.payroll_service.date', ApprovalDate)
    with app.app_context():
        # Isolate leave from the fixture's independent deduction ledgers.
        EmployeeDeduction.query.filter_by(company_id=ids['company']).delete()
        PayrollItemAssignment.query.filter_by(company_id=ids['company']).delete()
        db.session.execute(
            text('UPDATE payroll_run SET run_date=:day WHERE id=:id'), {'day': approval_day, 'id': ids['run']}
        )
        db.session.add(
            Leave(
                company_id=ids['company'],
                employee_id=ids['employee'],
                leave_type='unpaid',
                status='approved',
                days_requested=2,
                start_date=approval_day - timedelta(days=2),
                end_date=approval_day - timedelta(days=1),
            )
        )
        db.session.commit()
    try:
        assert approve(app, ids).success
        assert not approve(app, ids).success
        with engine.connect() as conn:
            row = conn.execute(
                text('SELECT net_pay, unpaid_leave_reduction FROM payslip WHERE payroll_run_id=:id'), {'id': ids['run']}
            ).one()
            reduction = (Decimal('10000') / 30 * expected_days).quantize(Decimal('0.01'))
            assert row == (Decimal('10000') - reduction, reduction)
            assert (
                conn.execute(
                    text("SELECT count(*) FROM audit_log WHERE company_id=:id AND action='payroll_run_completed'"),
                    {'id': ids['company']},
                ).scalar_one()
                == 1
            )
    finally:
        with engine.begin() as conn:
            conn.execute(text('DELETE FROM leave WHERE company_id=:id'), {'id': ids['company']})
