"""Pytest collection defaults must not embed or replace encryption keys."""

import os
import runpy
import secrets
from pathlib import Path

import pytest

CONFTEST = Path(__file__).with_name('conftest.py')


def test_missing_test_key_is_fresh_for_each_collection(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'testing')
    keys = []
    for _ in range(2):
        monkeypatch.delenv('DB_ENCRYPTION_KEY', raising=False)
        runpy.run_path(str(CONFTEST))
        keys.append(os.environ['DB_ENCRYPTION_KEY'])

    assert all(len(bytes.fromhex(key)) == 32 for key in keys)
    assert keys[0] != keys[1]


@pytest.mark.parametrize('environment', ['testing', 'production'])
def test_configured_key_is_preserved(monkeypatch, environment):
    configured_key = secrets.token_hex(32)
    monkeypatch.setenv('FLASK_ENV', environment)
    monkeypatch.setenv('DB_ENCRYPTION_KEY', configured_key)
    runpy.run_path(str(CONFTEST))
    assert os.environ['DB_ENCRYPTION_KEY'] == configured_key


def test_missing_production_key_is_not_generated(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('DB_ENCRYPTION_KEY', raising=False)
    runpy.run_path(str(CONFTEST))
    assert 'DB_ENCRYPTION_KEY' not in os.environ
