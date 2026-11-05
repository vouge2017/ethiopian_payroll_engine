"""One synthetic month compared with independently worked amounts."""

import re
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy import text
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import saved_review

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def test_fixed_month_reconciles_all_outputs(worksheet, monkeypatch):
    # One salaried employee: 10,000 basic + 2,000 taxable general allowance.
    # Project's gross-tax policy: 300 + 600 + 750 + (2,000 * 30%) = 2,250.
    # Employee pension 10,000 * 7% = 700; employer pension 10,000 * 11% = 1,100.
    # Net = 12,000 - 2,250 - 700 = 9,050. No leave, bonus, loan or exemptions.
    app, client, ids, engine, rid = saved_review(worksheet, monkeypatch)
    page = client.get(f'/payroll/{rid}/confirm').get_data(as_text=True)
    key = re.search(r'name="idempotency_key" value="([^"]+)"', page).group(1)
    version = re.search(r'name="run_version" value="([^"]+)"', page).group(1)
    assert (
        client.post(
            '/payroll/approve',
            data={
                'run_id': rid,
                'password': 'Synthetic1!',
                'idempotency_key': key,
                'run_version': version,
            },
        ).status_code
        == 302
    )
    with engine.connect() as conn:
        row = conn.execute(
            text(
                'SELECT id, gross_salary, taxable_income, tax, employee_pension, employer_pension, net_pay '
                'FROM payslip WHERE company_id=:company AND payroll_run_id=:run'
            ),
            {'company': ids['company'], 'run': rid},
        ).one()
        assert row[1:] == tuple(map(Decimal, ('12000', '12000', '2250', '700', '1100', '9050')))
        approval = conn.execute(
            text('SELECT status, approved_by, approved_at FROM payroll_run WHERE id=:run AND company_id=:company'),
            {'company': ids['company'], 'run': rid},
        ).one()
        assert approval.status == 'completed' and approval.approved_by == ids['user'] and approval.approved_at
        assert conn.execute(
            text('SELECT reviewed_version FROM approval_idempotency WHERE payroll_run_id=:run'), {'run': rid}
        ).scalar_one() == int(version)
        assert (
            conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id=:company AND action='payroll_run_completed'"),
                {'company': ids['company']},
            ).scalar_one()
            == 1
        )

    pdf = client.get(f'/payslips/{row.id}/download')
    assert pdf.status_code == 200
    pdf_text = ' '.join(page.extract_text() for page in PdfReader(BytesIO(pdf.data)).pages)
    for expected in ('12,000.00', '2,250.00', '700.00', '9,050.00'):
        assert expected in pdf_text

    paye = client.get(f'/reports/erca/{rid}')
    assert paye.status_code == 200
    paye_sheet = load_workbook(BytesIO(paye.data), data_only=True).active
    paye_row = {
        paye_sheet.cell(5, col).value: paye_sheet.cell(6, col).value for col in range(1, paye_sheet.max_column + 1)
    }
    assert Decimal(str(paye_row['Total Taxable'])) == Decimal('12000')
    assert Decimal(str(paye_row['Tax withheld'])) == Decimal('2250')

    pension = client.get(f'/reports/pension/{rid}')
    assert pension.status_code == 200
    pension_sheet = load_workbook(BytesIO(pension.data), data_only=True).active
    assert [Decimal(str(pension_sheet.cell(6, col).value)) for col in (4, 5, 6, 7)] == list(
        map(Decimal, ('10000', '700', '1100', '1800'))
    )

    from payroll_engine.accounting_bp import _generate_journal_entries

    with app.app_context():
        journal = _generate_journal_entries(rid, ids['company'])
        assert journal['balanced']
        assert journal['total_debits'] == journal['total_credits'] == Decimal('13100')
        assert journal['totals']['gross'] == Decimal('12000')
        assert journal['totals']['net'] == Decimal('9050')
    accounting = client.get(f'/accounting/export/{rid}?format=generic')
    assert accounting.status_code == 200 and '9050.00' in accounting.get_data(as_text=True)
    bank = client.get(f'/reports/bank/{rid}?format=csv&bank=cbe')
    assert bank.status_code == 200 and '9050.00' in bank.get_data(as_text=True)
