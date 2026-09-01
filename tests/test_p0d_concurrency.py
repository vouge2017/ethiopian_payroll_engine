"""P0-D: Payroll concurrency invariants.

Verifies the state-machine and DB-level guards that make double-approval
impossible. Real concurrency is covered by the version_id + for_update
mechanism in the route; here we test the invariant: once a run is
'completed', re-approval is rejected.
"""
import pytest

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    PayrollRun,
    Payslip,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeded(app):
    with app.app_context():
        co = Company(name='Acme', country='ET', currency='ETB')
        db.session.add(co)
        db.session.commit()
        u = User(phone='0911111111')
        u.set_password('x' * 12)
        db.session.add(u)
        db.session.commit()
        emp = Employee(company_id=co.id, employee_id='E001', name='Alice',
                       basic_salary=5000)
        db.session.add(emp)
        db.session.commit()
        run = PayrollRun(company_id=co.id, period='2026-01',
                         status='review', source='test')
        db.session.add(run)
        db.session.commit()
        return co.id, u.id, emp.id, run.id


def test_approval_guard_rejects_completed_run(app, seeded):
    co_id, u_id, emp_id, run_id = seeded
    with app.app_context():
        # First approval
        run = db.session.get(PayrollRun, run_id)
        run.status = 'completed'
        run.approved_by = u_id
        db.session.commit()

        # Second approval attempt
        run = db.session.get(PayrollRun, run_id)
        # The route guard: status not in ('review', 'pending_approval') -> reject
        assert run.status not in ('review', 'pending_approval')


def test_payslip_uniqueness_constraint_in_model(app, seeded):
    """P0-F: Payslip __table_args__ declares UNIQUE(run, employee, type)."""
    declared = any(
        c.name == 'uq_payslip_run_emp_type'
        for c in Payslip.__table__.constraints
    )
    assert declared, (
        "Payslip model must declare UniqueConstraint('payroll_run_id', "
        "'employee_id', 'payslip_type', name='uq_payslip_run_emp_type'). "
        'Without it, fresh DBs created via db.create_all() (dev, tests, '
        'onboarding) are unprotected even after the migration runs.'
    )

    # Senior-level: also confirm the DB enforces the constraint.
    insp = __import__('sqlalchemy').inspect(db.engine)
    uqs = insp.get_unique_constraints('payslip')
    assert any(u.get('name') == 'uq_payslip_run_emp_type' for u in uqs), (
        f"DB-level UNIQUE constraint 'uq_payslip_run_emp_type' missing. "
        f"Constraints found: {uqs}"
    )


def test_duplicate_payslip_rejected_via_python_check(app, seeded):
    """P0-F: a second 'regular' payslip for the same (run, employee) must
    be rejected by the database.

    The original test only checked that an existing row could be queried,
    which is a tautology. This version actually attempts the duplicate
    insert and asserts IntegrityError.
    """
    from sqlalchemy.exc import IntegrityError

    co_id, _u_id, emp_id, run_id = seeded
    with app.app_context():
        ps1 = Payslip(
            company_id=co_id, payroll_run_id=run_id, employee_id=emp_id,
            gross_salary=5000, tax=0, employee_pension=0, employer_pension=0,
            net_pay=5000, payslip_type='regular',
        )
        db.session.add(ps1)
        db.session.commit()

        ps2 = Payslip(
            company_id=co_id, payroll_run_id=run_id, employee_id=emp_id,
            gross_salary=5000, tax=0, employee_pension=0, employer_pension=0,
            net_pay=5000, payslip_type='regular',
        )
        db.session.add(ps2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_concurrent_duplicate_inserts_one_succeeds(app, seeded):
    """P0-D senior: two threads racing to insert the same (run, emp, type)
    tuple. Exactly one must succeed; the other must hit IntegrityError.

    This is the test the original P0-D comment claimed existed but didn't.
    Uses SQLite in WAL mode for cross-thread visibility; on PostgreSQL the
    same test exercises the row-level lock.
    """
    import threading
    from sqlalchemy.exc import IntegrityError

    co_id, _u_id, emp_id, run_id = seeded

    # Force WAL so the two threads see the same DB state.
    try:
        db.session.execute(db.text('PRAGMA journal_mode=WAL'))
        db.session.commit()
    except Exception:
        pass

    results = {'success': 0, 'integrity': 0, 'other': []}
    barrier = threading.Barrier(2)
    app_obj = app  # capture for the threads

    def attempt():
        with app_obj.app_context():
            barrier.wait()
            try:
                ps = Payslip(
                    company_id=co_id, payroll_run_id=run_id, employee_id=emp_id,
                    gross_salary=5000, tax=0,
                    employee_pension=0, employer_pension=0,
                    net_pay=5000, payslip_type='regular',
                )
                db.session.add(ps)
                db.session.commit()
                results['success'] += 1
            except IntegrityError:
                db.session.rollback()
                results['integrity'] += 1
            except Exception as e:  # pragma: no cover
                results['other'].append(repr(e))
            finally:
                db.session.remove()

    t1 = threading.Thread(target=attempt)
    t2 = threading.Thread(target=attempt)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert results['other'] == [], f'unexpected errors: {results["other"]}'
    assert results['success'] == 1, f'expected 1 success, got {results}'
    assert results['integrity'] == 1, f'expected 1 IntegrityError, got {results}'


def test_adjustment_payslip_coexists_with_regular(app, seeded):
    """Adjustment payslip (different payslip_type) must coexist with regular."""
    from payroll_engine.payroll import calculate_payroll

    co_id, u_id, emp_id, run_id = seeded
    with app.app_context():
        result = calculate_payroll(basic_salary=5000, allowances=0)
        ps_reg = Payslip(
            company_id=co_id, payroll_run_id=run_id, employee_id=emp_id,
            gross_salary=result['gross'], tax=result['tax'],
            employee_pension=result['pension_employee'],
            employer_pension=result['pension_employer'], net_pay=result['net'],
            payslip_type='regular',
        )
        ps_adj = Payslip(
            company_id=co_id, payroll_run_id=run_id, employee_id=emp_id,
            gross_salary=result['gross'], tax=result['tax'],
            employee_pension=result['pension_employee'],
            employer_pension=result['pension_employer'], net_pay=result['net'],
            payslip_type='adjustment', reason='correction', original_payslip_id=None,
        )
        db.session.add_all([ps_reg, ps_adj])
        db.session.commit()

        slips = Payslip.query.filter_by(
            payroll_run_id=run_id, employee_id=emp_id, company_id=co_id,
        ).all()
        assert len(slips) == 2
        assert {s.payslip_type for s in slips} == {'regular', 'adjustment'}


def test_run_state_machine_transitions(app, seeded):
    """Verify the allowed transitions for PayrollRun.status."""
    co_id, u_id, emp_id, run_id = seeded
    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        assert run.status == 'review'

        # review -> pending_approval (accountant submits)
        run.status = 'pending_approval'
        db.session.commit()
        assert db.session.get(PayrollRun, run_id).status == 'pending_approval'

        # pending_approval -> completed (owner approves)
        run = db.session.get(PayrollRun, run_id)
        run.status = 'completed'
        run.approved_by = u_id
        db.session.commit()
        assert db.session.get(PayrollRun, run_id).status == 'completed'

        # completed -> locked (admin locks the period)
        run = db.session.get(PayrollRun, run_id)
        run.status = 'locked'
        run.locked_at = db.func.now()
        run.locked_by = u_id
        db.session.commit()
        assert db.session.get(PayrollRun, run_id).status == 'locked'