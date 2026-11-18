"""Audit-chain verification with concurrent PostgreSQL transactions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session
from test_pg_corrections import PG_URL

from payroll_engine.models import AuditLog, Company

pytest_plugins = ('test_pg_corrections',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def test_legacy_and_concurrent_audit_writes(database):
    url, _ = database
    engine = create_engine(url)
    with Session(engine) as session, session.begin():
        companies = [Company(name=uuid4().hex), Company(name=uuid4().hex)]
        session.add_all(companies)
        session.flush()
        cid, foreign = [company.id for company in companies]
        legacy = AuditLog(company_id=cid, action='legacy', details={'amount': '50.00'})
        session.execute(
            insert(AuditLog.__table__).values(
                company_id=cid,
                action=legacy.action,
                details=legacy.details,
                hash=legacy.compute_hash(),
            )
        )
    barrier = Barrier(2)

    def append(company_ids):
        with Session(engine) as session, session.begin():
            session.add_all([AuditLog(company_id=company, action='concurrent') for company in company_ids])
            barrier.wait(timeout=10)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(append, group) for group in ([cid, foreign, cid], [foreign, cid, cid])]
            for future in futures:
                future.result(timeout=30)
        with Session(engine) as session:
            for company, expected in [(cid, 5), (foreign, 2)]:
                rows = session.query(AuditLog).filter_by(company_id=company).order_by(AuditLog.id).all()
                assert len(rows) == expected
                assert [r.previous_hash for r in rows] == [None, *(r.hash for r in rows[:-1])]
                assert all(r.hash == r.compute_hash() for r in rows)
    finally:
        engine.dispose()


def test_postgres_prevents_rewriting_salary_evidence(database):
    from alembic import command
    from sqlalchemy import delete, update
    from sqlalchemy.exc import DBAPIError

    url, cfg = database
    engine = create_engine(url)
    try:
        with Session(engine) as session, session.begin():
            company = Company(name=uuid4().hex)
            session.add(company)
            session.flush()
            row = AuditLog(company_id=company.id, action='salary_changed', details={'reason': {'note': 'Original'}})
            session.add(row)
            session.flush()
            row_id = row.id

        for change in (
            update(AuditLog).where(AuditLog.id == row_id).values(details={'reason': {'note': 'Rewritten'}}),
            delete(AuditLog).where(AuditLog.id == row_id),
        ):
            with (
                pytest.raises(DBAPIError, match='Salary audit records cannot be modified or deleted'),
                engine.begin() as connection,
            ):
                connection.execute(change)
        # A schema rollback must preserve the version marker and audit evidence.
        command.downgrade(cfg, 'k20261104a01')
        command.upgrade(cfg, 'head')
        with Session(engine) as session:
            row = session.get(AuditLog, row_id)
            assert row.details['reason']['note'] == 'Original'
            assert row.hash == row.compute_hash()
    finally:
        engine.dispose()
