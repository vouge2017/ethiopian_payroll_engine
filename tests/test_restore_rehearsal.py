"""Run the genuine local PostgreSQL drill only when explicitly requested."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get('RUN_LOCAL_RESTORE_REHEARSAL') != '1', reason='Explicit local cluster drill opt-in')
def test_fresh_local_postgres_restore_rehearsal():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / 'restore_rehearsal_local.py')],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"verdict": "PASS"' in result.stdout
