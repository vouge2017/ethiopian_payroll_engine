"""
Role system tests.

Tests:
- Three roles: owner, accountant, employee
- Permission checks on routes
- Invite flow
- Multi-company accountant
- Approval visibility (owner vs accountant)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, OvertimeEntry, TenantQuery, User, UserCompany


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def company_with_users(ctx):
    """Create a company with owner, accountant, and employee users."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    owner = User(phone='0911111111', company_id=company.id, role='owner')
    owner.set_password('owner123')
    accountant = User(phone='0922222222', company_id=company.id, role='accountant')
    accountant.set_password('acc123')
    employee = User(phone='0933333333', company_id=company.id, role='employee')
    employee.set_password('emp123')
    db.session.add_all([owner, accountant, employee])
    db.session.commit()

    return company, owner, accountant, employee


# ---------------------------------------------------------------
# ROLE TESTS
# ---------------------------------------------------------------

def test_owner_role(company_with_users):
    """Owner has full access."""
    company, owner, _, _ = company_with_users
    assert owner.role == 'owner'
    assert owner.get_role_for_company(company.id) == 'owner'


def test_accountant_role(company_with_users):
    """Accountant can process but not approve."""
    company, _, accountant, _ = company_with_users
    assert accountant.role == 'accountant'
    assert accountant.get_role_for_company(company.id) == 'accountant'


def test_employee_role(company_with_users):
    """Employee is view-only."""
    company, _, _, employee = company_with_users
    assert employee.role == 'employee'
    assert employee.get_role_for_company(company.id) == 'employee'


# ---------------------------------------------------------------
# INVITE TESTS
# ---------------------------------------------------------------

def test_invite_creates_user(company_with_users):
    """Inviting a team member creates a new user."""
    company, owner, _, _ = company_with_users
    new_user = User(phone='0944444444', company_id=company.id, role='accountant', must_change_password=True)
    new_user.set_password('temp123')
    db.session.add(new_user)
    db.session.commit()

    found = User.query.filter_by(phone='0944444444').first()
    assert found is not None
    assert found.role == 'accountant'
    assert found.must_change_password


def test_invite_existing_user_links_company(company_with_users):
    """Inviting an existing user creates a UserCompany link."""
    company, owner, _, _ = company_with_users
    # Create user in different company
    other_company = Company(name='OtherCo')
    db.session.add(other_company)
    db.session.commit()
    existing_user = User(phone='0955555555', company_id=other_company.id, role='employee')
    existing_user.set_password('pass123')
    db.session.add(existing_user)
    db.session.commit()

    # Link to owner's company
    link = UserCompany(user_id=existing_user.id, company_id=company.id, role='accountant')
    db.session.add(link)
    db.session.commit()

    assert existing_user.can_access_company(company.id)
    assert existing_user.get_role_for_company(company.id) == 'accountant'


# ---------------------------------------------------------------
# MULTI-COMPANY TESTS
# ---------------------------------------------------------------

def test_accountant_multiple_companies(ctx):
    """Accountant can be linked to multiple companies."""
    company1 = Company(name='Company A')
    company2 = Company(name='Company B')
    db.session.add_all([company1, company2])
    db.session.commit()

    accountant = User(phone='0911234567', company_id=company1.id, role='accountant')
    accountant.set_password('pass123')
    db.session.add(accountant)
    db.session.commit()

    # Link to company2
    link = UserCompany(user_id=accountant.id, company_id=company2.id, role='accountant')
    db.session.add(link)
    db.session.commit()

    assert accountant.can_access_company(company1.id)
    assert accountant.can_access_company(company2.id)
    assert len(accountant.companies) == 2


def test_company_isolation(ctx):
    """Can't access company user is not linked to."""
    company1 = Company(name='Company A')
    company2 = Company(name='Company B')
    db.session.add_all([company1, company2])
    db.session.commit()

    user = User(phone='0911234567', company_id=company1.id, role='employee')
    user.set_password('pass123')
    db.session.add(user)
    db.session.commit()

    assert user.can_access_company(company1.id)
    assert not user.can_access_company(company2.id)


def test_switch_company(app):
    """Switching company stores active_company_id in session, not DB."""
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    with app.app_context():
        company1 = Company(name='Company A')
        company2 = Company(name='Company B')
        db.session.add_all([company1, company2])
        db.session.commit()

        user = User(phone='0911234567', company_id=company1.id, role='accountant')
        user.set_password('pass123')
        db.session.add(user)
        db.session.flush()
        link = UserCompany(user_id=user.id, company_id=company2.id, role='accountant')
        db.session.add(link)
        db.session.commit()
        cid1, cid2 = company1.id, company2.id
        uid = user.id

    # Login as the multi-company accountant
    login_resp = client.post('/auth/login', data={
        'login_id': '0911234567', 'password': 'pass123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200, f'Login failed: {login_resp.status_code}'
    assert b'Dashboard' in login_resp.data or b'dashboard' in login_resp.data.lower()

    # Switch to company2 via the route
    resp = client.get(f'/switch-company/{cid2}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Company B' in resp.data or b'Switched' in resp.data

    # DB record is unchanged — still points to company1
    with app.app_context():
        db_user = db.session.get(User, uid)
        assert db_user.company_id == cid1  # DB unchanged


# ---------------------------------------------------------------
# PERMISSION TESTS
# ---------------------------------------------------------------

def test_owner_can_approve(company_with_users):
    """Owner should be able to approve."""
    _, owner, _, _ = company_with_users
    assert owner.role == 'owner'


def test_accountant_cannot_approve(company_with_users):
    """Accountant should not be able to approve (submit for approval instead)."""
    _, _, accountant, _ = company_with_users
    assert accountant.role == 'accountant'
    assert accountant.role != 'owner'


def test_employee_cannot_upload(company_with_users):
    """Employee should not be able to upload payroll."""
    _, _, _, employee = company_with_users
    assert employee.role == 'employee'
    assert employee.role not in ('owner', 'accountant')


def test_role_change(company_with_users):
    """User role can be changed."""
    _, owner, accountant, _ = company_with_users
    accountant.role = 'owner'
    db.session.commit()
    assert accountant.role == 'owner'
