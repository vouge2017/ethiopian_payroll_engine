# Synthetic ordinary month acceptance

Prepared before executing the application or reading its calculated results.
All companies, people, salaries, identifiers and credentials are invented.
Base: `1dac3c3ed9dc4c2f87f8a03fb4ffac4241cf86d6`.

## Independent oracle

This is a test of the owner-specified 2025 schedule, not a legal opinion.
Monthly taxable bands: first 2,000 at 0%; next 2,000 at 15%; next
3,000 at 20%; next 3,000 at 25%; next 4,000 at 30%; excess at 35%.
Tax is on gross taxable earnings before pension. All allowances here are
fully taxable. Pension is 7% employee and 11% employer on basic only.
Use Decimal throughout and round each completed money step to 0.01 HALF_UP.

The company is **Imaginary Lantern QA PLC**. The month is November 2026
(Gregorian), using the requested 2025 schedule as explicit synthetic rule data.

| Employee code | Basic | Allowance | OT | Gross/taxable | Tax | Employee pension | Employer pension | Absence reduction | Net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SYN01 | 1800.00 | 100.00 | 0 | 1900.00 | 0.00 | 126.00 | 198.00 | 0 | 1774.00 |
| SYN02 | 3000.00 | 200.00 | 0 | 3200.00 | 180.00 | 210.00 | 330.00 | 0 | 2810.00 |
| SYN03 | 5000.00 | 500.00 | 0 | 5500.00 | 600.00 | 350.00 | 550.00 | 0 | 4550.00 |
| SYN04 | 8000.00 | 1000.00 | 0 | 9000.00 | 1400.00 | 560.00 | 880.00 | 0 | 7040.00 |
| SYN05 | 10000.00 | 2000.00 | 0 | 12000.00 | 2250.00 | 700.00 | 1100.00 | 0 | 9050.00 |
| SYN06 | 12000.00 | 1000.00 | 0 | 13000.00 | 2550.00 | 840.00 | 1320.00 | 866.67 | 8743.33 |
| SYN07 | 14000.00 | 0.00 | 0 | 14000.00 | 2850.00 | 980.00 | 1540.00 | 0 | 10170.00 |
| SYN08 | 16000.00 | 2000.00 | 0 | 18000.00 | 4250.00 | 1120.00 | 1760.00 | 0 | 12630.00 |
| SYN09 | 20800.00 | 1000.00 | 600.00 | 22400.00 | 5790.00 | 1456.00 | 2288.00 | 0 | 15154.00 |
| SYN10 | 25000.50 | 1500.25 | 0 | 26500.75 | 7225.26 | 1750.04 | 2750.06 | 0 | 17525.45 |

Full arithmetic, independent of application functions:

- SYN02: gross = 3000 + 200 = 3200; tax = 2000*0 + 1200*.15 = 180;
  employee pension = 3000*.07 = 210; employer pension = 3000*.11 = 330;
  net = 3200 - 180 - 210 = 2810.
- SYN05: gross = 10000 + 2000 = 12000; tax = 2000*0 + 2000*.15 +
  3000*.20 + 3000*.25 + 2000*.30 = 0+300+600+750+600 = 2250;
  employee pension = 10000*.07 = 700; employer = 10000*.11 = 1100;
  net = 12000 - 2250 - 700 = 9050.
- SYN06: gross = 12000+1000 = 13000; tax = 300+600+750+3000*.30 = 2550;
  pensions = 12000*.07 = 840 and 12000*.11 = 1320;
  absence = (12000+1000)/30*2 = 866.666... -> 866.67;
  net = 13000-2550-840-866.67 = 8743.33. This explicitly tests the existing
  worksheet policy of a post-tax absence reduction; it does not endorse that
  policy as a legal conclusion.
- SYN09: hourly = 20800/208 = 100; four daytime overtime hours at 1.5
  give 100*4*1.5 = 600; gross = 20800+1000+600 = 22400;
  tax = 300+600+750+1200+(22400-14000)*.35 = 5790;
  pensions = 20800*.07 = 1456 and 20800*.11 = 2288;
  net = 22400-5790-1456 = 15154.
- SYN10: gross = 25000.50+1500.25 = 26500.75;
  tax = 300+600+750+1200+12500.75*.35 = 7225.2625 -> 7225.26;
  employee pension = 25000.50*.07 = 1750.035 -> 1750.04;
  employer pension = 25000.50*.11 = 2750.055 -> 2750.06;
  net = 26500.75-7225.26-1750.04 = 17525.45.

The test uses literal expected amounts, checks every employee and sums those
independent literals for run totals. No expected payroll amount comes from an
application calculator. Execution results and limitations are recorded below.

## Results

All ten employees matched on SQLite and migrated PostgreSQL 16.15. No case was
dropped and no amount mismatch occurred. Totals (ETB): gross 125500.75;
tax 27095.26; employee pension 8092.04; employer pension 12716.06;
absence 866.67; net 89446.78. Reconciliation:
125500.75 - 27095.26 - 8092.04 - 866.67 = 89446.78.

The test exercises real worksheet save, review creation, all ten reviewed
amounts, review page, submission, confirmation, rendered version/key approval,
sequential retry and lock. No calculation/approval service is mocked. The route
clock is fixed to November 2026. Only fixture data and session authentication
are supplied. SQLite uses create_all; PostgreSQL uses the real migration chain.

Initial focused command: python -m pytest tests/test_synthetic_month_acceptance.py -q
Exact summary: `1 passed, 4 warnings in 20.93s`.

Combined focused command, RUN_LOCAL_RESTORE_REHEARSAL=1:
python -m pytest tests/test_restore_rehearsal.py tests/test_synthetic_month_acceptance.py -q
Exact summary: `2 passed, 4 warnings in 61.71s (0:01:01)`, exit 0.

Absence is a worksheet absence input, not a leave approval workflow. Its
post-tax treatment is the existing policy explicitly recorded above, not an
independent legal endorsement. Tests use CSRF-disabled Flask test clients;
browser/human acceptance, PDF/bank exports, real payment/filing, concurrency,
production restore and escrow recovery remain outside this evidence.
The PostgreSQL CI list does not include these files; reviewer wiring is separate.
Final full-suite and branch/head receipts are in the draft PR body.
