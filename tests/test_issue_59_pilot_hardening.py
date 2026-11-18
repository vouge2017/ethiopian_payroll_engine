import os
from datetime import date, datetime

import pytest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')

from payroll_engine import create_app, db
from payroll_engine.models import Company, PayrollRun, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def signed_in_client(app):
    with app.app_context():
        company = Company(name='Issue 59 Test Company', compliance_deadlines={})
        db.session.add(company)
        db.session.flush()
        user = User(phone='0919999999', role='owner', company_id=company.id)
        user.set_password('FakeIssue59Pass1!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
    return client


def _add_run(company_id, reference, run_date, status, created_at):
    run = PayrollRun(
        company_id=company_id,
        reference=reference,
        period=reference,
        run_date=run_date,
        status=status,
        created_at=created_at,
    )
    db.session.add(run)
    db.session.commit()
    return run


def _fake_deadlines(monkeypatch, default_days=28):
    import payroll_engine.compliance as compliance

    dates_seen = []

    def get_deadlines(company=None, payroll_date=None):
        dates_seen.append(payroll_date)
        days = {
            '2026-07-01': -2,
            '2026-06-01': 1,
            '2026-08-01': -2,
            '2026-09-01': 14,
        }.get(payroll_date, default_days)
        return {
            'erca_deadline': '2026-08-25',
            'pension_deadline': '2026-08-10',
            'pssa_deadline': '2026-08-10',
            'erca_days_left': days,
            'pension_days_left': days,
            'pssa_days_left': days,
            'erca_status': 'danger' if days < 0 else 'success',
            'pension_status': 'danger' if days < 0 else 'success',
        }

    monkeypatch.setattr(compliance, 'get_upcoming_deadlines', get_deadlines)
    return dates_seen


def _request_with_periods(client, monkeypatch, path, expected_date, default_days=28):
    dates_seen = _fake_deadlines(monkeypatch, default_days)
    response = client.get(path)
    assert response.status_code == 200
    assert dates_seen[-2:] == [expected_date, expected_date]
    return response.get_data(as_text=True)


def test_newer_draft_does_not_change_any_deadline_period(app, signed_in_client, monkeypatch):
    with app.app_context():
        company = Company.query.filter_by(name='Issue 59 Test Company').first()
        _add_run(
            company.id,
            'EARLIER-2018-09',
            date(2026, 6, 1),
            'completed',
            datetime(2026, 7, 5),
        )
        _add_run(
            company.id,
            'COMPLETED-2018-10',
            date(2026, 7, 1),
            'completed',
            datetime(2026, 6, 2),
        )
        _add_run(
            company.id,
            'DRAFT-2018-12',
            date(2026, 9, 1),
            'draft',
            datetime(2026, 9, 2),
        )

    dashboard = _request_with_periods(signed_in_client, monkeypatch, '/', '2026-07-01')
    assert 'ERCA: 2 days overdue' in dashboard
    assert 'Overdue by 2 days' in dashboard

    companies = _request_with_periods(signed_in_client, monkeypatch, '/companies', '2026-07-01')
    assert 'ERCA: -2d' in companies
    assert 'Completed' in companies


def test_explicit_completed_period_is_used_by_banner_and_both_cards(app, signed_in_client, monkeypatch):
    with app.app_context():
        company = Company.query.filter_by(name='Issue 59 Test Company').first()
        selected = _add_run(
            company.id,
            'SELECTED-2018-09',
            date(2026, 6, 1),
            'completed',
            datetime(2026, 6, 2),
        )
        _add_run(
            company.id,
            'LATEST-2018-10',
            date(2026, 7, 1),
            'completed',
            datetime(2026, 7, 2),
        )
        selected_id = selected.id

    dashboard = _request_with_periods(
        signed_in_client,
        monkeypatch,
        f'/?run_id={selected_id}',
        '2026-06-01',
    )
    assert 'ERCA: 1 days remaining' in dashboard
    assert 'Due in 1 days' in dashboard

    companies = _request_with_periods(
        signed_in_client,
        monkeypatch,
        f'/companies?run_id={selected_id}',
        '2026-06-01',
    )
    assert 'ERCA: 1d' in companies


def test_no_completed_runs_uses_today_for_all_deadline_displays(app, signed_in_client, monkeypatch):
    with app.app_context():
        company = Company.query.filter_by(name='Issue 59 Test Company').first()
        _add_run(
            company.id,
            'DRAFT-2018-12',
            date(2026, 8, 1),
            'draft',
            datetime(2026, 8, 2),
        )

    today = date.today().isoformat()
    dashboard = _request_with_periods(signed_in_client, monkeypatch, '/', today, default_days=1)
    assert 'ERCA: 1 days remaining' in dashboard
    assert 'Due in 1 days' in dashboard
    companies = _request_with_periods(signed_in_client, monkeypatch, '/companies', today, default_days=1)
    assert 'ERCA: 1d' in companies
    assert 'No payroll' in companies
