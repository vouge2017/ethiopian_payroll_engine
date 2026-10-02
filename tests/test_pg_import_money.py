"""Mixed valid/invalid payroll files cannot silently create a partial payroll."""

import io

import openpyxl
import pytest
from test_pg_spreadsheet_inputs import PG_URL

from payroll_engine.models import PayrollDraft, PayrollPreview, PayrollRun

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


@pytest.mark.parametrize('path', ['/payroll', '/payroll/api/preview'])
@pytest.mark.parametrize('kind', ['csv', 'xlsx'])
@pytest.mark.parametrize('invalid', [True, False])
def test_money_validation_on_upload_and_preview(worksheet, path, kind, invalid):
    app, client, ids, _engine, _cfg = worksheet
    rows = [
        ['employee_id', 'name', 'basic_salary', 'allowances', 'tin', 'bank_or_telebirr'],
        ['BAD', 'Synthetic invalid', 'not a number', 0, '1234567890', 'cbe:1000123456789'],
        ['SHEET1', 'Synthetic monthly', 10000, 2000, '1234567890', 'cbe:1000123456789'],
    ]
    if not invalid:
        rows.pop(1)
    if kind == 'xlsx':
        book = openpyxl.Workbook()
        for row in rows:
            book.active.append(row)
        buffer = io.BytesIO()
        book.save(buffer)
        buffer.seek(0)
    else:
        buffer = io.BytesIO(('\n'.join(','.join(str(value) for value in row) for row in rows) + '\n').encode())
    response = client.post(path, data={'file': (buffer, f'synthetic.{kind}')})
    if not invalid:
        assert response.status_code == 200
        with app.app_context():
            expected = (0, 0, 1) if path.endswith('/preview') else (1, 1, 0)
            for model, count in zip((PayrollRun, PayrollDraft, PayrollPreview), expected, strict=True):
                assert model.query.filter_by(company_id=ids['company']).count() == count
        return
    if path.endswith('/preview'):
        assert response.status_code == 400
        assert not response.json['ok'] and 'Row 2' in response.json['row_errors'][0]
    else:
        assert response.status_code == 302 and response.location.endswith('/payroll')
        with client.session_transaction() as session:
            assert any('Row 2' in message for _category, message in session.get('_flashes', []))
    with app.app_context():
        for model in (PayrollRun, PayrollDraft, PayrollPreview):
            assert model.query.filter_by(company_id=ids['company']).count() == 0
