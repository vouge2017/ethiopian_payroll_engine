"""Exercise the actual Docker shell command without starting a web server."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('migration_exit', [0, 7])
def test_web_start_requires_successful_upgrade(tmp_path, migration_exit):
    shell = shutil.which('sh')
    if not shell:
        candidate = Path('C:/Program Files/Git/bin/sh.exe')
        shell = str(candidate) if candidate.exists() else None
    if not shell:
        pytest.skip('POSIX shell required to execute the Docker startup command')

    command_line = next(line for line in (REPO / 'Dockerfile').read_text().splitlines() if line.startswith('CMD '))
    command = json.loads(command_line.removeprefix('CMD '))
    assert command[:2] == ['sh', '-c']
    binary_dir = tmp_path / 'bin'
    binary_dir.mkdir()
    scripts = {
        'flask': """#!/bin/sh
printf 'flask %s\n' "$*" >> "$CALLS_FILE"
if test "$1 $2" = 'db upgrade'; then
    if test "$MIGRATION_EXIT" != 0; then printf 'migration-failed-visible\n' >&2; fi
    exit "$MIGRATION_EXIT"
fi
exit 0
""",
        'gunicorn': """#!/bin/sh
printf 'gunicorn %s\n' "$*" >> "$CALLS_FILE"
exit 0
""",
    }
    for name, source in scripts.items():
        script = binary_dir / name
        script.write_bytes(source.encode())
        script.chmod(0o755)
    calls_file = tmp_path / 'calls.txt'
    env = dict(os.environ, CALLS_FILE=calls_file.as_posix(), MIGRATION_EXIT=str(migration_exit), PORT='10000')
    # Git's POSIX shell understands drive-letter paths; use a POSIX PATH separator.
    env['PATH'] = binary_dir.as_posix() + ':' + '/usr/bin:/bin'
    result = subprocess.run([shell, '-c', command[2]], env=env, capture_output=True, text=True, timeout=10)
    calls = calls_file.read_text().splitlines()
    assert calls[0] == 'flask db upgrade'
    assert all('stamp' not in call for call in calls)
    if migration_exit:
        assert result.returncode == migration_exit
        assert calls == ['flask db upgrade']
        assert 'migration-failed-visible' in result.stderr
    else:
        assert result.returncode == 0
        assert len(calls) == 2
        assert calls[1] == 'gunicorn --bind 0.0.0.0:10000 --workers 4 --timeout 120 wsgi:app'
