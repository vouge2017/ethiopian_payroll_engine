"""
Tests for lazy PDF generation — approval no longer generates PDFs.
PDFs are generated on-demand at download time via _ensure_pdf().
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
from unittest.mock import patch

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    PayrollDraft,
    PayrollRun,
    Payslip,
    User,
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


# ─── Lazy PDF Generation ───


class TestLazyPdfGeneration:
    """Approval no longer generates PDFs. Payslips get pdf_status='not_generated'."""

    def test_approval_succeeds_without_pdf_generation(self, app):
        """Approval should complete without generating any PDFs."""
        cid, oid, rid = _setup(app)

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            result = process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            assert result.success is True
            assert '2 employees paid' in result.message

    def test_payslips_created_with_not_generated_status(self, app):
        """Payslips should be created with pdf_status='not_generated'."""
        cid, oid, rid = _setup(app)

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            payslips = Payslip.query.filter_by(payroll_run_id=rid).all()
            assert len(payslips) == 2
            for ps in payslips:
                assert ps.pdf_file_path is None
                assert ps.pdf_status == 'not_generated'

    def test_approval_message_mentions_lazy_pdf(self, app):
        """Success message should indicate PDFs will be generated on download."""
        cid, oid, rid = _setup(app)

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            result = process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            assert result.success is True
            assert 'PDF' in result.message or 'download' in result.message.lower()


# ─── Retry Route ───


class TestRetryPdf:
    """Test the PDF retry route with lazy generation."""

    def test_retry_generates_pdf(self, app):
        """Retry should generate PDF for a payslip with pdf_status='not_generated'."""
        cid, oid, rid = _setup(app)

        # First, complete payroll (no PDFs generated)
        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            assert payslip.pdf_status == 'not_generated'
            payslip_id = payslip.id

        # Now retry — mock _ensure_pdf to simulate successful generation
        with app.app_context():
            client = app.test_client()
            client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})

            with patch('payroll_engine.payroll_bp._ensure_pdf', return_value='/tmp/retry.pdf'):
                resp = client.post(
                    f'/payroll/{rid}/retry-pdf/{payslip_id}',
                    follow_redirects=True,
                )
                assert resp.status_code == 200
                assert b'generated' in resp.data.lower() or b'PDF' in resp.data

    def test_retry_rejects_already_generated(self, app):
        """Retry should reject if payslip already has a generated PDF."""
        import tempfile
        cid, oid, rid = _setup(app)

        from payroll_engine.services.payroll_service import process_payroll
        with app.app_context():
            run = db.session.get(PayrollRun, rid)
            process_payroll(
                run=run, company_id=cid, user_id=oid,
                user_email='test@test.com', request_ip='127.0.0.1',
            )

            # Simulate a previously generated PDF (file must exist on disk)
            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp.write(b'%PDF-1.4 test')
            tmp.close()
            payslip.pdf_status = 'generated'
            payslip.pdf_file_path = tmp.name
            db.session.commit()

            client = app.test_client()
            client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
            resp = client.post(
                f'/payroll/{rid}/retry-pdf/{payslip.id}',
                follow_redirects=True,
            )
            assert b'already has a PDF' in resp.data

            os.unlink(tmp.name)
