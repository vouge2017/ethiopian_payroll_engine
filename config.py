import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(basedir, 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', "redis:" + chr(47) + chr(47) + "localhost:6379/0")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        super().__init__()
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
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
