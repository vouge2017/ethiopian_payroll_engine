#!/usr/bin/env python3
"""Run all test files in separate processes to avoid SQLite lock contention.

This is the fix for the full-suite hang: in-memory SQLite doesn't support
multiple concurrent connections well. Running each file in its own process
avoids the issue entirely.

Usage:
    python3 run_tests.py              # run all, stop on first failure
    python3 run_tests.py --continue   # run all, report all failures
    python3 run_tests.py --verbose    # show each test name
"""
import glob
import os
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
    """Run a single test file in a subprocess. Returns (passed, failed, errors, output)."""
    cmd = [sys.executable, '-m', 'pytest', filepath, '--tb=line', '-q']
    if verbose:
        cmd.append('-v')

    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
            env=env,
            encoding='utf-8',
            errors='replace',
        )
        output = (result.stdout or '') + (result.stderr or '')

        # Parse summary
        passed = failed = errors = skipped = 0
        for line in output.split('\n'):
            if 'passed' in line:
                import re
                m = re.search(r'(\d+) passed', line)
                if m:
                    passed = int(m.group(1))
                m = re.search(r'(\d+) failed', line)
                if m:
                    failed = int(m.group(1))
                m = re.search(r'(\d+) error', line)
                if m:
                    errors = int(m.group(1))
                m = re.search(r'(\d+) skipped', line)
                if m:
                    skipped = int(m.group(1))

        return passed, failed, errors, skipped, output, result.returncode

    except subprocess.TimeoutExpired:
        return 0, 0, 1, 0, 'TIMEOUT after 120s', 2


def main():
    continue_on_failure = '--continue' in sys.argv
    verbose = '--verbose' in sys.argv

    test_files = get_test_files()
    print(f"Running {len(test_files)} test files in separate processes...\n")

    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    failed_files = []
    start_time = time.time()

    for i, filepath in enumerate(test_files):
        filename = os.path.basename(filepath)
        sys.stdout.write(f"[{i+1}/{len(test_files)}] {filename:45s} ")
        sys.stdout.flush()

        passed, failed, errors, skipped, output, returncode = run_test_file(filepath, verbose)

        total_passed += passed
        total_failed += failed
        total_errors += errors
        total_skipped += skipped

        if returncode == 0:
            print(f"✅ {passed} passed" + (f", {skipped} skipped" if skipped else ""))
        else:
            failed_files.append(filename)
            print(f"❌ {passed} passed, {failed} failed, {errors} errors")
            if verbose:
                for line in output.split('\n'):
                    if 'FAILED' in line or 'ERROR' in line:
                        print(f"   {line.strip()}")
            if not continue_on_failure:
                print("\nStopping on first failure. Use --continue to run all.")
                break

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_passed} passed, {total_failed} failed, {total_errors} errors, {total_skipped} skipped")
    print(f"TIME: {elapsed:.1f}s")
    if failed_files:
        print(f"FAILED FILES: {', '.join(failed_files)}")
    print(f"{'='*60}")

    sys.exit(1 if (total_failed > 0 or total_errors > 0) else 0)


if __name__ == '__main__':
    main()
