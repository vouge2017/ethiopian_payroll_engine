"""Run the actual Docker probe against a loopback HTTP server with Talisman."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from threading import Thread

import pytest
from flask import Flask, redirect
from flask_talisman import Talisman
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('mode,expected', [('ready', 0), ('not_ready', 1), ('unknown', 1), ('redirect', 1)])
def test_actual_container_probe_requires_ready_json_without_redirect(mode, expected):
    app = Flask(__name__)
    Talisman(app, force_https=True)
    seen = []

    @app.route('/readyz')
    def ready():
        from flask import request

        seen.append(request.headers.get('X-Forwarded-Proto'))
        if mode == 'redirect':
            return redirect('/login')
        return {
            'status': 'ready' if mode != 'not_ready' else 'not_ready',
            'checks': {
                'database': 'up',
                'migrations': 'unknown' if mode == 'unknown' else 'current',
                'schema': 'current',
            },
        }, 503 if mode == 'not_ready' else 200

    @app.route('/login')
    def login():
        seen.append('redirect-followed')
        return 'login', 200

    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        shell = shutil.which('sh') or (
            'C:/Program Files/Git/bin/sh.exe' if Path('C:/Program Files/Git/bin/sh.exe').exists() else None
        )
        if not shell:
            pytest.skip('POSIX shell required for Docker HEALTHCHECK command')
        command = next(
            line.strip().removeprefix('CMD ')
            for line in (ROOT / 'Dockerfile').read_text().splitlines()
            if line.strip().startswith('CMD python ')
        )
        command = command.replace('python ', shlex.quote(Path(sys.executable).as_posix()) + ' ', 1)
        result = subprocess.run(
            [shell, '-c', command],
            cwd=ROOT,
            env=dict(os.environ, PORT=str(server.server_port)),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        assert seen == ['https']
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
