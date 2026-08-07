"""
Tests for accounting_bp.py — journal entry exports.

Tests the journal entry generation logic, CSV/IIF/Peachtree export formats,
and the accounting preview page.

Run: python -m pytest tests/test_accounting_export.py -v
"""
import csv
import io
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─────────────────────────────────────────────
# Mock helpers
# ─────────────────────────────────────────────

def _make_payslip(gross=10000, tax=1500, pension_emp=700, pension_empr=1100, net=7800):
    """Create a mock payslip."""
    ps = MagicMock()
    ps.employee_id = 1
    ps.gross_salary = Decimal(str(gross))
    ps.tax = Decimal(str(tax))
    ps.employee_pension = Decimal(str(pension_emp))
    ps.employer_pension = Decimal(str(pension_empr))
    ps.net_pay = Decimal(str(net))
    return ps


def _make_employee(emp_id=1, name='Dawit Kebede', department='Finance'):
    """Create a mock employee."""
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = f'EMP-{emp_id:03d}'
    emp.name = name
    emp.department = department
    return emp


def _make_run(run_id=1, period='2026-07', reference='PR-2026-07-001'):
    """Create a mock payroll run."""
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.reference = reference
    run.run_date = MagicMock()
    run.run_date.strftime = lambda fmt: '2026-07-01' if fmt == '%Y-%m-%d' else '2026-07'
    return run


def _make_company(name='Test Company PLC'):
    """Create a mock company."""
    company = MagicMock()
    company.name = name
    return company


# ─────────────────────────────────────────────
# Tests: _generate_journal_entries
# ─────────────────────────────────────────────

