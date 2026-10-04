"""Persistent, loopback-only synthetic monthly trial; never a deployment launcher."""

import argparse
import json
import os
import re
import secrets
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / 'local-evidence' / 'founder-trial'
STATE_FILE = STATE_DIR / 'state.json'
CONTROL_URL = 'postgresql://payroll_test@127.0.0.1:55439/payroll_pr8_20261003'
PORT = 5058
sys.path.insert(0, str(ROOT))


def read_state():
    state = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    if not re.fullmatch(r'payroll_founder_trial_[0-9a-f]{32}', state.get('database', '')):
        raise RuntimeError('Invalid trial database identity; no database was changed.')
    if not state.get('ready'):
        raise RuntimeError('Trial setup is incomplete. Preserve the state file and ask for recovery; do not reset it.')
    return state


def database_url(state):
    from sqlalchemy.engine import make_url

    return make_url(CONTROL_URL).set(database=state['database'])


def configure_environment(state):
    # This dedicated child process must not inherit live integrations or database settings.
    keep = {
        'PATH',
        'SYSTEMROOT',
        'WINDIR',
        'COMSPEC',
        'TEMP',
        'TMP',
        'USERPROFILE',
        'HOMEDRIVE',
        'HOMEPATH',
        'APPDATA',
        'LOCALAPPDATA',
        'LANG',
        'LC_ALL',
        'TZ',
    }
    inherited = {key: value for key, value in os.environ.items() if key.upper() in keep}
    os.environ.clear()
    os.environ.update(inherited)
    os.environ.update(
        FLASK_ENV='development',
        ENABLE_DEMO_MODE='false',
        SECRET_KEY=state['session_key'],
        DB_ENCRYPTION_KEY=state['encryption_key'],
        DATABASE_URL=database_url(state).render_as_string(hide_password=False),
        UPLOAD_FOLDER=str(STATE_DIR / 'uploads'),
        RATELIMIT_STORAGE_URI='memory://',
    )
    (STATE_DIR / 'uploads').mkdir(parents=True, exist_ok=True)


def verify_database(state):
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url(state))
    try:
        with engine.connect() as connection:
            marker = connection.execute(
                text("SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname=current_database()")
            ).scalar_one()
            if marker != 'Synthetic founder trial: ' + state['database']:
                raise RuntimeError('Database is not the marked synthetic trial. Refusing to run.')
    finally:
        engine.dispose()


