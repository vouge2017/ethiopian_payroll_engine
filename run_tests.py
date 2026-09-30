#!/usr/bin/env python3
"""Run test files in separate processes to isolate module-level test state.

Child process exit codes determine success. Parsed pytest counts are only
reporting information; collection errors and unparseable failures must fail.

Usage:
    python3 run_tests.py              # run all, stop on first failure
    python3 run_tests.py --continue   # run all, report all failures
    python3 run_tests.py --verbose    # show each test name
"""

import glob
import os
import re
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(REPO_ROOT, 'tests')


def get_test_files():
    """Get all test_*.py files, sorted."""
    files = glob.glob(os.path.join(TEST_DIR, 'test_*.py'))
    return sorted(files)


def run_test_file(filepath, verbose=False):
    """Return (passed, failed, errors, skipped, output, child_exit_code)."""
    cmd = [sys.executable, '-m', 'pytest', filepath, '--tb=line', '-q']
    if verbose:
        cmd.append('-v')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
        output = result.stdout + result.stderr

        # Read summary lines only, including summaries with no passing tests.
        counts = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
        for line in output.splitlines():
            if not re.match(
                r'^\s*(?:=+\s*)?\d+ (?:passed|failed|errors?|skipped|warnings?|deselected|xfailed|xpassed)\b',
                line,
            ):
                continue
            for number, status in re.findall(r'(\d+) (passed|failed|errors?|skipped)\b', line):
                counts['errors' if status == 'error' else status] = int(number)
        passed, failed, errors, skipped = (counts[key] for key in ('passed', 'failed', 'errors', 'skipped'))

        return passed, failed, errors, skipped, output, result.returncode

    except subprocess.TimeoutExpired as exc:

        def diagnostic(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')

        output = diagnostic(exc.stdout) + diagnostic(exc.stderr)
        return 0, 0, 1, 0, output + '\nTIMEOUT after 120s', 2


def main():
    continue_on_failure = '--continue' in sys.argv
    verbose = '--verbose' in sys.argv

    test_files = get_test_files()
    if not test_files:
        print('ERROR: no test files selected', file=sys.stderr)
        sys.exit(5)
    print(f'Running {len(test_files)} test files in separate processes...\n')

    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    failed_files = []
    start_time = time.time()

    for i, filepath in enumerate(test_files):
        filename = os.path.basename(filepath)
        sys.stdout.write(f'[{i + 1}/{len(test_files)}] {filename:45s} ')
        sys.stdout.flush()

        passed, failed, errors, skipped, output, returncode = run_test_file(filepath, verbose)

        total_passed += passed
        total_failed += failed
        total_errors += errors
        total_skipped += skipped

        if returncode == 0:
            print(f'✅ {passed} passed' + (f', {skipped} skipped' if skipped else ''))
        else:
            failed_files.append(filename)
            print(f'❌ {passed} passed, {failed} failed, {errors} errors')
            # Ordinary CI runs need the failed child's reason, not only counts.
            print(output.rstrip() or f'Child exited with code {returncode} without output.')
            if not continue_on_failure:
                print('\nStopping on first failure. Use --continue to run all.')
                break

    elapsed = time.time() - start_time
    print(f'\n{"=" * 60}')
    print(f'TOTAL: {total_passed} passed, {total_failed} failed, {total_errors} errors, {total_skipped} skipped')
    print(f'TIME: {elapsed:.1f}s')
    if failed_files:
        print(f'FAILED FILES: {", ".join(failed_files)}')
    print(f'{"=" * 60}')

    sys.exit(1 if failed_files else 0)


if __name__ == '__main__':
    main()
