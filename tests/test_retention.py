"""Tests for retention policy hooks."""
import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import date, datetime, timezone, timedelta

from payroll_engine import create_app, db
from payroll_engine.models import Employee, Company, User, TenantQuery, OvertimeEntry, PayrollDraft


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
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


def test_purge_expired_uploads(app):
    """Purge uploads older than retention window."""
    from payroll_engine.retention import purge_expired_uploads
    folder = app.config['UPLOAD_FOLDER']
    old_path = os.path.join(folder, 'old_file.csv')
    new_path = os.path.join(folder, 'new_file.csv')
    with open(old_path, 'w') as f:
        f.write('old')
    with open(new_path, 'w') as f:
        f.write('new')
    old_mtime = datetime.now() - timedelta(days=400)
    os.utime(old_path, (old_mtime.timestamp(), old_mtime.timestamp()))
    purged = purge_expired_uploads(app, folder)
    assert purged == 1
    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)


def test_purge_expired_drafts(app, ctx):
    """Purge payroll drafts older than retention window."""
    from payroll_engine.retention import purge_expired_drafts
    from payroll_engine.models import PayrollRun
    c = Company(name='RetentionCo')
    db.session.add(c)
    db.session.commit()
    run = PayrollRun(company_id=c.id, run_date=date.today(), status='review')
    db.session.add(run)
    db.session.commit()
    draft_old = PayrollDraft(
        payroll_run_id=run.id, employee_data='{}',
        created_at=datetime.now(timezone.utc) - timedelta(days=200),
    )
    draft_new = PayrollDraft(
        payroll_run_id=run.id, employee_data='{}',
    )
    db.session.add(draft_old)
    db.session.add(draft_new)
    db.session.commit()
    purged = purge_expired_drafts(app)
    assert purged >= 1
    assert db.session.get(PayrollDraft, draft_new.id) is not None
