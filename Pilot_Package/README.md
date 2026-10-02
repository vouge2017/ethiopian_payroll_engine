# Pilot Package — Index

**Status:** Ready for the first controlled pilot (real accountant + real company +
real monthly payroll).

> This package is preparation, not validation. Validation is the human comparison
> the pilot accountant runs in the next maturity gate.

## Contents

| File | Purpose | Audience |
|---|---|---|
| `pilot_company_and_accountant.md` | Placeholder pilot company and accountant account setup, with the non-production isolation rules | Operator who provisions the pilot |
| `employee_import_template.csv` | 10-row, fully-valid CSV with Ethiopian names; matches the employee import schema | Pilot accountant for the first import |
| `discrepancy_log_template.md` | The log the pilot accountant fills in when EthioPayroll disagrees with Excel | Pilot accountant |
| `excel_comparison_template.csv` | Pre-populated comparison sheet (one row per (employee, field)) | Pilot accountant |
| `support_procedure.md` | How to report issues, response times, what the support team will and will not do | Pilot accountant |
| `recovery_procedure.md` | Per-company recovery (calculation error, data corruption, security incident, encryption key) | Operator / on-call |

## The four hard rules

1. **No real customer data** until the pilot accountant is on-boarded and
   the pilot company is real. Use `Pilot Test Co.` and the placeholder rows
   in `employee_import_template.csv` for testing the import flow.
2. **The pilot accountant must enable MFA** before the first payroll run.
   If the pilot accountant's account has `mfa_enabled=False`, block access
   and force enrolment.
3. **Every discrepancy is logged**, even `rounding` ones. The sign-off
   rule is in `discrepancy_log_template.md`.
4. **The encryption key escrow is operational before pilot starts**.
   See `../DISASTER_RECOVERY.md` Scenario 5 for the procedure.

## Companion documents (outside this folder)

- `../PILOT_PACKAGE.md` — high-level pilot onboarding and checklist
- `../PILOT_READINESS_EVIDENCE.md` — readiness evidence
- `../DISASTER_RECOVERY.md` — system-wide DR + key escrow procedure
- `../payroll_engine/cron_bp.py` — `/internal/cron/daily` endpoint (proves
  the cron is wired correctly; Render Cron Job hits it on schedule)
- `../migrations/versions/p0f1a2b3c4d5_payslip_unique_run_emp_type.py` —
  the UNIQUE(payroll_run_id, employee_id, payslip_type) migration
- `../tests/test_gate_payslip_unique.py` — local proof of the UNIQUE
  constraint
- `../tests/test_gate_payroll_immutability.py` — local proof of finalized
  payroll immutability