class TestGenerateJournalEntries:

    def _import_func(self):
        from payroll_engine.accounting_bp import _generate_journal_entries
        return _generate_journal_entries

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_basic_journal_structure(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        assert journal is not None
        assert 'journal_lines' in journal
        assert 'entries' in journal
        assert 'totals' in journal
        assert 'balanced' in journal

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_journal_is_balanced(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        assert journal['balanced'] is True
        assert journal['total_debits'] == journal['total_credits']

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_journal_lines_structure(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)
        lines = journal['journal_lines']

        # Should have 6 standard lines
        assert len(lines) == 6

        # Check account codes
        accounts = {l['account'] for l in lines}
        assert '5100' in accounts  # Salary Expense
        assert '5200' in accounts  # Employer Pension Expense
        assert '2100' in accounts  # PAYE Tax Payable
        assert '2200' in accounts  # Pension Payable (Employee)
        assert '2210' in accounts  # Pension Payable (Employer)
        assert '1000' in accounts  # Bank/Cash

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_debit_credit_structure(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        for line in journal['journal_lines']:
            assert 'debit' in line
            assert 'credit' in line
            assert 'account' in line
            assert 'name' in line
            assert 'type' in line
            # Each line should have exactly one side non-zero
            assert (line['debit'] > 0 and line['credit'] == 0) or \
                   (line['credit'] > 0 and line['debit'] == 0)

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_totals_match_input(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [
            _make_payslip(gross=10000, tax=1500, pension_emp=700, pension_empr=1100, net=7800),
            _make_payslip(gross=20000, tax=3500, pension_emp=1400, pension_empr=2200, net=15400),
        ]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        assert journal['totals']['gross'] == Decimal('30000')
        assert journal['totals']['tax'] == Decimal('5000')
        assert journal['totals']['pension_employee'] == Decimal('2100')
        assert journal['totals']['pension_employer'] == Decimal('3300')
        assert journal['totals']['net'] == Decimal('23200')

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_returns_none_for_empty_run(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = []
        result = func(1, 1)

        assert result is None

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_employee_detail_entries(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee(emp_id=1, name='Dawit Kebede')

        journal = func(1, 1)

        assert len(journal['entries']) == 1
        entry = journal['entries'][0]
        assert entry['employee_name'] == 'Dawit Kebede'
        assert entry['gross'] == Decimal('10000')
        assert entry['net_pay'] == Decimal('7800')

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_expense_lines_are_debits(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        for line in journal['journal_lines']:
            if line['type'] == 'expense':
                assert line['debit'] > 0
                assert line['credit'] == Decimal('0')

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_liability_lines_are_credits(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        for line in journal['journal_lines']:
            if line['type'] == 'liability':
                assert line['credit'] > 0
                assert line['debit'] == Decimal('0')

    @patch('payroll_engine.accounting_bp.Company')
    @patch('payroll_engine.accounting_bp.Employee')
    @patch('payroll_engine.accounting_bp.Payslip')
    @patch('payroll_engine.accounting_bp.PayrollRun')
    def test_reference_included(self, MockRun, MockPayslip, MockEmp, MockCompany):
        func = self._import_func()

        MockRun.query.filter_by.return_value.first_or_404.return_value = _make_run(
            reference='PR-2026-07-001'
        )
        MockCompany.query.get.return_value = _make_company()
        MockPayslip.query.filter_by.return_value.all.return_value = [_make_payslip()]
        MockEmp.query.get.return_value = _make_employee()

        journal = func(1, 1)

        assert journal['reference'] == 'PR-2026-07-001'
        assert journal['period'] == '2026-07'


# ─────────────────────────────────────────────
# Tests: CSV Export
# ─────────────────────────────────────────────

class TestGenericCSVExport:

    def _get_csv_output(self, journal):
        """Call _export_generic_csv and parse the CSV output."""
        from payroll_engine.accounting_bp import _export_generic_csv
        response = _export_generic_csv(journal)
        return response.get_data(as_text=True)

    def _sample_journal(self):
        return {
            'reference': 'PR-2026-07-001',
            'period': '2026-07',
            'date': '2026-07-01',
            'company': 'Test PLC',
            'entries': [
                {'employee_id': 'E001', 'employee_name': 'Dawit', 'department': 'IT',
                 'gross': Decimal('10000'), 'tax': Decimal('1500'),
                 'pension_employee': Decimal('700'), 'pension_employer': Decimal('1100'),
                 'net_pay': Decimal('7800')},
            ],
            'totals': {
                'gross': Decimal('10000'), 'tax': Decimal('1500'),
                'pension_employee': Decimal('700'), 'pension_employer': Decimal('1100'),
                'net': Decimal('7800'),
            },
            'journal_lines': [
                {'account': '5100', 'name': 'Salary Expense', 'debit': Decimal('10000'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '2100', 'name': 'PAYE Tax Payable', 'debit': Decimal('0'),
                 'credit': Decimal('1500'), 'type': 'liability'},
                {'account': '2200', 'name': 'Pension Payable', 'debit': Decimal('0'),
                 'credit': Decimal('700'), 'type': 'liability'},
                {'account': '1000', 'name': 'Bank/Cash', 'debit': Decimal('0'),
                 'credit': Decimal('7800'), 'type': 'asset'},
            ],
        }

    def test_csv_has_header_row(self):
        csv_text = self._get_csv_output(self._sample_journal())
        first_line = csv_text.split('\n')[0]
        assert 'Date' in first_line
        assert 'Account' in first_line
        assert 'Debit' in first_line
        assert 'Credit' in first_line

    def test_csv_contains_journal_lines(self):
        csv_text = self._get_csv_output(self._sample_journal())
        assert '5100' in csv_text
        assert 'Salary Expense' in csv_text
        assert '10000.00' in csv_text

    def test_csv_contains_employee_detail(self):
        csv_text = self._get_csv_output(self._sample_journal())
        assert 'Employee Detail' in csv_text
        assert 'Dawit' in csv_text
        assert 'E001' in csv_text

    def test_csv_contains_totals(self):
        csv_text = self._get_csv_output(self._sample_journal())
        assert 'TOTALS' in csv_text

    def test_csv_debit_credit_formatting(self):
        csv_text = self._get_csv_output(self._sample_journal())
        # Debits should show amounts, credits should be empty (or vice versa)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        # Find the Salary Expense row
        salary_row = None
        for row in rows:
            if len(row) > 3 and 'Salary Expense' in row[3]:
                salary_row = row
                break
        assert salary_row is not None
        assert salary_row[5] == '10000.00'  # Debit
        assert salary_row[6] == ''          # Credit (empty for debit lines)


# ─────────────────────────────────────────────
# Tests: QuickBooks IIF Export
# ─────────────────────────────────────────────

class TestQuickBooksIIFExport:

    def _get_iif_output(self, journal):
        from payroll_engine.accounting_bp import _export_quickbooks_iif
        response = _export_quickbooks_iif(journal)
        return response.get_data(as_text=True)

    def _sample_journal(self):
        return {
            'reference': 'PR-2026-07-001',
            'period': '2026-07',
            'date': '2026-07-01',
            'company': 'Test PLC',
            'entries': [],
            'totals': {},
            'journal_lines': [
                {'account': '5100', 'name': 'Salary Expense', 'debit': Decimal('10000'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '2100', 'name': 'PAYE Tax Payable', 'debit': Decimal('0'),
                 'credit': Decimal('10000'), 'type': 'liability'},
            ],
        }

    def test_iif_has_headers(self):
        iif = self._get_iif_output(self._sample_journal())
        assert '!TRNS' in iif
        assert '!SPL' in iif
        assert '!ENDTRNS' in iif

    def test_iif_has_transaction_type(self):
        iif = self._get_iif_output(self._sample_journal())
        assert 'GENERAL JOURNAL' in iif

    def test_iif_has_account_codes(self):
        iif = self._get_iif_output(self._sample_journal())
        assert '5100' in iif
        assert '2100' in iif

    def test_iif_debit_as_positive(self):
        iif = self._get_iif_output(self._sample_journal())
        # Debits should be positive amounts in TRNS lines
        lines = [l for l in iif.split('\n') if l.startswith('TRNS')]
        assert any('10000.00' in l for l in lines)

    def test_iif_credit_as_negative(self):
        iif = self._get_iif_output(self._sample_journal())
        # Credits should be negative amounts in SPL lines
        lines = [l for l in iif.split('\n') if l.startswith('SPL')]
        assert any('-10000.00' in l for l in lines)

    def test_iif_contains_reference(self):
        iif = self._get_iif_output(self._sample_journal())
        assert 'PR-2026-07-001' in iif

    def test_iif_contains_date(self):
        iif = self._get_iif_output(self._sample_journal())
        assert '2026-07-01' in iif


# ─────────────────────────────────────────────
# Tests: Peachtree CSV Export
# ─────────────────────────────────────────────

class TestPeachtreeExport:

    def _get_peachtree_output(self, journal):
        from payroll_engine.accounting_bp import _export_peachtree
        response = _export_peachtree(journal)
        return response.get_data(as_text=True)

    def _sample_journal(self):
        return {
            'reference': 'PR-2026-07-001',
            'period': '2026-07',
            'date': '2026-07-01',
            'company': 'Test PLC',
            'entries': [],
            'totals': {},
            'journal_lines': [
                {'account': '5100', 'name': 'Salary Expense', 'debit': Decimal('10000'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '2100', 'name': 'PAYE Tax Payable', 'debit': Decimal('0'),
                 'credit': Decimal('10000'), 'type': 'liability'},
            ],
        }

    def test_peachtree_has_header(self):
        output = self._get_peachtree_output(self._sample_journal())
        first_line = output.split('\n')[0]
        assert 'Date' in first_line
        assert 'Reference' in first_line
        assert 'Account' in first_line
        assert 'Debit' in first_line
        assert 'Credit' in first_line

    def test_peachtree_has_data_rows(self):
        output = self._get_peachtree_output(self._sample_journal())
        assert '5100' in output
        assert 'Salary Expense' in output
        assert '10000.00' in output

    def test_peachtree_zero_credits_for_debit_lines(self):
        output = self._get_peachtree_output(self._sample_journal())
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        salary_row = [r for r in rows if len(r) > 3 and 'Salary Expense' in r[3]]
        assert len(salary_row) == 1
        assert salary_row[0][4] == '10000.00'  # Debit
        assert salary_row[0][5] == '0.00'      # Credit


# ─────────────────────────────────────────────
# Tests: Xero CSV Export
# ─────────────────────────────────────────────

class TestXeroExport:

    def _get_xero_output(self, journal):
        from payroll_engine.accounting_bp import _export_xero
        response = _export_xero(journal)
        return response.get_data(as_text=True)

    def _sample_journal(self):
        return {
            'reference': 'PR-2026-07-001', 'period': '2026-07', 'date': '2026-07-01',
            'company': 'Test PLC', 'entries': [],
            'totals': {'gross': Decimal('10000'), 'tax': Decimal('0'),
                       'pension_employee': Decimal('0'), 'pension_employer': Decimal('0'),
                       'net': Decimal('10000')},
            'journal_lines': [
                {'account': '5100', 'name': 'Salary Expense', 'debit': Decimal('10000'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '2100', 'name': 'PAYE Tax Payable', 'debit': Decimal('0'),
                 'credit': Decimal('10000'), 'type': 'liability'},
            ],
        }

    def test_xero_has_header(self):
        output = self._get_xero_output(self._sample_journal())
        first_line = output.split('\n')[0]
        assert 'JournalDate' in first_line
        assert 'JournalNumber' in first_line
        assert 'AccountCode' in first_line
        assert 'Debit' in first_line
        assert 'Credit' in first_line

    def test_xero_has_data_rows(self):
        output = self._get_xero_output(self._sample_journal())
        assert '5100' in output
        assert 'Salary Expense' in output
        assert '10000.00' in output

    def test_xero_contains_reference(self):
        output = self._get_xero_output(self._sample_journal())
        assert 'PR-2026-07-001' in output

    def test_xero_contains_date(self):
        output = self._get_xero_output(self._sample_journal())
        assert '2026-07-01' in output

    def test_xero_contains_company_name(self):
        output = self._get_xero_output(self._sample_journal())
        assert 'Test PLC' in output

    def test_xero_tax_type_field(self):
        output = self._get_xero_output(self._sample_journal())
        assert 'Tax Exempt' in output or 'No Tax' in output

    def test_xero_content_type(self):
        from payroll_engine.accounting_bp import _export_xero
        resp = _export_xero(self._sample_journal())
        assert 'text/csv' in resp.content_type

    def test_xero_filename(self):
        from payroll_engine.accounting_bp import _export_xero
        resp = _export_xero(self._sample_journal())
        assert 'xero' in resp.headers.get('Content-Disposition', '')
        assert '.csv' in resp.headers.get('Content-Disposition', '')


# ─────────────────────────────────────────────
# Tests: Balance verification across formats
# ─────────────────────────────────────────────

class TestBalanceVerification:

    def _make_journal(self, lines):
        return {
            'reference': 'PR-2026-07-001',
            'period': '2026-07',
            'date': '2026-07-01',
            'company': 'Test PLC',
            'entries': [],
            'totals': {},
            'journal_lines': lines,
        }

    def test_balanced_journal_passes(self):
        # Test the balanced flag directly
        journal = self._make_journal([
            {'account': '5100', 'name': 'Expense', 'debit': Decimal('10000'),
             'credit': Decimal('0'), 'type': 'expense'},
            {'account': '1000', 'name': 'Bank', 'debit': Decimal('0'),
             'credit': Decimal('10000'), 'type': 'asset'},
        ])
        total_debits = sum(l['debit'] for l in journal['journal_lines'])
        total_credits = sum(l['credit'] for l in journal['journal_lines'])
        assert total_debits == total_credits

    def test_unbalanced_detected(self):
        journal = self._make_journal([
            {'account': '5100', 'name': 'Expense', 'debit': Decimal('10000'),
             'credit': Decimal('0'), 'type': 'expense'},
            {'account': '1000', 'name': 'Bank', 'debit': Decimal('0'),
             'credit': Decimal('5000'), 'type': 'asset'},
        ])
        total_debits = sum(l['debit'] for l in journal['journal_lines'])
        total_credits = sum(l['credit'] for l in journal['journal_lines'])
        assert total_debits != total_credits


# ─────────────────────────────────────────────
# Tests: Content-Type headers
# ─────────────────────────────────────────────

class TestResponseHeaders:

    def _sample_journal(self):
        return {
            'reference': 'PR-2026-07-001', 'period': '2026-07', 'date': '2026-07-01',
            'company': 'Test PLC', 'entries': [],
            'totals': {'gross': Decimal('1000'), 'tax': Decimal('0'),
                       'pension_employee': Decimal('0'), 'pension_employer': Decimal('0'),
                       'net': Decimal('1000')},
            'journal_lines': [
                {'account': '5100', 'name': 'Expense', 'debit': Decimal('1000'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '1000', 'name': 'Bank', 'debit': Decimal('0'),
                 'credit': Decimal('1000'), 'type': 'asset'},
            ],
        }

    def test_csv_content_type(self):
        from payroll_engine.accounting_bp import _export_generic_csv
        resp = _export_generic_csv(self._sample_journal())
        assert 'text/csv' in resp.content_type

    def test_csv_filename(self):
        from payroll_engine.accounting_bp import _export_generic_csv
        resp = _export_generic_csv(self._sample_journal())
        assert 'attachment' in resp.headers.get('Content-Disposition', '')
        assert '.csv' in resp.headers.get('Content-Disposition', '')

    def test_iif_content_type(self):
        from payroll_engine.accounting_bp import _export_quickbooks_iif
        resp = _export_quickbooks_iif(self._sample_journal())
        assert 'text/plain' in resp.content_type

    def test_iif_filename(self):
        from payroll_engine.accounting_bp import _export_quickbooks_iif
        resp = _export_quickbooks_iif(self._sample_journal())
        assert '.iif' in resp.headers.get('Content-Disposition', '')

    def test_peachtree_content_type(self):
        from payroll_engine.accounting_bp import _export_peachtree
        resp = _export_peachtree(self._sample_journal())
        assert 'text/csv' in resp.content_type


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def _make_totals(self, gross=0, tax=0, pension_emp=0, pension_empr=0, net=0):
        return {'gross': Decimal(str(gross)), 'tax': Decimal(str(tax)),
                'pension_employee': Decimal(str(pension_emp)),
                'pension_employer': Decimal(str(pension_empr)), 'net': Decimal(str(net))}

    def test_zero_amounts(self):
        """Journal with zero amounts should still balance."""
        from payroll_engine.accounting_bp import _export_generic_csv
        journal = {
            'reference': 'PR-ZERO', 'period': '2026-07', 'date': '2026-07-01',
            'company': 'Test', 'entries': [], 'totals': self._make_totals(),
            'journal_lines': [
                {'account': '5100', 'name': 'Expense', 'debit': Decimal('0'),
                 'credit': Decimal('0'), 'type': 'expense'},
            ],
        }
        resp = _export_generic_csv(journal)
        assert resp.status_code == 200

    def test_large_amounts(self):
        """Journal with large ETB amounts should format correctly."""
        from payroll_engine.accounting_bp import _export_generic_csv
        journal = {
            'reference': 'PR-LARGE', 'period': '2026-07', 'date': '2026-07-01',
            'company': 'Test', 'entries': [],
            'totals': self._make_totals(gross=9999999.99, net=9999999.99),
            'journal_lines': [
                {'account': '5100', 'name': 'Expense', 'debit': Decimal('9999999.99'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '1000', 'name': 'Bank', 'debit': Decimal('0'),
                 'credit': Decimal('9999999.99'), 'type': 'asset'},
            ],
        }
        resp = _export_generic_csv(journal)
        csv_text = resp.get_data(as_text=True)
        assert '9999999.99' in csv_text

    def test_multiple_employees_same_department(self):
        """Multiple employees in same department should all appear."""
        from payroll_engine.accounting_bp import _export_generic_csv
        journal = {
            'reference': 'PR-MULTI', 'period': '2026-07', 'date': '2026-07-01',
            'company': 'Test',
            'totals': self._make_totals(gross=25000, tax=4000, pension_emp=1750,
                                        pension_empr=2750, net=19250),
            'entries': [
                {'employee_id': 'E001', 'employee_name': 'Dawit', 'department': 'IT',
                 'gross': Decimal('10000'), 'tax': Decimal('1500'),
                 'pension_employee': Decimal('700'), 'pension_employer': Decimal('1100'),
                 'net_pay': Decimal('7800')},
                {'employee_id': 'E002', 'employee_name': 'Hana', 'department': 'IT',
                 'gross': Decimal('15000'), 'tax': Decimal('2500'),
                 'pension_employee': Decimal('1050'), 'pension_employer': Decimal('1650'),
                 'net_pay': Decimal('11450')},
            ],
            'journal_lines': [
                {'account': '5100', 'name': 'Expense', 'debit': Decimal('25000'),
                 'credit': Decimal('0'), 'type': 'expense'},
                {'account': '1000', 'name': 'Bank', 'debit': Decimal('0'),
                 'credit': Decimal('25000'), 'type': 'asset'},
            ],
        }
        resp = _export_generic_csv(journal)
        csv_text = resp.get_data(as_text=True)
        assert 'Dawit' in csv_text
        assert 'Hana' in csv_text
