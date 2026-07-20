"""
EthioPayroll — Performance Benchmarks

Tests payroll calculation, PDF generation, and report generation
at different scales.

Usage:
    python benchmark.py
    python benchmark.py --employees 100 500 1000
"""
import argparse
import gc
import json
import os
import sys
import time
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

D = Decimal


def generate_employees(count):
    """Generate fake employee data for benchmarking."""
    employees = []
    for i in range(count):
        employees.append({
            'employee_id': f'EMP{i+1:05d}',
            'name': f'Employee {i+1}',
            'basic_salary': D(str(5000 + (i % 50) * 200)),
            'allowances': D(str(1000 + (i % 10) * 100)),
        })
    return employees


def benchmark_payroll(employees):
    """Benchmark core payroll calculation."""
    from payroll_engine.payroll import calculate_payroll

    gc.collect()
    start = time.perf_counter()
    results = []
    for emp in employees:
        results.append(calculate_payroll(
            basic_salary=emp['basic_salary'],
            allowances=emp['allowances'],
        ))
    elapsed = time.perf_counter() - start

    first = results[0]
    assert first['gross'] > 0
    assert first['pension_employee'] > 0
    assert first['net'] > 0

    return {
        'operation': 'Payroll Calculation',
        'employees': len(employees),
        'total_seconds': round(elapsed, 4),
        'per_employee_ms': round(elapsed / len(employees) * 1000, 4),
        'per_second': round(len(employees) / elapsed, 0),
    }


def benchmark_pension(employees):
    """Benchmark pension calculation."""
    from payroll_engine.pension import employee_pension, employer_pension

    gc.collect()
    start = time.perf_counter()
    for emp in employees:
        employee_pension(emp['basic_salary'])
        employer_pension(emp['basic_salary'])
    elapsed = time.perf_counter() - start

    return {
        'operation': 'Pension Calculation',
        'employees': len(employees),
        'total_seconds': round(elapsed, 4),
        'per_employee_ms': round(elapsed / len(employees) * 1000, 4),
        'per_second': round(len(employees) / elapsed, 0),
    }


def benchmark_tax(employees):
    """Benchmark tax calculation."""
    from payroll_engine.tax import calculate_tax

    gc.collect()
    start = time.perf_counter()
    for emp in employees:
        taxable = emp['basic_salary'] + emp['allowances'] - emp['basic_salary'] * D('0.07')
        calculate_tax(taxable)
    elapsed = time.perf_counter() - start

    return {
        'operation': 'Tax Calculation',
        'employees': len(employees),
        'total_seconds': round(elapsed, 4),
        'per_employee_ms': round(elapsed / len(employees) * 1000, 4),
        'per_second': round(len(employees) / elapsed, 0),
    }


def benchmark_pdf(employees):
    """Benchmark PDF generation."""
    from payroll_engine.pdf import generate_payslip
    from payroll_engine.payroll import calculate_payroll

    count = min(len(employees), 200)  # Cap at 200 for PDF
    payslips = []
    for i, emp_data in enumerate(employees[:count]):
        result = calculate_payroll(
            basic_salary=emp_data['basic_salary'],
            allowances=emp_data['allowances'],
        )
        payslips.append({
            'id': i,
            'employee_id': emp_data['employee_id'],
            'name': emp_data['name'],
            'basic_salary': emp_data['basic_salary'],
            'allowances': emp_data['allowances'],
            'basic': emp_data['basic_salary'],
            'gross': result['gross'],
            'pension': result['pension_employee'],
            'pension_employee': result['pension_employee'],
            'pension_employer': result.get('pension_employer', D('0')),
            'tax': result['tax'],
            'net': result['net'],
            'taxable': result['taxable'],
            'tax_explanation': '',
            'bank': '',
            'department': '',
            'position': '',
            'period': 'July 2026',
        })

    gc.collect()
    start = time.perf_counter()
    for p in payslips:
        generate_payslip(p)
    elapsed = time.perf_counter() - start

    return {
        'operation': f'PDF Generation (cap {count})',
        'employees': count,
        'total_seconds': round(elapsed, 4),
        'per_employee_ms': round(elapsed / count * 1000, 4),
        'per_second': round(count / elapsed, 0),
    }


