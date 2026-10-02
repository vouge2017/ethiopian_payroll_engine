#!/usr/bin/env python3
"""P0-B encryption-recovery verification script.

Operates against a database pointed to by DATABASE_URL. Verifies that:

1. The DB_ENCRYPTION_KEY in the environment decrypts stored encrypted PII.
2. A fresh key (simulated key loss) fails to decrypt — proving the key
   is actually required and that encrypted data is not plaintext.

This does NOT contain or print the actual secret. It proves the key
can be recovered by an authorized operator by:

  a. The operator sets DB_ENCRYPTION_KEY to the escrowed value.
  b. Runs this script.
  c. The script reads a known test row (created by seed_staging.py or
     a previous run) and decrypts its `tin` and `bank_account` columns.
  d. Exit 0 + "ENCRYPTION OK" on success, exit 1 + an error message on failure.

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/db \
    DB_ENCRYPTION_KEY=<from escrow> \
    python3 scripts/verify_encryption_recovery.py --check

    DATABASE_URL=postgresql://user:pass@host:5432/db \
    DB_ENCRYPTION_KEY=<from escrow> \
    python3 scripts/verify_encryption_recovery.py --seed   # creates a test row

    DATABASE_URL=postgresql://user:pass@host:5432/db \
    DB_ENCRYPTION_KEY=<wrong-key> \
    python3 scripts/verify_encryption_recovery.py --check  # must exit 1
"""
import argparse
import os
import sys


def _check_env():
    db_url = os.environ.get('DATABASE_URL')
    enc_key = os.environ.get('DB_ENCRYPTION_KEY')
    if not db_url:
        print('ERROR: DATABASE_URL is not set.', file=sys.stderr)
        sys.exit(2)
    if not enc_key:
        print('ERROR: DB_ENCRYPTION_KEY is not set. This is the secret from escrow.', file=sys.stderr)
        sys.exit(2)


def seed():
    """Create a single test Company + Employee with known encrypted PII."""
    _check_env()
    from payroll_engine import create_app, db
    from payroll_engine.models import Company, Employee

    app = create_app()
    with app.app_context():
        co = Company(name='__Encryption Recovery Test Co__', country='ET', currency='ETB')
        db.session.add(co)
        db.session.flush()
        emp = Employee(
            company_id=co.id,
            employee_id='__ENC-TEST-001__',
            name='Recovery Test Subject',
            basic_salary=1000,
            bank_account='CBE-RECOVERY-VERIFY-1234567890',
            tin='TIN-RECOVERY-VERIFY',
            fayda_fin='FIN-RECOVERY-XYZ',
        )
        db.session.add(emp)
        db.session.commit()
        print(f'SEED OK: company_id={co.id} employee_id={emp.id}')
        print('Store company_id and employee_id in your escrow recovery notes.')
        print('These are the values the --check step reads back.')


def check(company_id=None, employee_id=None):
    """Decrypt a known row with the current key. Exit 0 on success."""
    _check_env()
    from payroll_engine import create_app, db
    from payroll_engine.models import Company, Employee
    from sqlalchemy.exc import SQLAlchemyError

    app = create_app()
    with app.app_context():
        try:
            if company_id and employee_id:
                co = db.session.get(Company, company_id)
                emp = Employee.query.filter_by(
                    id=employee_id, company_id=co.id if co else company_id,
                ).first() if co else None
            else:
                # No explicit row — find the test row by marker employee_id.
                emp = Employee.query.filter_by(
                    employee_id='__ENC-TEST-001__',
                ).first()

            if not emp:
                print(
                    'ERROR: No encrypted test row found. Run --seed first, or '
                    'provide --company-id and --employee-id.', file=sys.stderr,
                )
                sys.exit(1)

            # Force a fresh read to make sure decryption actually happens.
            db.session.expire_all()
            fresh = db.session.get(Employee, emp.id)
            _ = fresh.tin          # triggers decryption
            _ = fresh.bank_account
            _ = fresh.fayda_fin

            if fresh.tin != 'TIN-RECOVERY-VERIFY':
                print(
                    f'ERROR: Decryption produced wrong value for tin. '
                    f'Got {fresh.tin!r} — key may be wrong.', file=sys.stderr,
                )
                sys.exit(1)

            if fresh.bank_account != 'CBE-RECOVERY-VERIFY-1234567890':
                print(
                    f'ERROR: Decryption produced wrong value for bank_account. '
                    f'Got {fresh.bank_account!r}.', file=sys.stderr,
                )
                sys.exit(1)

            print(f'ENCRYPTION OK: company_id={fresh.company_id} employee_id={fresh.id}')
            print(f'  tin         = {fresh.tin}')
            print(f'  bank_account= {fresh.bank_account}')
            print(f'  fayda_fin   = {fresh.fayda_fin}')
            sys.exit(0)

        except Exception as e:
            # sqlalchemy_utils raises InvalidToken, cryptography raises
            # InvalidToken too — catch broadly; the point is "key works or
            # it doesn't", and any exception here means the key is wrong.
            print(
                'ERROR: Decryption failed — DB_ENCRYPTION_KEY is likely WRONG '
                f'or the escrowed key does not match this database. '
                f'Error: {e!r}', file=sys.stderr,
            )
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Verify DB_ENCRYPTION_KEY recovery')
    parser.add_argument('--seed', action='store_true', help='Create a test row with known encrypted values')
    parser.add_argument('--check', action='store_true', help='Verify the current key decrypts a test row')
    parser.add_argument('--company-id', type=int, default=None)
    parser.add_argument('--employee-id', type=int, default=None)
    args = parser.parse_args()

    if args.check:
        check(args.company_id, args.employee_id)
    elif args.seed:
        seed()
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == '__main__':
    main()
