"""
Tests for Platform Admin Control Plane & Support Operations Engine.
"""

from datetime import date, timedelta
import pytest
from flask import session
from payroll_engine import create_app, db
from payroll_engine.models import (
    User, Company, UserCompany, SupportTicket,
    SupportTicketMessage, PlatformAuditLog, ImpersonationSession
)


@pytest.fixture
def app():
    """Create Flask app for testing."""
    _app = create_app()
    _app.config['TESTING'] = True
    _app.config['WTF_CSRF_ENABLED'] = False
    with _app.app_context():
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()


@pytest.fixture
def super_admin_user(app):
    """Create a platform super admin user with a linked company."""
    with app.app_context():
        admin_company = Company(
            name='EthioPayroll Admin Corp',
            tin='9999999999',
            billing_status='active',
            plan_code='pro',
            paid_until=date.today() + timedelta(days=365)
        )
        db.session.add(admin_company)
        db.session.flush()

        admin = User(
            email='superadmin@ethiopayroll.com',
            phone='911000111',
            is_platform_admin=True,
            company_id=admin_company.id
        )
        admin.set_password('AdminPass123!')
        db.session.add(admin)
        db.session.flush()

        uc = UserCompany(user_id=admin.id, company_id=admin_company.id, role='owner')
        db.session.add(uc)
        db.session.commit()
        return admin.id


@pytest.fixture
def regular_tenant_data(app):
    """Create a company tenant and associated owner user."""
    with app.app_context():
        company = Company(
            name='Acme Ethiopia PLC',
            tin='0012345678',
            billing_status='active',
            plan_code='standard',
            paid_until=date.today() + timedelta(days=30)
        )
        db.session.add(company)
        db.session.flush()

        user = User(
            email='owner@acme.et',
            phone='911222333',
            is_platform_admin=False,
            company_id=company.id
        )
        user.set_password('OwnerPass123!')
        db.session.add(user)
        db.session.flush()

        uc = UserCompany(user_id=user.id, company_id=company.id, role='owner')
        db.session.add(uc)
        db.session.commit()

        return {'company_id': company.id, 'user_id': user.id}


def login_as(client, email, password='AdminPass123!'):
    """Helper to login a user."""
    return client.post('/auth/login', data={
        'login_id': email,
        'password': password
    }, follow_redirects=True)


class TestAdminAuthorization:
    """Test platform admin authorization guards."""

    def test_regular_user_blocked_from_admin(self, client, app, regular_tenant_data):
        """Regular user cannot access admin dashboard."""
        login_as(client, 'owner@acme.et', 'OwnerPass123!')
        res = client.get('/admin/dashboard', follow_redirects=True)
        assert b'Access denied' in res.data or b'Platform Administrator' in res.data

    def test_super_admin_access(self, client, app, super_admin_user):
        """Platform admin can access admin dashboard."""
        login_as(client, 'superadmin@ethiopayroll.com', 'AdminPass123!')
        res = client.get('/admin/dashboard')
        assert res.status_code == 200
        assert b'Platform Admin Control Plane' in res.data


class TestTenantManagement:
    """Test tenant directory and management actions."""

    def test_tenant_directory_and_toggle_status(self, client, app, super_admin_user, regular_tenant_data):
        """Super admin can view tenant list and toggle company billing status."""
        login_as(client, 'superadmin@ethiopayroll.com', 'AdminPass123!')

        # Directory view
        res = client.get('/admin/tenants')
        assert res.status_code == 200
        assert b'Acme Ethiopia PLC' in res.data

        # Toggle status to suspended
        cid = regular_tenant_data['company_id']
        res = client.post(f'/admin/tenants/{cid}/toggle-status', data={'status': 'suspended'}, follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            company = db.session.get(Company, cid)
            assert company.billing_status == 'suspended'

            # Check platform audit log entry created
            log = PlatformAuditLog.query.filter_by(action='tenant_status_change').first()
            assert log is not None
            assert log.target_company_id == cid


class TestSupportTicketWorkflow:
    """Test tenant ticket creation and admin ticket resolution thread."""

    def test_full_support_ticket_lifecycle(self, client, app, super_admin_user, regular_tenant_data):
        """Tenant opens ticket, admin replies and changes status."""
        cid = regular_tenant_data['company_id']

        # 1. Tenant logs in and creates ticket
        login_as(client, 'owner@acme.et', 'OwnerPass123!')

        res = client.post('/support/tickets/new', data={
            'subject': 'Pension rate inquiry for new hire',
            'category': 'payroll',
            'priority': 'high',
            'message_text': 'Does Proclamation 1268/2022 apply at 7% employee rate?'
        }, follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            ticket = SupportTicket.query.filter_by(company_id=cid).first()
            assert ticket is not None
            assert ticket.subject == 'Pension rate inquiry for new hire'
            assert ticket.status == 'open'
            ticket_id = ticket.id

        # 2. Super admin logs in, views queue and replies
        client.get('/auth/logout', follow_redirects=True)
        login_as(client, 'superadmin@ethiopayroll.com', 'AdminPass123!')
        res = client.get('/admin/tickets', follow_redirects=True)
        assert res.status_code == 200
        assert b'Pension rate inquiry' in res.data

        # Reply to ticket
        res = client.post(f'/admin/tickets/{ticket_id}/reply', data={
            'message_text': 'Yes, Proclamation 1268/2022 specifies 7% employee and 11% employer rates.',
            'is_internal_note': '0'
        }, follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            ticket = db.session.get(SupportTicket, ticket_id)
            assert ticket.status == 'waiting_on_customer'
            messages = ticket.messages.all()
            assert len(messages) == 2
            assert messages[1].is_admin_reply is True


class TestSupportAssistImpersonation:
    """Test support assist / impersonation mode initialization and termination."""

    def test_impersonation_session_flow(self, client, app, super_admin_user, regular_tenant_data):
        """Super admin starts support assist and stops assist session."""
        admin_id = super_admin_user
        target_uid = regular_tenant_data['user_id']
        cid = regular_tenant_data['company_id']

        login_as(client, 'superadmin@ethiopayroll.com', 'AdminPass123!')

        # Start Support Assist
        res = client.post('/admin/impersonate/start', data={
            'target_user_id': target_uid,
            'target_company_id': cid,
            'reason': 'Debugging tax calculation issue'
        }, follow_redirects=True)
        assert res.status_code == 200

        with client.session_transaction() as sess:
            assert sess.get('impersonator_admin_id') == admin_id
            assert sess.get('company_id') == cid

        with app.app_context():
            session_rec = ImpersonationSession.query.filter_by(is_active=True).first()
            assert session_rec is not None
            assert session_rec.admin_user_id == admin_id
            assert session_rec.target_user_id == target_uid

        # Stop Support Assist
        res = client.post('/admin/impersonate/stop', follow_redirects=True)
        assert res.status_code == 200

        with app.app_context():
            session_rec = ImpersonationSession.query.filter_by(admin_user_id=admin_id).first()
            assert session_rec.is_active is False
