import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-change-in-production')
    ENABLE_DEMO_MODE = _env_bool('ENABLE_DEMO_MODE', default=False)
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'app.db'))
    # Fix postgres:// → postgresql:// for SQLAlchemy 2.x
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(basedir, 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB



class DevelopmentConfig(Config):
    DEBUG = True
    ENABLE_DEMO_MODE = _env_bool('ENABLE_DEMO_MODE', default=True)


class ProductionConfig(Config):
    DEBUG = False
    # Demo auto-login is never available in production — ignore env overrides.
    ENABLE_DEMO_MODE = False

    def __init__(self):
        super().__init__()
        # Hard-lock even if subclassing or env tries to re-enable it.
        self.ENABLE_DEMO_MODE = False
        if self.SECRET_KEY in ('dev-change-in-production', 'your-secret-key-here'):
            raise ValueError(
                "SECRET_KEY must be set to a real value in production. "
                "Generate one with: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if 'sqlite' in self.SQLALCHEMY_DATABASE_URI:
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string in production, "
                "not SQLite. Set the DATABASE_URL environment variable."
            )
        _db_enc_key = os.environ.get('DB_ENCRYPTION_KEY', '')
        if not _db_enc_key or _db_enc_key == 'dev-encryption-key-not-for-production-use-only-32b':
            raise ValueError(
                "DB_ENCRYPTION_KEY must be set to a real value in production. "
                "Generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'"
            )


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Respect DATABASE_URL if set (CI uses PostgreSQL); fall back to SQLite for local tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
