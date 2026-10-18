"""Production durability warning for /tmp-based UPLOAD_FOLDER (2026-10-18)."""

import logging

from flask import Flask

from payroll_engine import warn_ephemeral_upload_folder


def _capture_records(caplog, app):
    caplog.set_level(logging.WARNING)
    app.logger.propagate = True
    return caplog


def test_production_tmp_upload_folder_warns(caplog):
    app = Flask('payroll_engine')
    app.config['ENV'] = 'production'
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    _capture_records(caplog, app)

    warn_ephemeral_upload_folder(app)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any('UPLOAD_FOLDER is under /tmp' in r.getMessage() for r in warnings)
    assert any('/tmp/uploads' in r.getMessage() for r in warnings)


def test_persistent_upload_folder_is_silent(caplog):
    app = Flask('payroll_engine')
    app.config['ENV'] = 'production'
    app.config['UPLOAD_FOLDER'] = '/var/data/ethiopian_payroll/uploads'
    _capture_records(caplog, app)

    warn_ephemeral_upload_folder(app)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == []


def test_tmp_folder_outside_production_is_silent(caplog):
    app = Flask('payroll_engine')
    app.config['ENV'] = 'testing'
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    _capture_records(caplog, app)

    warn_ephemeral_upload_folder(app)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == []
