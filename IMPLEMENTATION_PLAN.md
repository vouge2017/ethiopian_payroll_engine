# IMPLEMENTATION PLAN — Current Status & Next Steps

**Last updated:** 2026-07-13 22:40 UTC

---

## Completed Phases

### Phase 0: Baselines ✅

| Metric | Value |
|--------|-------|
| App startup | 5,483 ms |
| Dashboard (100 emp) | 11.4 ms |
| Payroll calc / emp | 1.01 ms |
| Spreadsheet (100 emp) | 2.1 ms (before N+1 fix) |
| ERCA report (10 emp) | 284 ms |
| Tests | 384 passed |
| Routes | 80 |

### Phase 1: Database Indexes ✅

17 indexes added via migration `j0k1l2m3n4o5`:

- `idx_employee_company_id`, `idx_employee_company_deleted`
- `idx_payroll_run_company_id`, `idx_run_company_status`
- `idx_payslip_run_id`, `idx_payslip_employee_id`
- `idx_overtime_company_id`, `idx_overtime_employee_id`, `idx_overtime_company_date`
- `idx_leave_company_id`, `idx_leave_employee_id`, `idx_leave_company_status`
- `idx_audit_log_company_id`
- `idx_deduction_company_id`, `idx_deduction_employee_id`
- `idx_allowance_employee_id`
- `idx_validation_run_id`
- `idx_settlement_employee_id`

### Phase 2: N+1 Query Fixes ✅

| Page | Before | After | Fix |
|------|--------|-------|-----|
| Dashboard | 25 queries | 8 | joinedload on overtime→employee |
| Spreadsheet | 87 queries | 7 | batch-load overtime, leave; cache tax/pension |
| Leave | N+1 | 5 | joinedload on leave→employee |
| Employees | 1 | 5 | already OK |

**Tax/pension caching:** `_get_brackets_and_relief()` and `_get_rates()` now cache per `for_date`. Eliminates ~80 TaxRule queries per payroll calculation. Test suite dropped from 58s to 46s.

---

## Next Phases (For Next Session)

### Phase 3: Standardize Shared Logic (NEXT)

**Goal:** Extract shared helpers before splitting main.py.

**What to extract:**

1. `shared.py` — shared helpers:
   - `_company_id()` — session-scoped active company
   - `role_required(*roles)` — decorator
   - `get_employee_or_404(emp_id)` — common pattern
   - `get_active_company()` — company lookup

2. `payroll_service.py` — payroll business logic:
   - `calculate_employee_payroll(employee, overtime, deductions)` — wraps calculate_payroll with employee context
   - `get_monthly_overtime(company_id)` — batch overtime loader
   - `get_monthly_leave_deductions(company_id, employees)` — batch leave loader

3. `report_service.py` — report generation:
   - `generate_erca(run_id)` — wraps ERCA report
   - `generate_pension(run_id)` — wraps pension report
   - `generate_bank_file(run_id, bank)` — wraps bank file

**Why before blueprints:**
- Reduces route handler complexity
- Makes blueprint extraction mechanical (routes become thin wrappers)
- Reduces risk of breaking business logic during split

**Estimated time:** 2-3 hours

### Phase 4: Blueprint Split

**5 blueprints:**

| Blueprint | Routes | Domain |
|-----------|--------|--------|
| `main` | 7 | Dashboard, demo, setup, company management |
| `employees` | 12 | CRUD, overtime, allowances, deductions, termination, leave |
| `payroll` | 16 | Upload, workflow, spreadsheet, runs, register, batch |
| `reports` | 6 | ERCA, pension, yearly, bank, audit log |
| `settings` | 5 | Team, invite, portal |

**Template changes:** ~60 `url_for('main.xxx')` → `url_for('payroll.xxx')` across 29 files.

**Estimated time:** 4-6 hours

### Phase 5: Service Layer (Incremental)

Only extract where already reused:
- PayrollService (calculate, validate, approve)
- EmployeeService (CRUD, search, dedup)
- ReportService (generate, download)

Don't create services for simple CRUD.

### Phase 6: Production Hardening

- Structured logging (JSON format, log levels)
- Health endpoint (`/health`, `/ready`)
- Request IDs (trace requests across logs)
- CI pipeline (GitHub Actions: lint, test, migrate)
- Migration test (verify migrations apply cleanly)
- Backup restore test

---

## Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|------------|
| 3 (Shared Logic) | Low | Pure extraction, no behavior change |
| 4 (Blueprints) | Medium | Template URL changes, test after each step |
| 5 (Services) | Low | Incremental, only where reused |
| 6 (Hardening) | Low | Additive changes, no behavior change |

---

## What NOT To Build

- Offline mode (different product)
- WhatsApp integration (pre-mature)
- Video walkthrough (pre-mature)
- Complex RBAC (3 roles is enough)
- Multi-level approval chains (SMEs don't need them)
- Celery/Redis (not yet needed at current scale)
