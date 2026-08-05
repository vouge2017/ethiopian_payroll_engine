"""
Tests for cockpit.py — Accountant Cockpit

Tests the landing page that answers 5 questions in 10 seconds.

Run: python -m pytest tests/test_cockpit.py -v
"""
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.cockpit import build_cockpit, CockpitData, AttentionItem


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_company(company_id=1, name='Test PLC'):
    company = MagicMock()
    company.id = company_id
    company.name = name
    company.compliance_deadlines = {}
    return company


def _make_run(run_id=1, period='2018-10', company_id=1, status='completed',
              run_date=None):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.status = status
    run.run_date = run_date or date(2026, 8, 1)
    run.disbursement_status = None
    return run


def _make_employee(emp_id, name, bank='1000123', tin='123', phone='0911'):
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = f'EMP-{emp_id:03d}'
    emp.name = name
    emp.company_id = 1
    emp.bank_or_telebirr = bank
    emp.tin = tin
    emp.phone = phone
    emp.is_deleted = False
    return emp


def _setup(company, runs=None, employees=None):
    """Set up mocks for build_cockpit."""
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Company lookup — use a dict to simulate session.get
    def session_get(model, id):
        if id == company.id:
            return company
        return None
    mock_session = MagicMock()
    mock_session.get.side_effect = session_get
    mock_db.session = mock_session

    # Runs — set up the full chain
    mock_chain = MagicMock()
    mock_chain.first.return_value = runs[0] if runs else None
    mock_models.PayrollRun.query.filter_by.return_value = mock_chain
    mock_chain.filter.return_value = mock_chain
    mock_chain.order_by.return_value = mock_chain

    # Employees
    mock_models.Employee.query.filter_by.return_value.all.return_value = employees or []

    return mock_db, mock_models


# ─────────────────────────────────────────────
# Tests: No payroll runs
# ─────────────────────────────────────────────

class TestNoPayroll:

    def test_no_runs_status(self):
        company = _make_company()
        mock_db, mock_models = _setup(company)

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert cockpit is not None
        assert cockpit.status == 'no_payroll'
        assert 'No payroll runs' in cockpit.status_message
        assert len(cockpit.attention_items) > 0

    def test_no_runs_attention_item(self):
        company = _make_company()
        mock_db, mock_models = _setup(company)

        cockpit = build_cockpit(1, mock_db, mock_models)

        item = cockpit.attention_items[0]
        assert item.priority == 'urgent'
        assert 'No payroll runs' in item.title
        assert item.action_url == '/payroll/upload'


# ─────────────────────────────────────────────
# Tests: Draft payroll
# ─────────────────────────────────────────────

class TestDraftPayroll:

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_draft_payroll_needs_attention(self, mock_deadline, mock_change,
                                            mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)
        mock_change.return_value = None
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)
        mock_exceptions.return_value = MagicMock(has_blocking=False, blocking_issues=[])

        company = _make_company()
        run = _make_run(status='draft')
        emp = _make_employee(1, 'Dawit')

        mock_db, mock_models = _setup(company, [run], [emp])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert cockpit.status == 'attention'
        assert any('draft' in item.title.lower() for item in cockpit.attention_items)


# ─────────────────────────────────────────────
# Tests: Completed payroll
# ─────────────────────────────────────────────

class TestCompletedPayroll:

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_completed_payroll_ready_for_approval(self, mock_deadline, mock_change,
                                                    mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)
        mock_change.return_value = None
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)
        mock_exceptions.return_value = MagicMock(has_blocking=False, blocking_issues=[])

        company = _make_company()
        run = _make_run(status='completed')
        emp = _make_employee(1, 'Dawit')

        mock_db, mock_models = _setup(company, [run], [emp])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert any('approval' in item.title.lower() for item in cockpit.attention_items)


# ─────────────────────────────────────────────
# Tests: Missing employee data
# ─────────────────────────────────────────────

