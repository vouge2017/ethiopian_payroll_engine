"""
Performance benchmarks — trust components and dashboard at realistic scale.

Tests the actual compute path with real data (not mocks).
Employee counts: 50, 200, 500 (realistic for Ethiopian businesses).

Thresholds:
- Trust components: <2s for 200 employees, <5s for 500
- Dashboard API: <3s for 200 employees
- Full payroll cycle: <10s for 200 employees
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User, Employee, PayrollRun, Payslip
from payroll_engine.change_summary import compute_change_summary
from payroll_engine.evidence import collect_evidence
from payroll_engine.exceptions import classify_exceptions
from payroll_engine.narrative import generate_narrative
from payroll_engine import trust_cache
from decimal import Decimal
from datetime import date


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _seed_employees(company_id, count):
    """Create N employees with realistic Ethiopian data."""
    employees = []
    for i in range(count):
        emp = Employee(
            employee_id=f'EMP-{i:04d}',
            name=f'Employee {i}',
            basic_salary=Decimal(str(5000 + (i * 100) % 20000)),
            allowances=Decimal('0'),
            bank_or_telebirr=f'1000{i:09d}'[:13],
            tin=f'TIN{i:06d}',
            phone=f'+251911{i:06d}'[:13],
            company_id=company_id,
        )
        db.session.add(emp)
        employees.append(emp)
    db.session.commit()
    return employees


def _seed_payroll(company_id, employees, period='2018-10'):
    """Create a completed payroll run with payslips for all employees."""
    run = PayrollRun(
        company_id=company_id,
        run_date=date(2026, 8, 1),
        status='completed',
        period=period,
        reference=f'PR-{period}-001',
    )
    db.session.add(run)
    db.session.flush()

    for emp in employees:
        gross = emp.basic_salary + emp.allowances
        tax = gross * Decimal('0.15')
        pension = emp.basic_salary * Decimal('0.07')
        net = gross - tax - pension
        ps = Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            gross_salary=gross,
            tax=tax,
            employee_pension=pension,
            employer_pension=pension,
            net_pay=net,
        )
        db.session.add(ps)
    db.session.commit()
    return run


# ─────────────────────────────────────────
# Trust Component Benchmarks
# ─────────────────────────────────────────

class TestTrustComponentBenchmarks:
    """Benchmark trust components at realistic employee counts."""

    @pytest.mark.parametrize("emp_count", [50, 200, 500])
    def test_change_summary_performance(self, app, emp_count):
        """Change Summary should compute within threshold."""
        with app.app_context():
            company = Company(name='Benchmark PLC', tin='123')
            db.session.add(company)
            db.session.flush()

            employees = _seed_employees(company.id, emp_count)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            from payroll_engine import models as trust_models
            start = time.perf_counter()
            result = compute_change_summary(run.id, company.id, db, trust_models)
            elapsed = time.perf_counter() - start

            assert result is not None
            assert result.current_employee_count == emp_count

            threshold = 2.0 if emp_count <= 200 else 5.0
            print(f"\n  Change Summary ({emp_count} employees): {elapsed:.3f}s (threshold: {threshold}s)")
            assert elapsed < threshold, (
                f'Change Summary with {emp_count} employees took {elapsed:.2f}s, '
                f'exceeding threshold of {threshold}s'
            )

    @pytest.mark.parametrize("emp_count", [50, 200, 500])
    def test_evidence_performance(self, app, emp_count):
        """Evidence collection should complete within threshold."""
        with app.app_context():
            company = Company(name='Benchmark PLC', tin='123')
            db.session.add(company)
            db.session.flush()

            employees = _seed_employees(company.id, emp_count)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            from payroll_engine import models as trust_models
            change = compute_change_summary(run.id, company.id, db, trust_models)

            start = time.perf_counter()
            evidence = collect_evidence(run.id, company.id, db, trust_models, change)
            elapsed = time.perf_counter() - start

            assert evidence is not None
            threshold = 2.0 if emp_count <= 200 else 5.0
            print(f"\n  Evidence ({emp_count} employees): {elapsed:.3f}s (threshold: {threshold}s)")
            assert elapsed < threshold, (
                f'Evidence with {emp_count} employees took {elapsed:.2f}s, '
                f'exceeding threshold of {threshold}s'
            )

    @pytest.mark.parametrize("emp_count", [50, 200, 500])
    def test_exceptions_performance(self, app, emp_count):
        """Exception classification should complete within threshold."""
        with app.app_context():
            company = Company(name='Benchmark PLC', tin='123')
            db.session.add(company)
            db.session.flush()

            employees = _seed_employees(company.id, emp_count)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            from payroll_engine import models as trust_models
            change = compute_change_summary(run.id, company.id, db, trust_models)

            start = time.perf_counter()
            exceptions = classify_exceptions(run.id, company.id, db, trust_models, change)
            elapsed = time.perf_counter() - start

            assert exceptions is not None
            threshold = 2.0 if emp_count <= 200 else 5.0
            print(f"\n  Exceptions ({emp_count} employees): {elapsed:.3f}s (threshold: {threshold}s)")
            assert elapsed < threshold, (
                f'Exceptions with {emp_count} employees took {elapsed:.2f}s, '
                f'exceeding threshold of {threshold}s'
            )

    @pytest.mark.parametrize("emp_count", [50, 200, 500])
    def test_all_trust_components_combined(self, app, emp_count):
        """All trust components together should complete within threshold."""
        with app.app_context():
            company = Company(name='Benchmark PLC', tin='123')
            db.session.add(company)
            db.session.flush()

            employees = _seed_employees(company.id, emp_count)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            from payroll_engine import models as trust_models

            start = time.perf_counter()
            change = compute_change_summary(run.id, company.id, db, trust_models)
            narrative = generate_narrative(change)
            evidence = collect_evidence(run.id, company.id, db, trust_models, change)
            exceptions = classify_exceptions(run.id, company.id, db, trust_models, change)
            elapsed = time.perf_counter() - start

            assert change is not None
            assert len(narrative) > 0
            assert evidence is not None
            assert exceptions is not None

            threshold = 3.0 if emp_count <= 200 else 8.0
            print(f"\n  All trust components ({emp_count} employees): {elapsed:.3f}s (threshold: {threshold}s)")
            assert elapsed < threshold, (
                f'All trust components with {emp_count} employees took {elapsed:.2f}s, '
                f'exceeding threshold of {threshold}s'
            )


# ─────────────────────────────────────────
# Cache Performance
# ─────────────────────────────────────────

class TestCachePerformance:
    """Benchmark cache hit vs miss performance."""

    def test_cache_hit_is_instant(self, app):
        """Cached results should return in <1ms."""
        with app.app_context():
            company = Company(name='Cache PLC', tin='123')
            db.session.add(company)
            db.session.flush()

            employees = _seed_employees(company.id, 200)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            from payroll_engine import models as trust_models
            # First call — cache miss
            change = compute_change_summary(run.id, company.id, db, trust_models)
            trust_cache.put_change_summary(run.id, company.id, change)

            # Second call — cache hit
            start = time.perf_counter()
            cached = trust_cache.get_change_summary(run.id, company.id)
            elapsed = time.perf_counter() - start

            assert cached is not None
            print(f"\n  Cache hit: {elapsed*1000:.3f}ms")
            assert elapsed < 0.001, f'Cache hit took {elapsed*1000:.2f}ms, should be <1ms'


# ─────────────────────────────────────────
# Dashboard API Benchmark
# ─────────────────────────────────────────

class TestDashboardBenchmarks:
    """Benchmark dashboard API response time."""

    @pytest.mark.parametrize("emp_count", [50, 200, 500])
    def test_dashboard_api_performance(self, app, emp_count):
        """Dashboard API should respond within threshold."""
        with app.app_context():
            client = app.test_client()
            client.post('/auth/register', data={
                'company_name': 'Benchmark PLC',
                'phone': '0911123456',
                'password': 'TestPass123!',
                'password2': 'TestPass123!',
            }, follow_redirects=True)

            company = Company.query.filter_by(name='Benchmark PLC').first()
            employees = _seed_employees(company.id, emp_count)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            client.post('/auth/login', data={
                'login_id': '0911123456',
                'password': 'TestPass123!',
            }, follow_redirects=True)

            start = time.perf_counter()
            resp = client.get('/payroll/api/dashboard')
            elapsed = time.perf_counter() - start

            assert resp.status_code == 200
            threshold = 3.0 if emp_count <= 200 else 6.0
            print(f"\n  Dashboard API ({emp_count} employees): {elapsed:.3f}s (threshold: {threshold}s)")
            assert elapsed < threshold, (
                f'Dashboard API with {emp_count} employees took {elapsed:.2f}s, '
                f'exceeding threshold of {threshold}s'
            )


# ─────────────────────────────────────────
# Full Cycle Benchmark
# ─────────────────────────────────────────

class TestFullCycleBenchmark:
    """Benchmark the full payroll review cycle."""

    def test_full_review_cycle_200_employees(self, app):
        """Full review cycle (compute all + render) should complete in <10s."""
        with app.app_context():
            client = app.test_client()
            client.post('/auth/register', data={
                'company_name': 'Benchmark PLC',
                'phone': '0911123456',
                'password': 'TestPass123!',
                'password2': 'TestPass123!',
            }, follow_redirects=True)

            company = Company.query.filter_by(name='Benchmark PLC').first()
            employees = _seed_employees(company.id, 200)
            run = _seed_payroll(company.id, employees)
            trust_cache.invalidate_trust_cache()

            client.post('/auth/login', data={
                'login_id': '0911123456',
                'password': 'TestPass123!',
            }, follow_redirects=True)

            start = time.perf_counter()
            resp = client.get(f'/payroll/runs/{run.id}/review')
            elapsed = time.perf_counter() - start

            assert resp.status_code == 200
            print(f"\n  Full review cycle (200 employees): {elapsed:.3f}s (threshold: 10s)")
            assert elapsed < 10.0, (
                f'Full review cycle with 200 employees took {elapsed:.2f}s, '
                f'exceeding threshold of 10s'
            )
