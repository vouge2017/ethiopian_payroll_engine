"""
Tests for filing_workspace.py — Filing Workspace

Tests the month-end filing readiness: ERCA, Pension, Bank File.

Run: python -m pytest tests/test_filing_workspace.py -v
"""
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch

from payroll_engine.filing_workspace import (
    FILED,
    NOT_READY,
    READY,
    build_filing_workspace,
)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_run(run_id=1, period='2018-10', company_id=1, status='completed',
              run_date=None, disbursement_status=None):
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.status = status
    run.run_date = run_date or date(2026, 8, 1)
    run.disbursement_status = disbursement_status
    return run


def _make_company(company_id=1):
    company = MagicMock()
    company.id = company_id
    company.compliance_deadlines = {}
    return company


def _setup(run, company, filing_records=None, deadline_days=None):
    """Set up mocks for build_filing_workspace."""
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Run lookup
    def session_get(model, id):
        if id == run.id:
            return run
        if id == company.id:
            return company
        return None
    mock_db.session.get.side_effect = session_get

    # Filing records
    records = filing_records or {}
    def filing_filter_by(**kwargs):
        ftype = kwargs.get('filing_type')
        mock = MagicMock()
        mock.first.return_value = records.get(ftype)
        return mock
    mock_models.FilingRecord.query.filter_by.side_effect = filing_filter_by

    # Deadline calculation
    mock_models.Company = MagicMock

    return mock_db, mock_models


# ─────────────────────────────────────────────
# Tests: Payroll step
# ─────────────────────────────────────────────

class TestPayrollStep:

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_completed_payroll(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='completed')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        payroll = workspace.steps[0]
        assert payroll.name == 'Payroll'
        assert payroll.status == FILED

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_draft_payroll(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='draft')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        payroll = workspace.steps[0]
        assert payroll.status == NOT_READY

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_locked_payroll(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='locked')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        payroll = workspace.steps[0]
        assert payroll.status == FILED


# ─────────────────────────────────────────────
# Tests: Filing steps
# ─────────────────────────────────────────────

class TestFilingSteps:

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_four_steps_exist(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run()
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        assert len(workspace.steps) == 4
        names = [s.name for s in workspace.steps]
        assert 'Payroll' in names
        assert 'ERCA Tax Filing' in names
        assert 'Pension Remittance' in names
        assert 'Bank File' in names

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_amharic_names(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run()
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        for step in workspace.steps:
            assert step.name_am is not None
            assert len(step.name_am) > 0

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_not_ready_when_payroll_draft(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='draft')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        # Only payroll step should be NOT_READY, others should also be NOT_READY
        for step in workspace.steps:
            assert step.status == NOT_READY

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_ready_when_payroll_completed(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='completed')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        # ERCA, Pension, Bank should be READY
        erca = [s for s in workspace.steps if s.name == 'ERCA Tax Filing'][0]
        pension = [s for s in workspace.steps if s.name == 'Pension Remittance'][0]
        bank = [s for s in workspace.steps if s.name == 'Bank File'][0]

        assert erca.status == READY
        assert pension.status == READY
        assert bank.status == READY


# ─────────────────────────────────────────────
# Tests: Filed status
# ─────────────────────────────────────────────

class TestFiledStatus:

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_erca_filed(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run()
        company = _make_company()

        erca_record = MagicMock()
        erca_record.filed_at = datetime(2026, 8, 25)
        erca_record.confirmation_number = 'ERCA-2026-12345'

        mock_db, mock_models = _setup(run, company, filing_records={'erca': erca_record})

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        erca = [s for s in workspace.steps if s.name == 'ERCA Tax Filing'][0]
        assert erca.status == FILED
        assert erca.confirmation == 'ERCA-2026-12345'

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_bank_disbursed(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(disbursement_status='disbursed')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        bank = [s for s in workspace.steps if s.name == 'Bank File'][0]
        assert bank.status == FILED
        assert 'Disbursed' in bank.detail


# ─────────────────────────────────────────────
# Tests: Workspace summary
# ─────────────────────────────────────────────

class TestWorkspaceSummary:

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_all_filed(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(disbursement_status='disbursed')
        company = _make_company()

        erca_record = MagicMock()
        erca_record.filed_at = datetime(2026, 8, 25)
        erca_record.confirmation_number = 'ERCA-123'
        pension_record = MagicMock()
        pension_record.filed_at = datetime(2026, 8, 20)
        pension_record.confirmation_number = 'PEN-456'

        mock_db, mock_models = _setup(run, company, filing_records={
            'erca': erca_record, 'pension': pension_record
        })

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        assert workspace.all_filed is True
        assert 'All filings complete' in workspace.summary

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_not_all_filed(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='completed')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        assert workspace.all_filed is False

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_ready_count(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run(status='completed')
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        # Payroll=FILED, ERCA=READY, Pension=READY, Bank=READY
        assert workspace.filed_count == 1
        assert workspace.ready_count == 3


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_invalid_run_returns_none(self):
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = None

        result = build_filing_workspace(999, 1, mock_db, mock_models)
        assert result is None

    def test_wrong_company_returns_none(self):
        run = _make_run(company_id=2)
        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_db.session.get.return_value = run

        result = build_filing_workspace(1, 1, mock_db, mock_models)
        assert result is None

    @patch('payroll_engine.filing_workspace.get_deadline_for_type')
    def test_amharic_names_present(self, mock_deadline):
        mock_deadline.return_value = date(2026, 9, 25)
        run = _make_run()
        company = _make_company()

        mock_db, mock_models = _setup(run, company)

        workspace = build_filing_workspace(1, 1, mock_db, mock_models)

        for step in workspace.steps:
            assert step.name_am != ''
            assert step.name_am != step.name  # Should be different from English
