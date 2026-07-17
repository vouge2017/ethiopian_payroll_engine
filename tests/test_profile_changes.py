"""
Profile change request tests — verifies the employee edit workflow:
- Employees can edit safe fields directly
- Sensitive fields create approval requests
- Admins can approve/reject
- Notifications are sent
- Audit logs are created
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date, datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, ProfileChangeRequest, Notification, AuditLog
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


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _setup(app):
    """Create company, admin user, employee user, and employee record."""
    with app.app_context():
        company = Company(name='ProfileTestCo')
        db.session.add(company)
        db.session.flush()

        admin = User(phone='0910000000', role='owner', company_id=company.id)
        admin.set_password('AdminPass1!')
        db.session.add(admin)
        db.session.flush()

        emp_user = User(phone='0910000001', role='employee', company_id=company.id)
        emp_user.set_password('EmpPass1!')
        db.session.add(emp_user)
        db.session.flush()

        emp = Employee(
            employee_id='EMP001',
            name='Tigist Haile',
            phone='0911111111',
            department='Finance',
            position='Accountant',
            basic_salary=10000,
            bank_account='1234567890',
            tin='0001234567',
            company_id=company.id,
            user_id=emp_user.id,
        )
        db.session.add(emp)
        db.session.commit()

        return company.id, admin.id, emp_user.id, emp.id


def _login(client, phone, password):
    """Log in a user via the auth route."""
    return client.post('/auth/login', data={
        'login_id': phone,
        'password': password,
    }, follow_redirects=True)


class TestProfileChangeRequestModel:
    """Tests for the ProfileChangeRequest model."""

    def test_model_creation(self, app):
        with app.app_context():
            company_id, admin_id, emp_user_id, emp_id = _setup(app)
            req = ProfileChangeRequest(
                company_id=company_id,
                employee_id=emp_id,
                field_name='phone',
                old_value='0911111111',
                new_value='0922222222',
                requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()

            assert req.id is not None
            assert req.status == 'pending'
            assert req.field_label == 'Phone Number'

    def test_editable_fields_defined(self):
        assert 'phone' in ProfileChangeRequest.EDITABLE_FIELDS
        assert 'bank_account' in ProfileChangeRequest.EDITABLE_FIELDS
        assert 'tin' in ProfileChangeRequest.EDITABLE_FIELDS
        assert 'name' in ProfileChangeRequest.EDITABLE_FIELDS
        assert 'address' in ProfileChangeRequest.EDITABLE_FIELDS

    def test_sensitive_vs_safe_fields(self):
        """Phone, bank, tin, name require approval. Address, emergency don't."""
        assert 'phone' in ProfileChangeRequest.SENSITIVE_FIELDS
        assert 'bank_account' in ProfileChangeRequest.SENSITIVE_FIELDS
        assert 'address' in ProfileChangeRequest.SAFE_FIELDS
        assert 'emergency_contact' in ProfileChangeRequest.SAFE_FIELDS

    def test_field_labels(self, app):
        with app.app_context():
            company_id, admin_id, emp_user_id, emp_id = _setup(app)
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='bank_account', old_value='old', new_value='new',
                requested_by=emp_user_id,
            )
            assert req.field_label == 'Bank Account'


