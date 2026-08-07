"""
UserCompany tenant isolation tests.

Proves that UserCompany is structurally enforced by TenantQuery —
a query without company_id must raise RuntimeError.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, TenantQuery, User, UserCompany


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_usercompany_registered_with_tenant_query(ctx):
    """UserCompany must be in the TenantQuery registry."""
    assert UserCompany in TenantQuery._tenant_scoped_models, 'UserCompany is not registered with TenantQuery'


def test_usercompany_query_without_company_id_raises(ctx):
    """Querying UserCompany without company_id must raise RuntimeError."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.flush()

    user = User(phone='0911234567', company_id=company.id, role='owner')
    user.set_password('pass')
    db.session.add(user)
    db.session.flush()

    link = UserCompany(user_id=user.id, company_id=company.id, role='owner')
    db.session.add(link)
    db.session.commit()

    # Query WITHOUT company_id — must raise
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        UserCompany.query.all()


def test_usercompany_query_with_company_id_works(ctx):
    """Querying UserCompany WITH company_id must work normally."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.flush()

    user = User(phone='0911234567', company_id=company.id, role='owner')
    user.set_password('pass')
    db.session.add(user)
    db.session.flush()

    link = UserCompany(user_id=user.id, company_id=company.id, role='owner')
    db.session.add(link)
    db.session.commit()

    # Query WITH company_id — must work
    results = UserCompany.query.filter_by(company_id=company.id).all()
    assert len(results) == 1
    assert results[0].user_id == user.id


def test_cross_tenant_usercompany_blocked(ctx):
    """Cannot access another company's UserCompany links."""
    company_a = Company(name='Company A')
    company_b = Company(name='Company B')
    db.session.add_all([company_a, company_b])
    db.session.flush()

    user_a = User(phone='0911111111', company_id=company_a.id, role='owner')
    user_a.set_password('pass')
    user_b = User(phone='0922222222', company_id=company_b.id, role='owner')
    user_b.set_password('pass')
    db.session.add_all([user_a, user_b])
    db.session.flush()

    link_a = UserCompany(user_id=user_a.id, company_id=company_a.id, role='owner')
    link_b = UserCompany(user_id=user_b.id, company_id=company_b.id, role='owner')
    db.session.add_all([link_a, link_b])
    db.session.commit()

    # Company A's admin can see their own links
    a_links = UserCompany.query.filter_by(company_id=company_a.id).all()
    assert len(a_links) == 1
    assert a_links[0].user_id == user_a.id

    # Company A's admin CANNOT see Company B's links without filter
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        UserCompany.query.filter_by(user_id=user_b.id).all()


def test_get_role_for_company_uses_filtered_query(ctx):
    """get_role_for_company must work (it already filters by company_id)."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.flush()

    user = User(phone='0911234567', company_id=company.id, role='owner')
    user.set_password('pass')
    db.session.add(user)
    db.session.flush()

    link = UserCompany(user_id=user.id, company_id=company.id, role='accountant')
    db.session.add(link)
    db.session.commit()

    # This query includes company_id — must work
    role = user.get_role_for_company(company.id)
    assert role == 'accountant'


def test_user_companies_property_works(ctx):
    """User.companies property must work across companies with TenantQuery."""
    company_a = Company(name='Company A')
    company_b = Company(name='Company B')
    db.session.add_all([company_a, company_b])
    db.session.flush()

    # User belongs to A as owner, linked to B as accountant
    user = User(phone='0911234567', company_id=company_a.id, role='owner')
    user.set_password('pass')
    db.session.add(user)
    db.session.flush()

    link = UserCompany(user_id=user.id, company_id=company_b.id, role='accountant')
    db.session.add(link)
    db.session.commit()

    # companies property should return both (sets tenant context internally)
    companies = user.companies
    company_ids = {c.id for c in companies}
    assert company_a.id in company_ids
    assert company_b.id in company_ids
    assert len(companies) == 2
