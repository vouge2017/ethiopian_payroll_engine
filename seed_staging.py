"""Create a small synthetic trial on an explicitly identified staging database.

Run after migrations:
    python seed_staging.py --database-name ethiopayroll_staging --database-host <confirmed-host>

Set ENABLE_SYNTHETIC_PREVIEW=true and unique PREVIEW_OWNER_PASSWORD and
PREVIEW_ACCOUNTANT_PASSWORD secrets first. Existing data is never reset.
"""

import argparse
import json
import os
from decimal import Decimal

WORKSPACES = ('Synthetic first-use preview', 'Synthetic payroll preview')
LOGINS = {'first_use_owner': '900000101', 'payroll_owner': '900000102', 'accountant': '900000103'}
SEED_ACTION = 'synthetic_preview_seeded'


class PreviewSeedError(RuntimeError):
    """A safe, actionable refusal without connection or credential details."""


def check_environment(database_name):
    if os.environ.get('FLASK_ENV') != 'staging':
        raise PreviewSeedError('Seeding requires FLASK_ENV=staging.')
    if os.environ.get('ENABLE_SYNTHETIC_PREVIEW', '').lower() != 'true':
        raise PreviewSeedError('Set ENABLE_SYNTHETIC_PREVIEW=true for this isolated trial.')
    if not database_name or not (database_name.endswith('_staging') or database_name.startswith('synthetic_preview_')):
        raise PreviewSeedError('Identify a staging database or a synthetic_preview_ test database.')


def seed_preview(app, *, database_name, database_host, owner_password, accountant_password):
    """Seed once under a database lock; refuse other environments and existing data."""
    check_environment(database_name)
    if not owner_password or not accountant_password or min(len(owner_password), len(accountant_password)) < 16:
        raise PreviewSeedError(
            'Provide unique preview passwords of at least 16 characters through environment secrets.'
        )
    if owner_password == accountant_password:
        raise PreviewSeedError('Owner and accountant passwords must be different.')

    from sqlalchemy import select, text

    from payroll_engine import db
    from payroll_engine.models import AuditLog, Company, Employee, User, UserCompany
    from payroll_engine.schema_health import inspect_schema, source_heads

    with app.app_context():
        if db.engine.dialect.name != 'postgresql' or db.engine.url.database != database_name:
            raise PreviewSeedError('The connected PostgreSQL database must match --database-name exactly.')
        if not database_host or db.engine.url.host != database_host:
            raise PreviewSeedError('The connected PostgreSQL host must match --database-host exactly.')
        with db.engine.connect() as connection, connection.begin():
            connection.exec_driver_sql('SET TRANSACTION READ ONLY')
            report = inspect_schema(connection, db.metadata, source_heads(app.extensions['migrate'].directory))
        if not report['revisions_match'] or report['missing_tables'] or report['missing_columns']:
            raise PreviewSeedError('Apply the real Alembic migrations before seeding.')
        try:
            # Serialize competing seed attempts without creating another control table.
            db.session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': 6260051393})
            companies = Company.query.all()
            if companies:
                if {company.name for company in companies} == set(WORKSPACES) and len(companies) == 2:
                    markers = [
                        AuditLog.query.filter_by(company_id=company.id, action=SEED_ACTION).first()
                        for company in companies
                    ]
                    if all(marker and marker.details.get('version') == 1 for marker in markers):
                        db.session.rollback()
                        return {'status': 'already_seeded', 'logins': LOGINS}
                raise PreviewSeedError('Database already contains company data. It will not be changed.')
            if db.session.execute(select(User.id).limit(1)).first():
                raise PreviewSeedError('Database already contains user data. It will not be changed.')

            first_use, payroll = [Company(name=name) for name in WORKSPACES]
            db.session.add_all([first_use, payroll])
            db.session.flush()
            from payroll_engine.catalog import seed_company_catalog

            for company in (first_use, payroll):
                seed_company_catalog(company.id, commit=False)
            users = []
            for identity, company, role, password in (
                ('first_use_owner', first_use, 'owner', owner_password),
                ('payroll_owner', payroll, 'owner', owner_password),
                ('accountant', payroll, 'accountant', accountant_password),
            ):
                user = User(
                    phone=LOGINS[identity],
                    email=f'{identity}@example.invalid',
                    company_id=company.id,
                    role=role,
                    first_name='Synthetic',
                    last_name=identity.replace('_', ' ').title(),
                )
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                db.session.add(UserCompany(user_id=user.id, company_id=company.id, role=role))
                users.append(user)
            for number, salary, allowance in (
                (1, '10000.00', '2000.00'),
                (2, '7000.00', '0.00'),
                (3, '12000.00', '500.00'),
            ):
                db.session.add(
                    Employee(
                        company_id=payroll.id,
                        employee_id=f'SYN{number:03d}',
                        name=f'Synthetic Employee {number}',
                        phone=f'90000020{number}',
                        basic_salary=Decimal(salary),
                        allowances=Decimal(allowance),
                        bank_or_telebirr=f'cbe:000000000000{number}',
                        tin=f'000000000{number}',
                    )
                )
            for company, user in ((first_use, users[0]), (payroll, users[1])):
                db.session.add(
                    AuditLog(
                        company_id=company.id,
                        user_id=user.id,
                        action=SEED_ACTION,
                        details={'version': 1, 'synthetic': True},
                    )
                )
            db.session.commit()
            return {'status': 'seeded', 'companies': 2, 'employees': 3, 'logins': LOGINS}
        except Exception:
            db.session.rollback()
            raise


def seed(*, database_name, database_host, owner_password, accountant_password):
    check_environment(database_name)
    from payroll_engine import create_app

    return seed_preview(
        create_app(),
        database_name=database_name,
        database_host=database_host,
        owner_password=owner_password,
        accountant_password=accountant_password,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-name', required=True)
    parser.add_argument('--database-host', required=True)
    arguments = parser.parse_args()
    try:
        result = seed(
            database_name=arguments.database_name,
            database_host=arguments.database_host,
            owner_password=os.environ.get('PREVIEW_OWNER_PASSWORD'),
            accountant_password=os.environ.get('PREVIEW_ACCOUNTANT_PASSWORD'),
        )
    except PreviewSeedError as error:
        parser.exit(1, f'Preview seed refused: {error}\n')
    except Exception as error:
        parser.exit(1, f'Preview seed failed ({type(error).__name__}). Existing data was not reset.\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
