"""Synthetic subprocess helper; not an operator recovery tool or an RQ worker."""

import json
import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy_utils.types.encrypted.padding import InvalidPaddingError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee

EMPLOYEE_VALUES = {
    'bank_account': '1000123456789',
    'tin': '1234567890',
    'fayda_fin': '123456789012',
}
WEBHOOK_VALUE = 'synthetic-webhook-value'
FIELDS = (*EMPLOYEE_VALUES, 'webhook_secret')


def assert_ciphertext(company_id, employee_id):
    """Raw SQL bypasses ORM decryption and also proves connectivity/row presence."""
    row = (
        db.session.execute(
            text(
                'SELECT e.bank_account, e.tin, e.fayda_fin, c.webhook_secret '
                'FROM employee e JOIN company c ON c.id = e.company_id '
                'WHERE e.id = :employee_id AND e.company_id = :company_id'
            ),
            {'employee_id': employee_id, 'company_id': company_id},
        )
        .mappings()
        .one()
    )
    for field, expected in {**EMPLOYEE_VALUES, 'webhook_secret': WEBHOOK_VALUE}.items():
        stored = bytes(row[field])
        assert stored and stored != expected.encode() and expected.encode() not in stored, (
            f'{field}: expected encrypted storage'
        )


def field_query(field, company_id, employee_id):
    if field == 'webhook_secret':
        return select(Company.webhook_secret).where(Company.id == company_id)
    return select(getattr(Employee, field)).where(Employee.id == employee_id, Employee.company_id == company_id)


def main():
    mode, company_arg = sys.argv[1:3]
    company_id = int(company_arg)
    app = create_app()
    with app.app_context():
        if mode == 'write':
            company = db.session.get(Company, company_id)
            assert company is not None
            company.webhook_secret = WEBHOOK_VALUE
            employee = Employee(
                company_id=company_id,
                employee_id='CROSS-PROCESS-KEY',
                name='Synthetic encryption subject',
                basic_salary=10000,
                allowances=0,
                **EMPLOYEE_VALUES,
            )
            db.session.add(employee)
            db.session.flush()
            employee_id = employee.id
            db.session.commit()
            db.session.remove()
            assert_ciphertext(company_id, employee_id)
            print(json.dumps({'employee_id': employee_id, 'ciphertext_fields': list(FIELDS)}))
            return

        employee_id = int(sys.argv[3])
        assert_ciphertext(company_id, employee_id)
        if mode == 'read':
            for field, expected in {**EMPLOYEE_VALUES, 'webhook_secret': WEBHOOK_VALUE}.items():
                actual = db.session.execute(field_query(field, company_id, employee_id)).scalar_one()
                assert actual == expected, f'{field}: decrypted value mismatch'
            print(json.dumps({'decrypted_fields': list(FIELDS)}))
        elif mode == 'wrong-key':
            field = sys.argv[4]
            assert field in FIELDS
            # Only catch errors around result decryption, after the raw query
            # proved connectivity and row presence. Startup/SQL errors propagate.
            try:
                db.session.execute(field_query(field, company_id, employee_id)).scalar_one()
            except InvalidPaddingError:
                error_type = 'InvalidPaddingError'
            except ValueError as exc:
                if str(exc) != 'Invalid decryption key':
                    raise
                error_type = 'Invalid decryption key'
            else:
                raise AssertionError(f'{field}: wrong key unexpectedly decrypted the value')
            print(json.dumps({'rejected_field': field, 'decryption_error': error_type}))
        else:
            raise ValueError('Unknown probe mode')


if __name__ == '__main__':
    main()
