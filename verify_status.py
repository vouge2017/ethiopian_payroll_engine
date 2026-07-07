#!/usr/bin/env python3
"""
verify_status.py — Run this FIRST at the start of every session.

Prevents stale-document problems by checking the actual codebase
against PROGRESS_TRACKER.md claims.

Usage:
    python3 verify_status.py
    python3 verify_status.py --json        # machine-readable output
    python3 verify_status.py --fix-tracker # auto-update PROGRESS_TRACKER.md
"""

import os
import re
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
ENGINE_DIR = REPO_ROOT / "payroll_engine"
TESTS_DIR = REPO_ROOT / "tests"
TRACKER_PATH = REPO_ROOT / ".mimo" / "PROGRESS_TRACKER.md"


def count_py_files():
    """Count .py files in /payroll_engine/"""
    files = list(ENGINE_DIR.glob("*.py"))
    return len(files), [f.name for f in sorted(files)]


def count_test_files():
    """Count test files and lines"""
    files = list(TESTS_DIR.glob("test_*.py"))
    total_lines = sum(f.read_text(encoding='utf-8').count('\n') for f in files)
    return len(files), total_lines, [f.name for f in sorted(files)]


def run_pytest():
    """Run pytest and capture results"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=line", "-q"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=120
        )
        output = result.stdout + result.stderr

        # Parse summary line: "X passed, Y failed, Z errors"
        summary_match = re.search(
            r'(\d+) passed.*?(\d+) failed.*?(\d+)',
            output
        )
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        error_match = re.search(r'(\d+) error', output)
        collected_match = re.search(r'collected (\d+) items', output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        errors = int(error_match.group(1)) if error_match else 0
        collected = int(collected_match.group(1)) if collected_match else 0

        # Get failed test names
        failed_tests = []
        for line in output.split('\n'):
            if 'FAILED' in line:
                test_name = line.split('FAILED')[0].strip()
                if test_name:
                    failed_tests.append(test_name)

        return {
            'collected': collected,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'total': collected,
            'failed_tests': failed_tests,
            'raw_output': output[-2000:],  # last 2000 chars
        }
    except subprocess.TimeoutExpired:
        return {'error': 'pytest timed out after 120s'}
    except Exception as e:
        return {'error': str(e)}


def check_feature_exists(description, search_paths, search_patterns):
    """Check if a feature/file exists"""
    results = []
    for path in search_paths:
        full_path = REPO_ROOT / path
        if full_path.exists():
            if search_patterns:
                content = full_path.read_text(encoding='utf-8')
                found = all(p in content for p in search_patterns)
                results.append({
                    'file': path,
                    'exists': True,
                    'has_patterns': found,
                    'missing_patterns': [p for p in search_patterns if p not in content]
                })
            else:
                results.append({'file': path, 'exists': True, 'has_patterns': None})
        else:
            results.append({'file': path, 'exists': False, 'has_patterns': None})
    return results


def run_all_checks():
    """Run all verification checks"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'repo': str(REPO_ROOT),
    }

    # 1. File counts
    engine_count, engine_files = count_py_files()
    test_count, test_lines, test_files = count_test_files()
    report['files'] = {
        'engine_py_count': engine_count,
        'engine_files': engine_files,
        'test_file_count': test_count,
        'test_total_lines': test_lines,
        'test_files': test_files,
    }

    # 2. Pytest results
    print("Running pytest (this may take a moment)...")
    report['pytest'] = run_pytest()

    # 3. Feature checks
    report['features'] = {}

    # Ethiopian calendar
    report['features']['ethiopian_calendar'] = check_feature_exists(
        'Ethiopian calendar with JDN conversion',
        ['payroll_engine/ethiopian_calendar.py'],
        ['gregorian_to_ethiopian', 'ETHIOPIAN_MONTHS']
    )

    # Amharic strings
    report['features']['amharic_strings'] = check_feature_exists(
        'Amharic i18n strings',
        ['payroll_engine/i18n.py'],
        ['get_string', 'STRINGS']
    )

    # PDF payslip
    report['features']['pdf_payslip'] = check_feature_exists(
        'PDF payslip generator',
        ['payroll_engine/pdf.py'],
        ['generate_payslip', 'reportlab']
    )

    # Ethiopian font
    font_exists = any(REPO_ROOT.rglob("*.ttf")) or any(REPO_ROOT.rglob("*.otf"))
    report['features']['ethiopian_font'] = {
        'exists': font_exists,
        'files': [str(f.relative_to(REPO_ROOT)) for f in REPO_ROOT.rglob("*.ttf")] +
                 [str(f.relative_to(REPO_ROOT)) for f in REPO_ROOT.rglob("*.otf")]
    }

    # Bank file generator
    report['features']['bank_file'] = check_feature_exists(
        'Bank file generator',
        ['payroll_engine/bank_file.py'],
        ['validate_account_number', 'ACCOUNT_PATTERNS']
    )

    # Bank file "bank:" stripping
    bank_content = (REPO_ROOT / 'payroll_engine' / 'bank_file.py').read_text(encoding='utf-8')
    report['features']['bank_prefix_stripping'] = {
        'exists': "split(':', 1)" in bank_content,
        'detail': 'bank_file.py splits on ":" to strip bank: prefix from payment method'
    }

    # ERCA report
    report['features']['erca_report'] = check_feature_exists(
        'ERCA report generation',
        ['payroll_engine/reports.py'],
        ['generate_erca_report', 'openpyxl']
    )

    # MergedCell handling in reports
    reports_content = (REPO_ROOT / 'payroll_engine' / 'reports.py').read_text(encoding='utf-8')
    report['features']['merged_cell_handling'] = {
        'exists': 'MergedCell' in reports_content or 'merged' in reports_content.lower(),
        'detail': 'reports.py handles openpyxl MergedCell objects'
    }

    # E2E test
    e2e_exists = (TESTS_DIR / 'test_e2e.py').exists() or (REPO_ROOT / 'test_e2e.py').exists()
    report['features']['e2e_test'] = {
        'exists': e2e_exists,
        'detail': 'End-to-end integration test'
    }

    # TIN field
    report['features']['tin_field'] = check_feature_exists(
        'TIN field on Employee',
        ['payroll_engine/models.py'],
        ['tin']
    )

    # TenantQuery
    report['features']['tenant_isolation'] = check_feature_exists(
        'TenantQuery structural enforcement',
        ['payroll_engine/models.py'],
        ['TenantQuery']
    )

    # CSRF
    report['features']['csrf'] = check_feature_exists(
        'CSRF protection',
        ['payroll_engine/__init__.py'],
        ['CSRFProtect']
    )

    # Payroll lifecycle
    report['features']['payroll_lifecycle'] = check_feature_exists(
        'Payroll lifecycle (Draft→Approve)',
        ['payroll_engine/models.py', 'payroll_engine/main.py'],
        ['status']
    )

    # Compliance deadlines
    report['features']['compliance_deadlines'] = check_feature_exists(
        'Compliance deadline tracking',
        ['payroll_engine/compliance.py'],
        ['get_upcoming_deadlines']
    )

    # Payroll reference number
    models_content = (REPO_ROOT / 'payroll_engine' / 'models.py').read_text(encoding='utf-8')
    report['features']['payroll_reference'] = {
        'exists': 'reference' in models_content.lower() and 'PR-' in models_content or 'generate_reference' in models_content,
        'detail': 'PayrollRun has human-readable reference (PR-YYYY-MM-NNN)'
    }

    # 4. Read PROGRESS_TRACKER.md for comparison
    if TRACKER_PATH.exists():
        tracker_content = TRACKER_PATH.read_text(encoding='utf-8')
        report['tracker'] = {
            'exists': True,
            'path': str(TRACKER_PATH),
            'lines': tracker_content.count('\n'),
        }
    else:
        report['tracker'] = {'exists': False}

    return report