def benchmark_erca_report(employees):
    """Benchmark ERCA Excel report generation."""
    from payroll_engine import create_app, db
    from payroll_engine.models import Employee, Payslip, PayrollRun, Company
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.reports import generate_erca_report

    app = create_app()
    with app.app_context():
        db.create_all()
        company = Company(name='Benchmark Co', tin='1234567890')
        db.session.add(company)
        db.session.flush()

        run = PayrollRun(company_id=company.id, period='July 2026', status='completed')
        db.session.add(run)
        db.session.flush()

        payslips = []
        for emp_data in employees:
            emp = Employee(
                employee_id=emp_data['employee_id'],
                name=emp_data['name'],
                basic_salary=emp_data['basic_salary'],
                allowances=emp_data['allowances'],
                company_id=company.id,
            )
            db.session.add(emp)
            db.session.flush()

            result = calculate_payroll(
                basic_salary=emp_data['basic_salary'],
                allowances=emp_data['allowances'],
            )

            payslip = Payslip(
                employee_id=emp.id,
                payroll_run_id=run.id,
                gross_salary=result['gross'],
                employee_pension=result['pension_employee'],
                employer_pension=result.get('pension_employer', D('0')),
                tax=result['tax'],
                net_pay=result['net'],
            )
            db.session.add(payslip)
            payslips.append(payslip)

        db.session.commit()

        gc.collect()
        start = time.perf_counter()
        report_bytes = generate_erca_report(payslips, 'Benchmark Co', 'July 2026', company=company)
        elapsed = time.perf_counter() - start

        return {
            'operation': 'ERCA Report (Excel)',
            'employees': len(payslips),
            'total_seconds': round(elapsed, 4),
            'per_employee_ms': round(elapsed / len(payslips) * 1000, 4),
            'per_second': round(len(payslips) / elapsed, 0),
            'file_size_kb': round(len(report_bytes) / 1024, 1),
        }


def run_benchmarks(scales):
    """Run all benchmarks at specified scales."""
    results = []

    for scale in scales:
        print(f"\n{'=' * 60}")
        print(f"  BENCHMARK: {scale:,} employees")
        print(f"{'=' * 60}")

        employees = generate_employees(scale)

        # Core calculations
        for bench_fn in [benchmark_payroll, benchmark_pension, benchmark_tax]:
            r = bench_fn(employees)
            results.append(r)
            print(f"  {r['operation']:35} {r['total_seconds']:8.3f}s  "
                  f"({r['per_employee_ms']:.3f} ms/emp, {r['per_second']:,.0f}/s)")

        # ERCA Report
        r = benchmark_erca_report(employees)
        results.append(r)
        print(f"  {r['operation']:35} {r['total_seconds']:8.3f}s  "
              f"({r.get('file_size_kb', 0):.1f} KB)")

        # PDF (capped)
        if scale <= 200:
            r = benchmark_pdf(employees)
            results.append(r)
            print(f"  {r['operation']:35} {r['total_seconds']:8.3f}s  "
                  f"({r['per_employee_ms']:.3f} ms/emp)")
        else:
            print(f"  PDF Generation                     SKIPPED (>{scale} too slow)")

    return results


def print_summary(results):
    """Print summary table."""
    print(f"\n{'=' * 85}")
    print("  SUMMARY")
    print(f"{'=' * 85}")
    print(f"  {'Operation':35} {'Employees':>10} {'Time':>10} {'Per Emp':>10} {'Rate':>12}")
    print(f"  {'-' * 35} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 12}")

    for r in results:
        emp_s = f"{r['employees']:>10,}"
        time_s = f"{r['total_seconds']:>8.3f}s"
        per_s = f"{r['per_employee_ms']:>8.3f}ms"
        rate_s = f"{r.get('per_second', 0):>10,.0f}/s"
        print(f"  {r['operation']:35} {emp_s} {time_s} {per_s} {rate_s}")


def main():
    parser = argparse.ArgumentParser(description='EthioPayroll Performance Benchmarks')
    parser.add_argument('--employees', type=int, nargs='+', default=[100, 500, 1000],
                        help='Employee counts (default: 100 500 1000)')
    args = parser.parse_args()

    print("EthioPayroll — Performance Benchmarks")
    print(f"Python {sys.version.split()[0]}")
    print(f"Scales: {', '.join(f'{n:,}' for n in args.employees)}")

    results = run_benchmarks(args.employees)
    print_summary(results)

    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to benchmark_results.json")


if __name__ == '__main__':
    main()
