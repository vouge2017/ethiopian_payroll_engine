#!/usr/bin/env python3
"""
Run each test_*.py file in its own process to avoid SQLite/in-memory lock contention.

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
TEST_DIR = os.path.join(REPO_ROOT, "tests")
PYTEST_TIMEOUT = 120


def get_test_files():
    """Return all test_*.py files (sorted)."""
    files = glob.glob(os.path.join(TEST_DIR, "test_*.py"))
    return sorted(files)


def _parse_pytest_counts(output):
    """
    Parse pytest summary numbers from output.
    Returns dict with keys: passed, failed, errors, skipped (ints).
    """
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for number, status in re.findall(r"(\d+)\s+(passed|failed|errors?|skipped)\b", output):
        n = int(number)
        key = "errors" if status.startswith("error") else status
        counts[key] = n
    return counts


def run_test_file(filepath, verbose=False):
    """Run a single test file in a subprocess."""
    cmd = [sys.executable, "-m", "pytest", filepath, "--tb=line", "-q"]
    if verbose:
        cmd.append("-v")

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PYTEST_TIMEOUT,
            cwd=REPO_ROOT,
            env=env,
            encoding="utf-8",
            errors="replace",
        )
        output = (result.stdout or "") + (result.stderr or "")
        counts = _parse_pytest_counts(output)
        return (
            counts["passed"],
            counts["failed"],
            counts["errors"],
            counts["skipped"],
            output,
            result.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        def diagnostic(value):
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        output = diagnostic(getattr(exc, "stdout", None)) + diagnostic(getattr(exc, "stderr", None))
        return 0, 0, 1, 0, output + f"\nTIMEOUT after {PYTEST_TIMEOUT}s", 2
    except Exception as exc:
        return 0, 0, 1, 0, f"UNEXPECTED ERROR: {exc}\n", 2


def main():
    continue_on_failure = "--continue" in sys.argv
    verbose = "--verbose" in sys.argv

    test_files = get_test_files()
    if not test_files:
        print("ERROR: no test files selected", file=sys.stderr)
        sys.exit(5)

    print(f"Running {len(test_files)} test files in separate processes...\n")

    total_passed = total_failed = total_errors = total_skipped = 0
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
                for line in output.splitlines():
                    if "FAILED" in line or "ERROR" in line:
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


if __name__ == "__main__":
    main()
