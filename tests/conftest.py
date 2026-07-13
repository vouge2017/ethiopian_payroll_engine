"""Shared test configuration — runs before all test modules."""
import os

os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
