"""Environment policy checks — production startup guards."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestProductionConfigGuards:
    def test_production_forces_demo_off(self, monkeypatch):
        monkeypatch.setenv('SECRET_KEY', 'a-real-secret-key-32-chars-minimum-here!')
        monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
        monkeypatch.setenv('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
        import importlib

        import config as cfg_mod
        importlib.reload(cfg_mod)
        from config import ProductionConfig
        cfg = ProductionConfig()
        assert cfg.ENABLE_DEMO_MODE is False

    def test_development_allows_demo(self):
        from config import DevelopmentConfig
        cfg = DevelopmentConfig()
        assert cfg.ENABLE_DEMO_MODE is True


class TestCreateAppProductionGuard:
    def test_create_app_production_raises_on_insecure(self, monkeypatch):
        monkeypatch.setenv('FLASK_ENV', 'production')
        monkeypatch.setenv('SECRET_KEY', 'dev-change-in-production')
        monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
        monkeypatch.delenv('DB_ENCRYPTION_KEY', raising=False)
        from payroll_engine import create_app
        with pytest.raises((ValueError, RuntimeError)):
            create_app()

    def test_create_app_development_succeeds(self, monkeypatch):
        monkeypatch.setenv('FLASK_ENV', 'development')
        monkeypatch.setenv('SECRET_KEY', 'test-secret')
        from payroll_engine import create_app
        app = create_app()
        assert app is not None
        assert app.config.get('ENABLE_DEMO_MODE') is True
