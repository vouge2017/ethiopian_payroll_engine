"""Membership discovery before company selection, and company access checks."""

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, TenantQuery, User, UserCompany


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def membership(app):
    with app.app_context():
        companies = [Company(name=name) for name in ('Company A', 'Company B', 'Company C')]
        db.session.add_all(companies)
        db.session.flush()
        user = User(phone='911234567', company_id=companies[0].id, role='owner')
        other = User(phone='922234567', company_id=companies[2].id, role='owner')
        for account in (user, other):
            account.set_password('SecurePass123!')
        db.session.add_all([user, other])
        db.session.flush()
        db.session.add_all(
            [
                UserCompany(user_id=user.id, company_id=companies[1].id, role='accountant'),
                UserCompany(user_id=other.id, company_id=companies[2].id, role='owner'),
            ]
        )
        db.session.commit()
        return user.id, other.id, [company.id for company in companies]


def test_memberships_are_user_scoped_before_company_selection(app, membership):
    """A user's memberships span companies without a company query context."""
    uid, other_uid, (_, linked, foreign) = membership
    with app.app_context():
        links = UserCompany.query.filter_by(user_id=uid).all()
        assert [(link.company_id, link.role) for link in links] == [(linked, 'accountant')]
        other_links = UserCompany.query.filter_by(user_id=other_uid).all()
        assert [link.company_id for link in other_links] == [foreign]


def test_company_filtered_memberships_still_work(app, membership):
    uid, _, (_, linked, _) = membership
    with app.app_context():
        links = UserCompany.query.filter_by(company_id=linked).all()
        assert [link.user_id for link in links] == [uid]


def test_company_access_and_roles_check_membership(app, membership):
    uid, _, (own, linked, foreign) = membership
    with app.app_context():
        user = db.session.get(User, uid)
        assert user.can_access_company(own)
        assert user.can_access_company(linked)
        assert not user.can_access_company(foreign)
        assert user.get_role_for_company(linked) == 'accountant'
        assert {company.id for company in user.companies} == {own, linked}


def test_switch_company_rejects_another_users_membership(app, membership):
    uid, _, (own, _, foreign) = membership
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(uid)
        session['_fresh'] = True
        session['active_company_id'] = own
    response = client.post(f'/switch-company/{foreign}')
    assert response.status_code == 403
    with client.session_transaction() as session:
        assert session['active_company_id'] == own
    with app.app_context():
        assert db.session.get(User, uid).company_id == own


def test_switch_company_accepts_own_membership(app, membership):
    uid, _, (own, linked, _) = membership
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(uid)
        session['_fresh'] = True
    response = client.post(f'/switch-company/{linked}')
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session['active_company_id'] == linked
    with app.app_context():
        assert db.session.get(User, uid).company_id == own


def test_payroll_tenant_models_remain_guarded(app):
    with app.app_context():
        assert Employee in TenantQuery._tenant_scoped_models
        with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
            Employee.query.all()
