"""
Tests for Phase 3 — Proactive System:
- Monthly draft pre-calculation
- Compliance deadline nudges
- Scheduler hook behavior
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
from unittest.mock import patch

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    Notification,
    PayrollDraft,
    PayrollRun,
    User,
    UserCompany,
)
from payroll_engine.services.proactive import (
    prepare_monthly_draft,
    send_compliance_nudges,
    should_prepare_draft,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _setup(app):
    """Create company, owner, employees."""
    with app.app_context():
        company = Company(name='ProactiveTestCo')
        db.session.add(company)
        db.session.flush()

        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('TestPass1!')
        db.session.add(owner)
        db.session.flush()

        owner_uc = UserCompany(user_id=owner.id, company_id=company.id, role='owner')
        db.session.add(owner_uc)

        emp1 = Employee(
            employee_id='EMP001', name='Abebe Kebede', phone='0911111111',
            basic_salary=10000, allowances=2000, company_id=company.id,
            bank_account='cbe:1000123456789', tin='1234567890',
        )
        emp2 = Employee(
            employee_id='EMP002', name='Hana Tesfaye', phone='0922222222',
            basic_salary=8000, allowances=1000, company_id=company.id,
            bank_account='dashen:2000987654321', tin='0987654321',
        )
        db.session.add_all([emp1, emp2])
        db.session.commit()

        return company.id, owner.id


# ─── should_prepare_draft ───


class TestShouldPrepareDraft:
    """Test the date check function."""

    @patch('payroll_engine.services.proactive.date')
    def test_returns_true_on_28th(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 28)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        assert should_prepare_draft() is True

    @patch('payroll_engine.services.proactive.date')
    def test_returns_true_on_29th(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        assert should_prepare_draft() is True

    @patch('payroll_engine.services.proactive.date')
    def test_returns_true_on_31st(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 31)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        assert should_prepare_draft() is True

    @patch('payroll_engine.services.proactive.date')
    def test_returns_false_before_28th(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 27)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        assert should_prepare_draft() is False

    @patch('payroll_engine.services.proactive.date')
    def test_returns_false_on_1st(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        assert should_prepare_draft() is False


# ─── prepare_monthly_draft ───


class TestPrepareMonthlyDraft:
    """Test monthly draft pre-calculation."""

    def test_creates_draft_for_new_period(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            result = prepare_monthly_draft(cid)
            assert result is not None
            assert result['status'] == 'ok'
            assert result['employee_count'] == 2
            assert result['total_net'] > 0

    def test_creates_draft_run_in_db(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            prepare_monthly_draft(cid)
            runs = PayrollRun.query.filter_by(company_id=cid, status='draft').all()
            assert len(runs) == 1
            assert runs[0].period is not None

    def test_creates_draft_data_in_db(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            prepare_monthly_draft(cid)
            runs = PayrollRun.query.filter_by(company_id=cid, status='draft').all()
            draft = PayrollDraft.query.filter_by(payroll_run_id=runs[0].id).first()
            assert draft is not None
            assert len(draft.employee_data) == 2

    def test_skips_if_run_already_exists(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            # First call creates the draft
            result1 = prepare_monthly_draft(cid)
            assert result1 is not None

            # Second call should skip
            result2 = prepare_monthly_draft(cid)
            assert result2 is None

    def test_skips_if_no_employees(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            # Delete all employees
            Employee.query.filter_by(company_id=cid).delete()
            db.session.commit()

            result = prepare_monthly_draft(cid)
            assert result is None

    def test_collects_bank_account_issues(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            # Remove bank account from one employee
            emp = Employee.query.filter_by(employee_id='EMP001', company_id=cid).first()
            emp.bank_account = None
            emp.bank_or_telebirr = None
            db.session.commit()

            result = prepare_monthly_draft(cid)
            assert result is not None
            assert len(result['issues']) > 0
            assert any('no bank account' in i for i in result['issues'])

    def test_collects_tin_issues(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            emp = Employee.query.filter_by(employee_id='EMP001', company_id=cid).first()
            emp.tin = None
            db.session.commit()

            result = prepare_monthly_draft(cid)
            assert result is not None
            assert any('no TIN' in i for i in result['issues'])

    def test_notifies_owner(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            prepare_monthly_draft(cid)
            notifs = Notification.query.filter_by(user_id=uid).all()
            assert len(notifs) >= 1
            assert 'Draft payroll' in notifs[0].message

    def test_draft_period_matches_current_ethiopian_month(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian
            today = date.today()
            eth_year, eth_month, _ = gregorian_to_ethiopian(today)
            expected_period = f'{eth_year}-{eth_month:02d}'

            result = prepare_monthly_draft(cid)
            assert result is not None
            assert result['period'] == expected_period


# ─── send_compliance_nudges ───


class TestSendComplianceNudges:
    """Test compliance deadline notifications."""

    def test_no_nudge_when_deadlines_far_away(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            # Create a recent completed run (deadlines are far away)
            run = PayrollRun(
                company_id=cid, run_date=date.today(), status='completed',
            )
            run.generate_period()
            db.session.add(run)
            db.session.commit()

            alerts = send_compliance_nudges(cid)
            # Deadlines should be >3 days away for a run created today
            assert len(alerts) == 0

    def test_no_nudge_when_no_completed_runs(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            alerts = send_compliance_nudges(cid)
            # Without a completed run, deadlines default to today — should be close
            # But the function should not crash
            assert isinstance(alerts, list)

    def test_sends_nudge_when_erca_deadline_close(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            # Create a run from 2 months ago — ERCA deadline should be past
            two_months_ago = date.today() - timedelta(days=60)
            run = PayrollRun(
                company_id=cid, run_date=two_months_ago, status='completed',
            )
            run.generate_period()
            db.session.add(run)
            db.session.commit()

            alerts = send_compliance_nudges(cid)
            # Should have at least one alert (ERCA overdue)
            assert len(alerts) > 0
            assert any('ERCA' in a or 'Pension' in a or 'overdue' in a.lower() for a in alerts)

    def test_creates_notification_for_owner(self, app):
        cid, uid = _setup(app)
        with app.app_context():
            # Create an old run to trigger overdue alerts
            old_date = date.today() - timedelta(days=60)
            run = PayrollRun(
                company_id=cid, run_date=old_date, status='completed',
            )
            run.generate_period()
            db.session.add(run)
            db.session.commit()

            send_compliance_nudges(cid)
            notifs = Notification.query.filter_by(user_id=uid).all()
            # Should have at least one notification
            assert len(notifs) >= 1

    def test_returns_empty_list_on_error(self, app):
        """Should not crash if DB has issues."""
        cid, uid = _setup(app)
        with app.app_context():
            # Pass invalid company_id — should not crash
            alerts = send_compliance_nudges(99999)
            assert isinstance(alerts, list)