class TestEmployeeProfileEdit:
    """Tests for the employee portal edit routes."""

    def test_edit_page_loads(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.get('/my/profile/edit')
        assert resp.status_code == 200
        assert b'Edit My Profile' in resp.data

    def test_safe_field_updates_immediately(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.post('/my/profile/edit', data={
            'address': 'Bole, Addis Ababa',
            'emergency_contact': 'Abebe Kebede',
            'emergency_phone': '0933333333',
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            emp = db.session.get(Employee, emp_id)
            assert emp.address == 'Bole, Addis Ababa'
            assert emp.emergency_contact == 'Abebe Kebede'
            assert emp.emergency_phone == '0933333333'

    def test_sensitive_field_creates_approval_request(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.post('/my/profile/edit', data={
            'phone': '0922222222',
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            emp = db.session.get(Employee, emp_id)
            # Employee phone should NOT be updated yet
            assert emp.phone == '0911111111'

            # But a change request should exist
            req = ProfileChangeRequest.query.filter_by(
                employee_id=emp_id, field_name='phone'
            ).first()
            assert req is not None
            assert req.status == 'pending'
            assert req.new_value == '0922222222'
            assert req.old_value == '0911111111'

    def test_no_change_submitted_if_value_same(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.post('/my/profile/edit', data={
            'phone': '0911111111',  # Same as current
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            reqs = ProfileChangeRequest.query.filter_by(
                employee_id=emp_id, field_name='phone'
            ).all()
            assert len(reqs) == 0

    def test_duplicate_pending_request_blocked(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        # First request
        client.post('/my/profile/edit', data={'phone': '0922222222'})
        # Second request for same field
        client.post('/my/profile/edit', data={'phone': '0933333333'})

        with app.app_context():
            pending = ProfileChangeRequest.query.filter_by(
                employee_id=emp_id, field_name='phone',
                status='pending'
            ).all()
            assert len(pending) == 1
            assert pending[0].new_value == '0922222222'


class TestAdminApproval:
    """Tests for admin approval/rejection routes."""

    def test_admin_can_list_changes(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='phone', old_value='0911111111',
                new_value='0922222222', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        resp = client.get('/profile-changes')
        assert resp.status_code == 200
        assert b'0922222222' in resp.data

    def test_admin_approve_applies_change(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='phone', old_value='0911111111',
                new_value='0922222222', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        resp = client.post(f'/profile-changes/{req_id}/approve',
                           follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            emp = db.session.get(Employee, emp_id)
            assert emp.phone == '0922222222'

            req = db.session.get(ProfileChangeRequest, req_id)
            assert req.status == 'approved'
            assert req.reviewed_by == admin_id
            assert req.reviewed_at is not None

    def test_admin_reject_with_reason(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='bank_account', old_value='1234567890',
                new_value='9999999999', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        resp = client.post(f'/profile-changes/{req_id}/reject',
                           data={'reason': 'Need bank statement'},
                           follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            emp = db.session.get(Employee, emp_id)
            assert emp.bank_account == '1234567890'

            req = db.session.get(ProfileChangeRequest, req_id)
            assert req.status == 'rejected'
            assert req.rejection_reason == 'Need bank statement'

    def test_approve_sends_notification(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='tin', old_value='0001234567',
                new_value='0009999999', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        client.post(f'/profile-changes/{req_id}/approve')

        with app.app_context():
            notif = Notification.query.filter_by(user_id=emp_user_id).first()
            assert notif is not None
            assert 'approved' in notif.message.lower()
            assert notif.type == 'success'

    def test_reject_sends_notification(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='name', old_value='Tigist Haile',
                new_value='Tigist H.', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        client.post(f'/profile-changes/{req_id}/reject',
                    data={'reason': 'Use full name'})

        with app.app_context():
            notif = Notification.query.filter_by(user_id=emp_user_id).first()
            assert notif is not None
            assert 'rejected' in notif.message.lower()
            assert notif.type == 'danger'

    def test_cannot_approve_already_reviewed(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='phone', old_value='0911111111',
                new_value='0922222222', requested_by=emp_user_id,
                status='approved',
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        resp = client.post(f'/profile-changes/{req_id}/approve',
                           follow_redirects=True)
        assert resp.status_code == 200
        assert b'already been reviewed' in resp.data

    def test_audit_log_created_on_approve(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='phone', old_value='0911111111',
                new_value='0922222222', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000000', 'AdminPass1!')
        client.post(f'/profile-changes/{req_id}/approve')

        with app.app_context():
            log = AuditLog.query.filter_by(
                action='profile_change_approved', company_id=company_id
            ).first()
            assert log is not None
            assert log.details['field'] == 'phone'
            assert log.details['employee_id'] == emp_id


class TestProfileViewWithPending:
    """Tests for profile view showing pending changes."""

    def test_profile_shows_pending_badge(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='phone', old_value='0911111111',
                new_value='0922222222', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()

        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.get('/my/profile')
        assert resp.status_code == 200
        assert b'Change pending' in resp.data

    def test_profile_shows_pending_summary(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='bank_account', old_value='1234567890',
                new_value='9999999999', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()

        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.get('/my/profile')
        assert resp.status_code == 200
        assert b'Pending Approval' in resp.data


class TestAccessControl:
    """Tests for role-based access control."""

    def test_employee_cannot_approve(self, app):
        company_id, admin_id, emp_user_id, emp_id = _setup(app)
        with app.app_context():
            req = ProfileChangeRequest(
                company_id=company_id, employee_id=emp_id,
                field_name='phone', old_value='0911111111',
                new_value='0922222222', requested_by=emp_user_id,
            )
            db.session.add(req)
            db.session.commit()
            req_id = req.id

        client = app.test_client()
        _login(client, '0910000001', 'EmpPass1!')
        resp = client.post(f'/profile-changes/{req_id}/approve',
                           follow_redirects=True)
        # Should be forbidden or redirected
        assert resp.status_code in (403, 200)
        # Employee phone should NOT change
        with app.app_context():
            emp = db.session.get(Employee, emp_id)
            assert emp.phone == '0911111111'

    def test_unauthenticated_redirected(self, app):
        client = app.test_client()
        resp = client.get('/my/profile', follow_redirects=False)
        assert resp.status_code in (302, 401)
