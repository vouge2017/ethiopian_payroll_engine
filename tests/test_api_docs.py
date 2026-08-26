import pytest

from payroll_engine import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

def test_openapi_json(app):
    with app.test_client() as client:
        res = client.get('/api/v1/openapi.json')
        assert res.status_code == 200
        data = res.get_json()
        assert data is not None
        assert data['openapi'] == '3.0.3'
        assert data['info']['title'] == 'EthioPayroll API'
        assert '/employees' in data['paths']

def test_api_docs_html(app):
    with app.test_client() as client:
        res = client.get('/api/v1/docs')
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        assert '<div id="swagger-ui"></div>' in html
        assert 'swagger-ui-bundle.js' in html
