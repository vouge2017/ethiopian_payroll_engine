"""Tests for the in-app help system."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User


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
def client(app):
    return app.test_client()


def _login(client, app):
    """Create a user and log in."""
    with app.app_context():
        company = Company(name='HelpTestCo')
        db.session.add(company)
        db.session.flush()
        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.commit()
        cid, uid = company.id, owner.id

    client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
    return cid, uid


class TestHelpCenter:
    """Test the help center page."""

    def test_help_page_loads(self, client, app):
        """Help center page loads successfully."""
        _login(client, app)
        resp = client.get('/help')
        assert resp.status_code == 200
        assert b'Help Center' in resp.data

    def test_help_page_requires_login(self, client, app):
        """Help page redirects to login if not authenticated."""
        resp = client.get('/help', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.location

    def test_help_page_shows_all_categories(self, client, app):
        """Help page displays all FAQ categories."""
        _login(client, app)
        resp = client.get('/help')
        assert b'Tax' in resp.data
        assert b'Pension' in resp.data
        assert b'Overtime' in resp.data
        assert b'Leave' in resp.data
        assert b'Severance' in resp.data
        assert b'Payroll' in resp.data
        assert b'Compliance' in resp.data
        assert b'Account' in resp.data

    def test_help_page_shows_search_box(self, client, app):
        """Help page has a search input."""
        _login(client, app)
        resp = client.get('/help')
        assert b'helpSearch' in resp.data

    def test_help_page_section_filter(self, client, app):
        """Help page can filter to a specific section."""
        _login(client, app)
        resp = client.get('/help?section=tax')
        assert resp.status_code == 200


class TestHelpSearch:
    """Test the FAQ search endpoint."""

    def test_search_returns_results(self, client, app):
        """Search for a keyword returns matching FAQ items."""
        _login(client, app)
        resp = client.get('/help/search?q=tax')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'results' in data
        assert len(data['results']) > 0

    def test_search_pension(self, client, app):
        """Search for 'pension' returns pension-related items."""
        _login(client, app)
        resp = client.get('/help/search?q=pension')
        data = resp.get_json()
        assert any('pension' in r['question'].lower() or 'pension' in r['answer'].lower()
                    for r in data['results'])

    def test_search_overtime(self, client, app):
        """Search for 'overtime' returns overtime-related items."""
        _login(client, app)
        resp = client.get('/help/search?q=overtime')
        data = resp.get_json()
        assert len(data['results']) > 0

    def test_search_empty_query(self, client, app):
        """Empty search returns no results."""
        _login(client, app)
        resp = client.get('/help/search?q=')
        data = resp.get_json()
        assert data['results'] == []

    def test_search_short_query(self, client, app):
        """Query shorter than 2 chars returns no results (handled by JS, but endpoint still works)."""
        _login(client, app)
        resp = client.get('/help/search?q=a')
        data = resp.get_json()
        # Endpoint still returns results for 1-char (JS handles the debounce)
        assert 'results' in data

    def test_search_no_match(self, client, app):
        """Search for nonsense returns empty."""
        _login(client, app)
        resp = client.get('/help/search?q=xyzzy12345')
        data = resp.get_json()
        assert data['results'] == []

    def test_search_requires_login(self, client, app):
        """Search endpoint requires authentication."""
        resp = client.get('/help/search?q=tax', follow_redirects=False)
        assert resp.status_code == 302


class TestFaqData:
    """Test the FAQ data JSON endpoint."""

    def test_faq_data_returns_json(self, client, app):
        """FAQ data endpoint returns valid JSON."""
        _login(client, app)
        resp = client.get('/help/faq-data')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_faq_data_has_structure(self, client, app):
        """Each FAQ category has the expected structure."""
        _login(client, app)
        resp = client.get('/help/faq-data')
        data = resp.get_json()
        for cat in data:
            assert 'id' in cat
            assert 'title' in cat
            assert 'icon' in cat
            assert 'questions' in cat
            for item in cat['questions']:
                assert 'question' in item
                assert 'answer' in item

    def test_faq_data_covers_key_topics(self, client, app):
        """FAQ data covers the essential Ethiopian payroll topics."""
        _login(client, app)
        resp = client.get('/help/faq-data')
        data = resp.get_json()
        all_text = str(data).lower()
        assert 'tax bracket' in all_text
        assert 'pension' in all_text
        assert 'overtime' in all_text
        assert 'maternity' in all_text
        assert 'severance' in all_text
        assert 'erca' in all_text
