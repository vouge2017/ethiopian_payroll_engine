"""
Tests for Phase 2 of BUILD_PLAN_2 — PDF Generation Failure Handling:
- PDF failure doesn't break entire payroll
- Failed PDFs are tracked
- Retry route works
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, UserCompany, PayrollDraft,
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
    """Create company, owner, employees, draft payroll."""
    with app.app_context():
        company = Company(name='PdfTestCo')
        db.session.add(company)
        db.session.flush()

        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.flush()

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
        db.session.flush()

        # Create a review run with draft
        run = PayrollRun(
            company_id=company.id, run_date=date.today(), status='review',
        )
        run.generate_period()
        db.session.add(run)
        db.session.flush()
        run.generate_reference()

        employees_data = [
            {
                'id': 'EMP001', 'name': 'Abebe Kebede', 'phone': '0911111111',
                'basic': 10000, 'allowances': 2000, 'gross': 12000,
                'tax': 1500, 'pension_employee': 700, 'pension_employer': 1100,
                'net': 9800, 'bank': 'cbe:1000123456789', 'tin': '1234567890',
                'taxable': 11300, 'department': '', 'position': '',
            },
            {
                'id': 'EMP002', 'name': 'Hana Tesfaye', 'phone': '0922222222',
                'basic': 8000, 'allowances': 1000, 'gross': 9000,
                'tax': 1000, 'pension_employee': 560, 'pension_employer': 880,
                'net': 7440, 'bank': 'dashen:2000987654321', 'tin': '0987654321',
                'taxable': 8440, 'department': '', 'position': '',
            },
        ]

        draft = PayrollDraft(
            payroll_run_id=run.id,
            employee_data=employees_data,
        )
        db.session.add(draft)
        db.session.commit()

        return company.id, owner.id, run.id


# ─── PDF Failure Handling ───


class TestPdfFailureHandling:
    """Test that PDF failure doesn't break entire payroll."""

    @patch('payroll_engine.services.payroll_service.generate_payslip')
    def test_payroll_completes_when_one_pdf_fails(self, mock_pdf, app):
        """If one PDF fails, the other should still be created."""
        cid, oid, rid = _setup(app)

        # First call fails, second succeeds
        mock_pdf.side_effect = [Exception('Font file not found'), '/tmp/test.pdf']

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            result = process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            assert result.success is True
            assert '1 of 2' in result.message
            assert 'Abebe Kebede' in result.message or 'Hana Tesfaye' in result.message

    @patch('payroll_engine.services.payroll_service.generate_payslip')
    def test_payslip_created_even_when_pdf_fails(self, mock_pdf, app):
        """Payslip should be created even if PDF generation fails."""
        cid, oid, rid = _setup(app)

        mock_pdf.side_effect = Exception('Disk full')

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            result = process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            # Both payslips should exist (even without PDFs)
            payslips = Payslip.query.filter_by(payroll_run_id=rid).all()
            assert len(payslips) == 2
            # Both should have no PDF path
            for ps in payslips:
                assert ps.pdf_file_path is None

    @patch('payroll_engine.services.payroll_service.generate_payslip')
    def test_success_message_when_all_pdfs_succeed(self, mock_pdf, app):
        """Normal message when all PDFs generate successfully."""
        cid, oid, rid = _setup(app)

        mock_pdf.return_value = '/tmp/test.pdf'

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            result = process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            assert result.success is True
            assert '2 employees paid' in result.message

    @patch('payroll_engine.services.payroll_service.generate_payslip')
    def test_all_pdfs_fail(self, mock_pdf, app):
        """If all PDFs fail, payroll still completes."""
        cid, oid, rid = _setup(app)

        mock_pdf.side_effect = Exception('System error')

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            result = process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            assert result.success is True
            assert '0 of 2' in result.message


# ─── Retry Route ───


class TestRetryPdf:
    """Test the PDF retry route."""

    @patch('payroll_engine.services.payroll_service.generate_payslip')
    def test_retry_generates_pdf(self, mock_pdf, app):
        """Retry should generate PDF for a failed payslip."""
        cid, oid, rid = _setup(app)

        # First, complete payroll with all PDFs failing
        mock_pdf.side_effect = Exception('Font missing')
        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            # Verify PDFs failed
            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            assert payslip.pdf_file_path is None

        # Now retry one PDF — mock the retry route's import
        mock_pdf.side_effect = None
        mock_pdf.return_value = '/tmp/retry.pdf'

        with app.app_context():
            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            payslip_id = payslip.id

            client = app.test_client()
            client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})

            # The retry route imports generate_payslip from payroll_engine.pdf
            # We need to mock that import too
            with patch('payroll_engine.pdf.generate_payslip', return_value='/tmp/retry.pdf'):
                resp = client.post(
                    f'/payroll/{rid}/retry-pdf/{payslip_id}',
                    follow_redirects=True,
                )
                assert resp.status_code == 200
                assert b'generated' in resp.data.lower() or b'PDF' in resp.data

    def test_retry_rejects_already_has_pdf(self, app):
        """Retry should reject if payslip already has a PDF."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            # Complete payroll with PDFs
            from unittest.mock import patch as mp
            with mp('payroll_engine.services.payroll_service.generate_payslip') as mock_pdf:
                mock_pdf.return_value = '/tmp/test.pdf'
                from payroll_engine.services.payroll_service import process_payroll
                run = db.session.get(PayrollRun, rid)
                process_payroll(
                    run=run, company_id=cid, user_id=oid,
                    user_email='test@test.com', request_ip='127.0.0.1',
                )

            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            assert payslip.pdf_file_path is not None

            client = app.test_client()
            client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
            resp = client.post(
                f'/payroll/{rid}/retry-pdf/{payslip.id}',
                follow_redirects=True,
            )
            assert b'already has a PDF' in resp.data