def make_app(state):
    configure_environment(state)
    verify_database(state)
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from flask_talisman import Talisman
    from sqlalchemy import text

    from payroll_engine import create_app, db

    app = create_app()
    # Plain HTTP is intentionally restricted to loopback. Normal login, CSRF,
    # authorization and rate limiting remain enabled; no auto-login routes exist.
    app.config.update(DEBUG=False, SESSION_COOKIE_SECURE=False, WTF_CSRF_ENABLED=True)
    for hook in app.before_request_funcs.get(None, []):
        extension = getattr(hook, '__self__', None)
        if isinstance(extension, Talisman):
            extension.force_https = False
            extension.session_cookie_secure = False
            extension.strict_transport_security = False
    # Automatic draft scheduling is outside this fixed synthetic monthly exercise.
    app.before_request_funcs[None] = [
        hook for hook in app.before_request_funcs.get(None, []) if hook.__name__ != 'proactive_checks'
    ]
    config = Config(str(ROOT / 'migrations' / 'alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    expected = ScriptDirectory.from_config(config).get_heads()
    with app.app_context():
        actual = list(db.session.execute(text('SELECT version_num FROM alembic_version')).scalars())
        if len(expected) != 1 or actual != expected:
            raise RuntimeError('Trial schema does not match this source. No automatic upgrade or stamp was attempted.')
    return app


def initialize():
    if STATE_FILE.exists():
        state = read_state()
        verify_database(state)
        print('Existing trial preserved. No seed, reset or migration was performed.')
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    current = date.today().replace(day=1)
    previous = (current - timedelta(days=1)).replace(day=1)
    state = dict(
        database='payroll_founder_trial_' + uuid4().hex,
        session_key=secrets.token_urlsafe(32),
        encryption_key=secrets.token_hex(32),
        password=secrets.token_urlsafe(18) + '1!',
        current_month=current.isoformat(),
        ready=False,
    )
    # Exclusive creation prevents two initializers from claiming/resetting one trial.
    with STATE_FILE.open('x', encoding='utf-8') as stream:
        json.dump(state, stream, indent=2)
    configure_environment(state)
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    control = create_engine(CONTROL_URL, isolation_level='AUTOCOMMIT')
    try:
        with control.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{state["database"]}"'))
            connection.execute(
                text(f'COMMENT ON DATABASE "{state["database"]}" IS \'Synthetic founder trial: {state["database"]}\'')
            )
    finally:
        control.dispose()
    config = Config(str(ROOT / 'migrations' / 'alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    config.set_main_option('sqlalchemy.url', database_url(state).render_as_string(hide_password=False))
    command.upgrade(config, 'head')
    app = make_app(state)
    from payroll_engine import db
    from payroll_engine.models import Company, Employee, PayrollDraft, User, UserCompany
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.services.worksheet_review import create_review
    from payroll_engine.shared import create_audit_log

    with app.app_context():
        company = Company(name='SYNTHETIC - Monthly Payroll Trial', tin='1234567890')
        db.session.add(company)
        db.session.flush()
        users = {}
        for role in ('owner', 'accountant'):
            user = User(company_id=company.id, email=f'{role}@trial.example.invalid', role=role)
            user.set_password(state['password'])
            db.session.add(user)
            db.session.flush()
            db.session.add(UserCompany(company_id=company.id, user_id=user.id, role=role))
            users[role] = user
        employee = Employee(
            company_id=company.id,
            employee_id='TRIAL1',
            name='Synthetic Monthly Employee',
            basic_salary=Decimal('10000'),
            allowances=Decimal('2000'),
            bank_or_telebirr='cbe:1000123456789',
            tin='1234567890',
        )
        db.session.add(employee)
        db.session.flush()
        run = create_review(company.id, users['owner'].id, previous)
        if any(flag.severity == 'BLOCK' for flag in run.validation_results):
            raise RuntimeError('Synthetic prior month has blocking validation. Setup stopped without resetting data.')
        result = process_payroll(run, company.id, users['owner'].id, users['owner'].email, '127.0.0.1')
        if not result.success:
            raise RuntimeError('Synthetic prior-month service approval failed. Preserve setup for investigation.')
        prior = PayrollDraft.query.filter_by(company_id=company.id, payroll_run_id=run.id).one()
        state.update(company_id=company.id, employee_id=employee.id, previous_run_id=run.id)
        state['prior_net'] = prior.employee_data[0]['net']
        employee.basic_salary = Decimal('12000')
        create_audit_log(
            company.id,
            users['owner'].id,
            'synthetic_trial_seeded',
            {
                'synthetic_only': True,
                'previous_run_id': run.id,
                'current_month': current.isoformat(),
                'source_note': 'Synthetic salary change from 10000 to 12000; no real employee or payment.',
            },
        )
        db.session.commit()
        db.session.remove()
        db.engine.dispose()
    credentials = STATE_DIR / 'ACCOUNT_DETAILS.txt'
    credentials.write_text(
        f'SYNTHETIC ONLY. Local computer trial; never use real payroll data.\n'
        f'URL: http://127.0.0.1:{PORT}/auth/login\n'
        f'Accountant: accountant@trial.example.invalid\nOwner: owner@trial.example.invalid\n'
        f'Password for both: {state["password"]}\n'
        f'Current Gregorian month: {current:%B %Y}\nPrevious approved fixture: {previous:%B %Y}\n'
        f'Prior net: {state["prior_net"]}\n'
        'Source notes: salary 10000 -> 12000; allowances 2000 unchanged.\n'
        'Enter day overtime 4 hours; bonus 500; advance 100; additional unpaid days 0.\n'
        'Initialization uses the existing services to seed an approved historical fixture;\n'
        'it is not evidence of founder/practitioner approval or statutory acceptance.\n',
        encoding='utf-8',
    )
    state['ready'] = True
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print(f'Trial initialized. Private synthetic account details: {credentials}')
    print('No real payment or filing was submitted. State and keys remain local.')


def main():
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('init', 'serve'))
    args = parser.parse_args()
    if args.action == 'init':
        initialize()
        return
    state = read_state()
    if state['current_month'] != date.today().replace(day=1).isoformat():
        raise RuntimeError('Trial month has changed. Preserve this trial and request a new isolated exercise.')
    app = make_app(state)
    print(f'Synthetic trial: http://127.0.0.1:{PORT}/auth/login ; Ctrl+C stops it without deleting data.')
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
