"""
Celery app entry point for workers.

This file creates the Celery instance and discovers @shared_task tasks.
It must NOT import create_app() at module level to avoid circular imports.
"""
import os
from celery import Celery

celery = Celery(
    'ethiopian_payroll',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
)

# Auto-discover @shared_task decorated tasks in these modules
celery.autodiscover_tasks(['payroll_engine'])
