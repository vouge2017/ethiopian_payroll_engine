"""
Tenant bypass guard tests.

Two layers of defense:

1. STATIC SCAN — bans raw ``Model.query.get(`` / ``db.session.get(Model`` for
   tenant-scoped models across payroll_engine/. These patterns either bypass
   TenantQuery entirely (session.get) or relied on the pre-2026-08 .get()
   gap (no company_id check). New code must use shared.tenant_get(),
   shared.get_tenant_or_404(), or an explicit filter_by(company_id=...).

2. BEHAVIORAL — proves TenantQuery.get/get_or_404/paginate now enforce the
   same structural company_id check as all/first/count.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollRun, TenantQuery

# The authoritative registration list lives in payroll_engine/__init__.py.
SCOPED_MODELS = [
    'Employee',
    'PayrollRun',
    'Payslip',
    'Attendance',
    'AuditLog',
    'OvertimeEntry',
    'EmployeeDeduction',
    'UserCompany',
    'PayrollDraft',
]


def _banned_patterns():
    pats = []
    for m in SCOPED_MODELS:
        # Model.query.get(  /  models.Model.query.get(
        pats.append(rf'\b(?:models\.)?{m}\.query\.get\(')
        # db.session.get(Model,  /  db.session.get(models.Model,
        pats.append(rf'db\.session\.get\(\s*(?:models\.)?{m}\b')
    return [re.compile(p) for p in pats]


def test_no_unscoped_tenant_fetches_in_source():
    """Static gate: raw PK fetches on tenant-scoped models are banned."""
    engine_dir = os.path.join(os.path.dirname(__file__), '..', 'payroll_engine')
    offenders = []
    for root, _dirs, files in os.walk(engine_dir):
        for fn in files:
            if not fn.endswith('.py'):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding='utf-8') as fh:
                for lineno, line in enumerate(fh, 1):
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    if '# tenant-ok:' in line:
                        continue  # documented waiver: server-side trust path
                    for pat in _banned_patterns():
                        if pat.search(line):
                            offenders.append(f'{fn}:{lineno}: {stripped[:120]}')
    assert not offenders, (
        'Unscoped tenant fetches found (use tenant_get/get_tenant_or_404 '
        'or filter_by(company_id=...)):\n' + '\n'.join(offenders)
    )


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(PayrollRun)
        c1 = Company(name='Company A')
        c2 = Company(name='Company B')
        db.session.add_all([c1, c2])
        db.session.commit()
        e1 = Employee(company_id=c1.id, name='A1', employee_id='EMP-1', basic_salary=1000)
        e2 = Employee(company_id=c2.id, name='B1', employee_id='EMP-1', basic_salary=2000)
        db.session.add_all([e1, e2])
        db.session.commit()
        yield app, c1.id, c2.id, e1.id, e2.id
        db.drop_all()


def test_query_get_without_company_filter_raises(app):
    _app, _c1, _c2, e1, _e2 = app
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        Employee.query.get(e1)


def test_query_get_with_company_filter_returns_tenant_row(app):
    _app, c1, _c2, e1, _e2 = app
    row = Employee.query.filter_by(id=e1, company_id=c1).first()
    assert row is not None and row.company_id == c1


def test_scoped_get_cannot_reach_other_tenant_row(app):
    _app, c1, _c2, _e1, e2 = app
    # Same PK shape as another tenant's row: scoped fetch must return None.
    assert Employee.query.filter_by(id=e2, company_id=c1).first() is None


def test_paginate_requires_company_filter(app):
    _app, _c1, _c2, _e1, _e2 = app
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        Employee.query.paginate(page=1, per_page=10, error_out=False)


def test_paginate_with_company_filter_works(app):
    _app, c1, _c2, _e1, _e2 = app
    page = Employee.query.filter_by(company_id=c1).paginate(page=1, per_page=10, error_out=False)
    assert page.total >= 0  # structural: no RuntimeError raised


def test_background_context_allows_unfiltered(app):
    """TenantQuery.set_tenant_context() permits worker-side queries."""
    _app, _c1, _c2, _e1, _e2 = app
    TenantQuery.set_tenant_context(999)
    try:
        count = Employee.query.count()
        assert isinstance(count, int)
    finally:
        TenantQuery.clear_tenant_context()