class TestMissingData:

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_missing_bank_detected(self, mock_deadline, mock_change,
                                    mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)
        mock_change.return_value = None
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)
        mock_exceptions.return_value = MagicMock(has_blocking=False, blocking_issues=[])

        company = _make_company()
        run = _make_run(status='completed')
        emp = _make_employee(1, 'Dawit', bank='')  # Missing bank

        mock_db, mock_models = _setup(company, [run], [emp])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert any('incomplete' in item.title.lower() for item in cockpit.attention_items)


# ─────────────────────────────────────────────
# Tests: Blocking issues
# ─────────────────────────────────────────────

class TestBlocking:

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_blocking_issues_detected(self, mock_deadline, mock_change,
                                       mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)
        mock_change.return_value = None
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)

        blocking_issue = MagicMock(
            title='Negative net pay',
            description='Employee owes money',
            action_url='/employees/1/deductions',
        )
        mock_exceptions.return_value = MagicMock(
            has_blocking=True,
            blocking_issues=[blocking_issue],
        )

        company = _make_company()
        run = _make_run(status='completed')
        emp = _make_employee(1, 'Dawit')

        mock_db, mock_models = _setup(company, [run], [emp])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert cockpit.status == 'blocked'
        assert cockpit.has_blocking is True
        assert len(cockpit.blocking_items) > 0


# ─────────────────────────────────────────────
# Tests: Unusual variance
# ─────────────────────────────────────────────

class TestUnusualVariance:

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_variance_flagged(self, mock_deadline, mock_change,
                               mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)

        mock_change.return_value = MagicMock(
            has_unusual_variance=True,
            variance_notes=['Total gross +25% — exceeds threshold'],
            salary_changes=[],
            headcount_change=0,
            gross_delta_pct=25.0,
        )
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)
        mock_exceptions.return_value = MagicMock(has_blocking=False, blocking_issues=[])

        from payroll_engine.change_summary import ChangeSummary
        mock_change.return_value = MagicMock(
            has_unusual_variance=True,
            variance_notes=['Total gross +25% — exceeds threshold'],
            salary_changes=[],
            headcount_change=0,
            gross_delta_pct=25.0,
        )

        company = _make_company()
        run = _make_run(status='completed')
        emp = _make_employee(1, 'Dawit')

        mock_db, mock_models = _setup(company, [run], [emp])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert cockpit.has_unusual is True
        assert len(cockpit.unusual_items) > 0


# ─────────────────────────────────────────────
# Tests: Narrative
# ─────────────────────────────────────────────

class TestNarrative:

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_narrative_generated(self, mock_deadline, mock_change,
                                  mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)
        mock_change.return_value = None
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)
        mock_exceptions.return_value = MagicMock(has_blocking=False, blocking_issues=[])

        company = _make_company()
        run = _make_run(status='completed')
        emp = _make_employee(1, 'Dawit')

        mock_db, mock_models = _setup(company, [run], [emp])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert len(cockpit.narrative) > 0
        assert 'employees' in cockpit.narrative.lower() or 'employee' in cockpit.narrative.lower()


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_invalid_company_returns_none(self):
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = None

        result = build_cockpit(999, mock_db, mock_models)
        assert result is None

    @patch('payroll_engine.cockpit.classify_exceptions')
    @patch('payroll_engine.cockpit.build_filing_workspace')
    @patch('payroll_engine.cockpit.compute_change_summary')
    @patch('payroll_engine.cockpit.get_deadline_for_type')
    def test_period_set_from_latest_run(self, mock_deadline, mock_change,
                                         mock_filing, mock_exceptions):
        mock_deadline.return_value = date(2026, 9, 25)
        mock_change.return_value = None
        mock_filing.return_value = MagicMock(steps=[], all_filed=False, has_overdue=False)
        mock_exceptions.return_value = MagicMock(has_blocking=False, blocking_issues=[])

        company = _make_company()
        run = _make_run(period='2018-10', status='completed')

        mock_db, mock_models = _setup(company, [run], [])

        cockpit = build_cockpit(1, mock_db, mock_models)

        assert cockpit.period == '2018-10'