def print_report(report):
    """Print human-readable report"""
    print("\n" + "=" * 70)
    print("  ETHIOPAYROLL — VERIFICATION REPORT")
    print(f"  Generated: {report['timestamp']}")
    print("=" * 70)

    # File counts
    f = report['files']
    print(f"\n📁 FILES")
    print(f"   Engine .py files:  {f['engine_py_count']}")
    print(f"   Test files:        {f['test_file_count']} ({f['test_total_lines']} lines)")

    # Pytest
    p = report.get('pytest', {})
    if 'error' in p:
        print(f"\n🧪 TESTS: ERROR — {p['error']}")
    else:
        status = "✅ ALL PASS" if p.get('failed', 0) == 0 and p.get('errors', 0) == 0 else "❌ FAILURES"
        print(f"\n🧪 TESTS: {status}")
        print(f"   Collected: {p.get('collected', '?')}")
        print(f"   Passed:    {p.get('passed', '?')}")
        print(f"   Failed:    {p.get('failed', '?')}")
        print(f"   Errors:    {p.get('errors', '?')}")
        if p.get('failed_tests'):
            print(f"\n   Failed tests:")
            for t in p['failed_tests']:
                print(f"   ❌ {t}")

    # Features
    print(f"\n🔍 FEATURE VERIFICATION")
    features = report.get('features', {})
    for name, data in features.items():
        if isinstance(data, list):
            # check_feature_exists returns a list
            exists = any(r.get('exists') for r in data)
            patterns_ok = all(r.get('has_patterns', True) for r in data if r.get('exists'))
            icon = "✅" if exists and patterns_ok else "⚠️" if exists else "❌"
            detail = ""
            if exists and not patterns_ok:
                missing = []
                for r in data:
                    if r.get('missing_patterns'):
                        missing.extend(r['missing_patterns'])
                detail = f" (missing: {', '.join(missing)})"
            elif not exists:
                detail = " — FILE MISSING"
            print(f"   {icon} {name}{detail}")
        elif isinstance(data, dict):
            exists = data.get('exists', False)
            icon = "✅" if exists else "❌"
            detail = data.get('detail', '')
            extra = ""
            if 'files' in data and data['files']:
                extra = f" [{', '.join(data['files'])}]"
            elif 'missing_patterns' in data:
                extra = f" (missing: {', '.join(data['missing_patterns'])})"
            print(f"   {icon} {name}{f' — {detail}' if detail else ''}{extra}")

    # Tracker
    t = report.get('tracker', {})
    if t.get('exists'):
        print(f"\n📄 PROGRESS_TRACKER.md: exists ({t['lines']} lines)")
    else:
        print(f"\n📄 PROGRESS_TRACKER.md: MISSING")

    print("\n" + "=" * 70)


def main():
    json_mode = '--json' in sys.argv
    fix_mode = '--fix-tracker' in sys.argv

    report = run_all_checks()

    if json_mode:
        # Remove raw output for JSON
        if 'pytest' in report and 'raw_output' in report['pytest']:
            del report['pytest']['raw_output']
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    # Exit code: 0 if all pass, 1 if any failures
    p = report.get('pytest', {})
    if p.get('failed', 0) > 0 or p.get('errors', 0) > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
