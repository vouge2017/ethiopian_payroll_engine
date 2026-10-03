"""Before/after cases for the repository's actual test runner."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'payroll_test_runner', Path(__file__).resolve().parents[1] / 'run_tests.py'
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.parametrize(
    'output, returncode, expected',
    [
        ('3 failed in 0.10s\n', 1, (0, 3, 0, 0)),
        ('1 error in 0.10s\n', 2, (0, 0, 1, 0)),
        ('3 warnings, 1 error in 0.10s\n', 2, (0, 0, 1, 0)),
        ('4 skipped in 0.10s\n', 0, (0, 0, 0, 4)),
        ('2 passed, 1 failed, 1 error, 3 skipped in 0.10s\n', 1, (2, 1, 1, 3)),
        (
            'FAILED tests/test_x.py::test_message - 99 passed is just an error message\n1 failed in 0.10s\n',
            1,
            (0, 1, 0, 0),
        ),
    ],
)
def test_counts_do_not_require_a_passing_test(monkeypatch, output, returncode, expected):
    monkeypatch.setattr(
        runner.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a, returncode, output, '')
    )
    result = runner.run_test_file('tests/test_x.py')
    assert result[:4] == expected
    assert result[4] == output
    assert result[5] == returncode


@pytest.mark.parametrize('continue_run', [False, True])
@pytest.mark.parametrize('returncode', [1, 2, 3, 4, 5])
def test_any_failed_child_makes_the_runner_fail(monkeypatch, continue_run, returncode):
    monkeypatch.setattr(runner, 'get_test_files', lambda: ['tests/test_x.py', 'tests/test_y.py'])
    calls = []

    def child(path, verbose=False):
        calls.append(path)
        return (0, 0, 0, 0, 'unparseable subprocess error', returncode)

    monkeypatch.setattr(runner, 'run_test_file', child)
    monkeypatch.setattr(runner.sys, 'argv', ['run_tests.py'] + (['--continue'] if continue_run else []))
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code != 0
    assert len(calls) == (2 if continue_run else 1)


def test_no_selected_files_is_not_a_green_suite(monkeypatch):
    monkeypatch.setattr(runner, 'get_test_files', lambda: [])
    monkeypatch.setattr(runner.sys, 'argv', ['run_tests.py'])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code != 0


def test_timeout_retains_the_diagnostic_output(monkeypatch):
    def child(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 120, output=b'last test before hang\n', stderr=b'diagnostic\n')

    monkeypatch.setattr(runner.subprocess, 'run', child)
    result = runner.run_test_file('tests/test_x.py')
    assert result[2] > 0 and result[5] != 0
    assert 'TIMEOUT' in result[4]
    assert 'last test before hang' in result[4]
    assert 'diagnostic' in result[4]


def test_successful_children_make_the_runner_succeed(monkeypatch):
    monkeypatch.setattr(runner, 'get_test_files', lambda: ['tests/test_x.py'])
    monkeypatch.setattr(runner, 'run_test_file', lambda *args: (2, 0, 0, 0, '2 passed', 0))
    monkeypatch.setattr(runner.sys, 'argv', ['run_tests.py'])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 0


def test_failed_child_reason_is_visible_without_verbose(monkeypatch, capsys):
    diagnostic = "ModuleNotFoundError: No module named 'pypdf'"
    monkeypatch.setattr(runner, 'get_test_files', lambda: ['tests/test_pdf.py'])
    monkeypatch.setattr(runner, 'run_test_file', lambda *args: (0, 1, 0, 0, diagnostic, 1))
    monkeypatch.setattr(runner.sys, 'argv', ['run_tests.py', '--continue'])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 1
    assert diagnostic in capsys.readouterr().out
