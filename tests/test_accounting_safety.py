"""Accounting files must not silently publish inconsistent payroll money."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from test_accounting_export import _make_company, _make_employee, _make_payslip, _make_run

from payroll_engine import accounting_bp


@pytest.mark.parametrize(
    'exporter',
    ['_export_generic_csv', '_export_quickbooks_iif', '_export_peachtree', '_export_xero'],
)
def test_export_rechecks_lines_even_when_balance_flag_says_true(exporter):
    journal = {
        'reference': 'SYNTHETIC',
        'period': '2026-10',
        'date': '2026-10-01',
        'company': 'Synthetic',
        'balanced': True,
        'entries': [],
        'totals': dict.fromkeys(['gross', 'tax', 'pension_employee', 'pension_employer', 'net'], Decimal('0')),
        'journal_lines': [
            {
                'account': '5100',
                'name': 'Salary',
                'debit': Decimal('14000.50'),
                'credit': Decimal('0'),
                'type': 'expense',
            },
            {'account': '1000', 'name': 'Bank', 'debit': Decimal('0'), 'credit': Decimal('12700.50'), 'type': 'asset'},
        ],
    }
    with pytest.raises(ValueError, match='reconcile'):
        getattr(accounting_bp, exporter)(journal)


def generate(monkeypatch, payslips):
    for name in ('Company', 'Employee', 'Payslip', 'PayrollRun'):
        monkeypatch.setattr(accounting_bp, name, MagicMock())
    accounting_bp.PayrollRun.query.filter_by.return_value.first_or_404.return_value = _make_run()
    accounting_bp.Company.query.get.return_value = _make_company()
    accounting_bp.Payslip.query.filter_by.return_value.all.return_value = payslips
    monkeypatch.setattr(accounting_bp, 'tenant_get', lambda *args: _make_employee())
    return accounting_bp._generate_journal_entries(1, 1)


def test_explicit_reductions_and_recoveries_reconcile_without_balancing_plug(monkeypatch):
    payslip = _make_payslip(net='7150')
    payslip.unpaid_leave_reduction = Decimal('300')
    payslip.sick_leave_reduction = Decimal('100')
    payslip.deduction_details = [
        {'type': 'loan', 'amount': '100'},
        {'type': 'advance', 'amount': '50'},
        {'type': 'court_order', 'amount': '100'},
    ]
    journal = generate(monkeypatch, [payslip])
    accounting_bp._require_balanced_journal(journal)
    assert journal['total_debits'] == journal['total_credits'] == Decimal('10700')
    lines = {line['account']: line for line in journal['journal_lines']}
    assert lines['5100']['debit'] == Decimal('9600')
    assert lines['1300']['credit'] == Decimal('150')
    assert lines['2300']['credit'] == Decimal('100')


def test_opposite_employee_errors_cannot_cancel_into_balanced_export(monkeypatch):
    journal = generate(monkeypatch, [_make_payslip(net=7700), _make_payslip(net=7900)])
    assert journal['total_debits'] == journal['total_credits']
    with pytest.raises(ValueError, match='reconcile'):
        accounting_bp._require_balanced_journal(journal)


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '0.001', 'not money', '1e100'])
def test_invalid_money_cannot_enter_journal(value):
    with pytest.raises(ValueError, match='invalid money'):
        accounting_bp._journal_money(value)
