# IMPLEMENTATION PLAN: Database Indexes + main.py Split

**Date:** 2026-07-13
**Author:** AI Technical Partner
**Status:** PENDING APPROVAL

---

## PART 1: DATABASE INDEXES

### Why Indexes First

- 30-minute change, zero risk to application logic
- Every query in the system benefits immediately
- No code changes required — just a migration
- Unblocks all future performance work

### Current State

The database has **3 indexes** (all from unique constraints):
- `uq_user_company` on `UserCompany(user_id, company_id)`
- `uq_employee_company_empid` on `Employee(company_id, employee_id)`
- `uq_leave_balance` on `LeaveBalance(company_id, employee_id, leave_type, year)`

**35 foreign keys exist with zero indexes on them.**

### Query Pattern Analysis

I analyzed every query in the codebase. Here are the columns that are filtered on most frequently:

| Column | Filter Count | Tables | Current Index? |
|--------|-------------|--------|----------------|
| `company_id` | 30+ | Employee, PayrollRun, Payslip, OvertimeEntry, Leave, AuditLog, EmployeeDeduction, EmployeeAllowance, LeaveBalance, FinalSettlement | ❌ No (except unique constraints) |
| `employee_id` (FK) | 15+ | Payslip, OvertimeEntry, Leave, EmployeeDeduction, EmployeeAllowance, LeaveBalance | ❌ No |
| `payroll_run_id` | 10+ | Payslip, PayrollValidationResult, PayrollDraft | ❌ No |
| `status` | 8 | PayrollRun, Leave | ❌ No |
| `is_deleted` | 5 | Employee | ❌ No |
| `date` | 4 | OvertimeEntry | ❌ No |
| `is_demo` | 2 | Company | ❌ No |
| `phone` | 2 | User | ✅ Yes (unique) |
| `email` | 2 | User | ✅ Yes (unique) |

### Proposed Indexes

**Single-column indexes (high impact):**

```sql
-- Employee: filtered on company_id in EVERY query
CREATE INDEX idx_employee_company_id ON employee(company_id);

-- PayrollRun: filtered on company_id in dashboard, runs list, reports
CREATE INDEX idx_payroll_run_company_id ON payroll_run(company_id);

-- Payslip: filtered on payroll_run_id in every report/download
CREATE INDEX idx_payslip_run_id ON payslip(payroll_run_id);

-- Payslip: filtered on employee_id in employee detail
CREATE INDEX idx_payslip_employee_id ON payslip(employee_id);

-- OvertimeEntry: filtered on company_id + date in dashboard
CREATE INDEX idx_overtime_company_id ON overtime_entry(company_id);

-- OvertimeEntry: filtered on employee_id in payroll calculation
CREATE INDEX idx_overtime_employee_id ON overtime_entry(employee_id);

-- Leave: filtered on company_id in leave management
CREATE INDEX idx_leave_company_id ON leave(company_id);

-- Leave: filtered on employee_id in leave balance
CREATE INDEX idx_leave_employee_id ON leave(employee_id);

-- AuditLog: filtered on company_id in audit log page
CREATE INDEX idx_audit_log_company_id ON audit_log(company_id);

-- EmployeeDeduction: filtered on company_id + employee_id
CREATE INDEX idx_deduction_company_id ON employee_deduction(company_id);
CREATE INDEX idx_deduction_employee_id ON employee_deduction(employee_id);

-- EmployeeAllowance: filtered on employee_id
CREATE INDEX idx_allowance_employee_id ON employee_allowance(employee_id);

-- PayrollValidationResult: filtered on payroll_run_id
CREATE INDEX idx_validation_run_id ON payroll_validation_result(payroll_run_id);

-- FinalSettlement: filtered on employee_id
CREATE INDEX idx_settlement_employee_id ON final_settlement(employee_id);

-- Employee: soft delete filter
CREATE INDEX idx_employee_is_deleted ON employee(company_id, is_deleted);
```

**Composite indexes (for common multi-column filters):**

```sql
-- Employee: most common query pattern (company + not deleted)
CREATE INDEX idx_employee_company_deleted ON employee(company_id, is_deleted);

-- PayrollRun: company + status (dashboard, runs list)
CREATE INDEX idx_run_company_status ON payroll_run(company_id, status);

-- Leave: company + status (leave management filter)
CREATE INDEX idx_leave_company_status ON leave(company_id, status);

-- OvertimeEntry: company + date range (dashboard overtime)
CREATE INDEX idx_overtime_company_date ON overtime_entry(company_id, date);
```

### What NOT to Index

- **Primary keys** — already indexed by default
- **Unique constraints** — already indexed
- **Low-cardinality columns** (booleans like `is_active`) — index won't help much
- **Columns only used in `get()` calls** — primary key lookup is already O(1)
- **Write-heavy tables with few reads** — index slows down writes for no benefit

### Migration Strategy

1. Create a single Alembic migration file
2. Use `CREATE INDEX CONCURRENTLY` if PostgreSQL (avoids table locks)
3. For SQLite (dev/test), regular `CREATE INDEX` is fine
4. No data changes — purely structural
5. Rollback: drop the indexes

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration fails on production | Low | High | Test on dev first, use CONCURRENTLY |
| Write performance degrades | Very Low | Low | Only adding indexes to read-heavy columns |
| Index bloat (too many indexes) | Low | Medium | 17 indexes is reasonable for 18 tables |
| Breaks existing queries | None | N/A | Indexes don't change query behavior |

### Estimated Time

- Migration file: 10 minutes
- Testing: 10 minutes
- Verification: 10 minutes
- **Total: 30 minutes**

---

## PART 2: SPLIT main.py INTO BLUEPRINTS

### Why This Is Harder Than It Looks

1. **29 templates** reference `url_for('main.xxx')` — changing the blueprint name means updating all of them
2. **Shared helpers** (`_company_id()`, `role_required()`, `_calculate_unpaid_leave_deduction()`) are used across routes
3. **`require_company` before_request handler** applies to all routes — needs to be on each blueprint or a shared parent
4. **Model imports** vary by route group — some routes use 10+ models
5. **Routes are interleaved** — employee routes reference payroll routes (e.g., employee detail shows payslips)

### Current main.py Structure (57 routes)

| Line Range | Domain | Routes | Lines |
|-----------|--------|--------|-------|
| 1-90 | Helpers | `_company_id`, `role_required`, `require_company` | 90 |
| 94-210 | Company | setup, dashboard, switch, demo | 120 |
| 226-310 | Dashboard | index (main dashboard) | 85 |
| 311-585 | Employees | list, add, edit, detail | 275 |
| 588-693 | CSV Templates | template download, prefilled CSV | 105 |
| 694-1037 | Payroll Workflow | upload, confirm, reject, approve | 345 |
| 1038-1350 | Payroll Extra | import, spreadsheet | 312 |
| 1354-1580 | Payroll Runs | runs list, lock, unlock, register, batch, detail, download | 230 |
| 1583-1600 | Payslip Download | single payslip download | 20 |
| 1597-1810 | Employee Features | overtime, allowances, deductions | 215 |
| 1810-2020 | Deduction Routes | stop, delete, deactivate, reactivate | 210 |
| 2020-2180 | Termination | terminate, settlement | 160 |
| 2182-2470 | Leave | balance, request, approve, reject, management | 290 |
| 2494-2640 | Reports | ERCA, pension, yearly, bank | 150 |
| 2640-2736 | Impact | impact calculator | 100 |
| 2736-2890 | Settings | team, invite, remove, link-user | 155 |
| 2889-3000 | Employee Portal | my dashboard, my payslips, my profile | 110 |

**Total: ~3,000 lines (including helpers and imports)**

### Proposed Blueprint Structure

```
payroll_engine/
├── __init__.py              # App factory (unchanged)
├── models.py                # Models (unchanged)
├── auth.py                  # Auth blueprint (unchanged)
├── api.py                   # API blueprint (unchanged)
├── main.py                  # REFACTORED: only helpers + dashboard + demo
│   ├── _company_id()
│   ├── role_required()
│   ├── require_company()
│   ├── setup_company()
│   ├── companies_dashboard()
│   ├── switch_company()
│   ├── demo_mode()
│   └── index() (dashboard)
├── employees.py             # NEW: Employee blueprint
│   ├── list_employees()
│   ├── add_employee()
│   ├── edit_employee()
│   ├── employee_detail()
│   ├── deactivate_employee()
│   ├── reactivate_employee()
│   └── link_user()
├── payroll.py               # NEW: Payroll blueprint
│   ├── payroll_upload()
│   ├── payroll_confirm()
│   ├── reject_payroll()
│   ├── approve_payroll()
│   ├── historical_import()
│   ├── payroll_spreadsheet()
│   ├── payroll_runs()
│   ├── lock_payroll()
│   ├── unlock_payroll()
│   ├── payroll_run_detail()
│   ├── download_all_payslips()
│   ├── payroll_register()
│   ├── batch_payslips()
│   ├── download_payslip()
│   ├── download_csv_template()
│   └── download_prefilled_csv()
├── employee_features.py     # NEW: Overtime, allowances, deductions
│   ├── add_overtime()
│   ├── delete_overtime()
│   ├── add_allowance()
│   ├── delete_allowance()
│   ├── add_deduction()
│   ├── stop_deduction()
│   └── delete_deduction()
├── leave_bp.py              # NEW: Leave blueprint
│   ├── employee_leave_balance()
│   ├── request_leave()
│   ├── approve_leave()
│   ├── reject_leave()
│   └── leave_management()
├── termination.py           # NEW: Termination & settlement
│   ├── terminate_employee()
│   └── view_settlement()
├── reports_bp.py            # NEW: Reports blueprint
│   ├── reports()
│   ├── download_erca()
│   ├── download_pension()
│   ├── download_yearly()
│   └── download_bank()
├── settings_bp.py           # NEW: Settings blueprint
│   ├── team_settings()
│   ├── invite_team_member()
│   └── remove_team_member()
├── employee_portal.py       # NEW: Employee self-service
│   ├── my_dashboard()
│   ├── my_payslips()
│   ├── my_payslip_detail()
│   └── my_profile()
└── impact_bp.py             # NEW: Impact calculator
    └── impact_calculator()
```

### Template URL Changes

Every `url_for('main.xxx')` in 29 templates must change:

| Old | New | Templates Affected |
|-----|-----|-------------------|
| `main.list_employees` | `employees.list_employees` | 9 |
| `main.add_employee` | `employees.add_employee` | 7 |
| `main.employee_detail` | `employees.employee_detail` | 6 |
| `main.payroll_upload` | `payroll.payroll_upload` | 11 |
| `main.payroll_runs` | `payroll.payroll_runs` | 4 |
| `main.payroll_confirm` | `payroll.payroll_confirm` | 2 |
| `main.approve_payroll` | `payroll.approve_payroll` | 2 |
| `main.payroll_spreadsheet` | `payroll.payroll_spreadsheet` | 4 |
| `main.reports` | `reports_bp.reports` | 2 |
| `main.leave_management` | `leave_bp.leave_management` | 2 |
| `main.approve_leave` | `leave_bp.approve_leave` | 2 |
| `main.reject_leave` | `leave_bp.reject_leave` | 2 |
| `main.terminate_employee` | `termination.terminate_employee` | 2 |
| `main.team_settings` | `settings_bp.team_settings` | 2 |
| `main.my_payslips` | `employee_portal.my_payslips` | 3 |
| `main.index` | `main.index` | (unchanged) |
| ... | ... | ... |

**Total template changes: ~60 url_for replacements across 29 files**

### Shared Dependencies

These must be accessible to all blueprints:

```python
# payroll_engine/shared.py (NEW)
from payroll_engine import db
from payroll_engine.models import Company, User, Employee, AuditLog

def _company_id():
    """Return the session-scoped active company ID."""
    from flask import session
    from flask_login import current_user
    return session.get('active_company_id', current_user.company_id)

def role_required(*roles):
    """Restrict access to users with specific roles."""
    from functools import wraps
    from flask import request, flash, redirect, url_for, abort
    from flask_login import current_user
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            effective_role = current_user.get_role_for_company(_company_id())
            if effective_role not in risks:
                flash('You do not have permission for this action.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### Registration in __init__.py

```python
# In create_app():
from payroll_engine.main import main as main_blueprint
from payroll_engine.employees import employees as employees_blueprint
from payroll_engine.payroll import payroll as payroll_blueprint
from payroll_engine.employee_features import employee_features as employee_features_blueprint
from payroll_engine.leave_bp import leave_bp as leave_blueprint
from payroll_engine.termination import termination as termination_blueprint
from payroll_engine.reports_bp import reports_bp as reports_blueprint
from payroll_engine.settings_bp import settings_bp as settings_blueprint
from payroll_engine.employee_portal import employee_portal as employee_portal_blueprint
from payroll_engine.impact_bp import impact_bp as impact_blueprint

app.register_blueprint(main_blueprint)
app.register_blueprint(employees_blueprint)
app.register_blueprint(payroll_blueprint)
app.register_blueprint(employee_features_blueprint)
app.register_blueprint(leave_blueprint)
app.register_blueprint(termination_blueprint)
app.register_blueprint(reports_blueprint)
app.register_blueprint(settings_blueprint)
app.register_blueprint(employee_portal_blueprint)
app.register_blueprint(impact_blueprint)
```

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Template url_for breaks | Certain | High | Automated find-and-replace + test suite |
| Circular imports | Medium | High | Shared module pattern, lazy imports |
| before_request not applied | Medium | High | Apply `require_company` to each blueprint |
| Route name conflicts | Low | Medium | Use unique blueprint names |
| Tests break | Medium | Medium | Run test suite after each blueprint extraction |
| Session/cookie behavior changes | Very Low | High | Blueprints share the same app context |

### Execution Order

**Step 1:** Create `shared.py` with `_company_id()`, `role_required()`, `_calculate_unpaid_leave_deduction()`

**Step 2:** Create `employees.py` blueprint (smallest domain, easiest to verify)

**Step 3:** Update templates referencing `main.list_employees`, `main.add_employee`, `main.employee_detail`, `main.edit_employee`

**Step 4:** Run tests — verify 384 pass

**Step 5:** Create `payroll.py` blueprint (largest domain, most routes)

**Step 6:** Update templates referencing `main.payroll_*`

**Step 7:** Run tests — verify 384 pass

**Step 8:** Create remaining blueprints (reports, leave, settings, employee_portal, impact, termination, employee_features)

**Step 9:** Update remaining templates

**Step 10:** Final test run — verify 384 pass

### Estimated Time

- Shared module: 30 minutes
- Employees blueprint: 45 minutes
- Payroll blueprint: 90 minutes
- Remaining blueprints: 90 minutes
- Template updates: 60 minutes
- Testing after each step: 30 minutes
- **Total: ~6 hours**

---

## PART 3: WHAT COULD GO WRONG

### Challenge 1: Template URL Breakage

**Problem:** 29 templates reference `url_for('main.xxx')`. Changing the blueprint name means updating all of them. Miss one → runtime error.

**Solution:** After each blueprint extraction, run `grep -r "url_for('main\." templates/` to find remaining references. Fix them before moving on. The test suite catches template errors at import time.

### Challenge 2: Circular Imports

**Problem:** `main.py` imports from `models.py`, `payroll.py`, `security.py`, `services/`. If `employees.py` also imports from these, and `models.py` imports from `main.py`, we get circular imports.

**Solution:** `models.py` does NOT import from `main.py`. The flow is: blueprints → models/services → (no reverse). Check for circular imports with `python3 -c "import payroll_engine.employees"` after each extraction.

### Challenge 3: Shared State

**Problem:** `_company_id()` reads from `session` and `current_user`. If this function is in `main.py`, other blueprints can't use it without importing from `main.py`.

**Solution:** Extract to `shared.py`. All blueprints import from `shared.py`. No circular dependency.

### Challenge 4: before_request Scope

**Problem:** `require_company` is a `@main.before_request` handler. If we split routes into other blueprints, those blueprints won't have this guard.

**Solution:** Apply `@main.before_request` to the main blueprint (dashboard, demo, setup). Apply a shared `require_company` decorator to routes in other blueprints. Or register it as `@app.before_request` (global).

### Challenge 5: Test Suite Breaks

**Problem:** Tests use `url_for('main.xxx')` or test routes by path. Blueprint name changes could break tests.

**Solution:** Tests mostly use paths (e.g., `client.get('/employees')`), not `url_for()`. Run tests after each extraction to catch breaks early.

---

## PART 4: CHALLENGE MY OWN PLAN

### Am I over-engineering the blueprint split?

**Yes, possibly.** 10 blueprints might be overkill for a 57-route app. A simpler approach:

**Option A (10 blueprints):** Maximum separation, cleanest code, most work (6 hours)
**Option B (5 blueprints):** Group related domains, less work (4 hours)
**Option C (3 blueprints):** Minimal split, fastest (2 hours)

**Option B seems right:**
- `main` — dashboard, demo, setup, company management
- `employees` — employee CRUD, overtime, allowances, deductions, termination, leave
- `payroll` — upload, workflow, spreadsheet, runs, register, batch
- `reports` — ERCA, pension, yearly, bank, audit log
- `settings` — team, invite, portal

This reduces template changes from ~60 to ~40 and blueprint count from 10 to 5.

### Am I under-estimating the index migration?

**Possibly.** Adding 17 indexes to a production database with data could take time. For small tables (< 1000 rows), it's instant. For large tables (100K+ rows), it could take minutes.

**Mitigation:** Test on dev with realistic data volumes first. Use `CREATE INDEX CONCURRENTLY` on PostgreSQL to avoid table locks.

### Should I do indexes and blueprints in the same PR?

**No.** Indexes are a database-only change with zero risk. Blueprints are a code-only change with moderate risk. Separate PRs = easier to review, easier to rollback.

### What about the template url_for changes?

**This is the riskiest part.** 60 find-and-replace operations across 29 files. One missed reference = runtime error on that page.

**Mitigation:** 
1. Automated `sed` replacement for each blueprint
2. `grep -r "url_for('main\." templates/` after each replacement to verify zero remaining
3. Test suite catches template errors at import time
4. Manual smoke test of key pages after each blueprint

---

## FINAL RECOMMENDATION

### Order of Operations

1. **Database indexes** (30 min) — zero risk, immediate benefit
2. **Create `shared.py`** (15 min) — extract shared helpers
3. **Split into 5 blueprints** (4-6 hours) — moderate risk, high benefit
4. **Update templates** (1 hour) — tedious but mechanical
5. **Test after each step** (30 min total)

### What I Need From You

1. **Approve the index list** — any columns I'm missing? Any indexes that shouldn't be added?
2. **Choose blueprint granularity** — 3, 5, or 10 blueprints?
3. **Approve the execution order** — indexes first, then blueprints?

### What I Will NOT Do

- Change any business logic
- Change any routes or URLs
- Change any database schema (beyond adding indexes)
- Change any test behavior
- Touch `auth.py` or `api.py` (they're already separate)

---

## APPENDIX: INDEX MIGRATION SQL

```sql
-- Migration: add_performance_indexes
-- Date: 2026-07-13
-- Description: Add indexes on frequently queried foreign keys and filter columns

-- Employee
CREATE INDEX IF NOT EXISTS idx_employee_company_id ON employee(company_id);
CREATE INDEX IF NOT EXISTS idx_employee_company_deleted ON employee(company_id, is_deleted);

-- PayrollRun
CREATE INDEX IF NOT EXISTS idx_payroll_run_company_id ON payroll_run(company_id);
CREATE INDEX IF NOT EXISTS idx_run_company_status ON payroll_run(company_id, status);

-- Payslip
CREATE INDEX IF NOT EXISTS idx_payslip_run_id ON payslip(payroll_run_id);
CREATE INDEX IF NOT EXISTS idx_payslip_employee_id ON payslip(employee_id);

-- OvertimeEntry
CREATE INDEX IF NOT EXISTS idx_overtime_company_id ON overtime_entry(company_id);
CREATE INDEX IF NOT EXISTS idx_overtime_employee_id ON overtime_entry(employee_id);
CREATE INDEX IF NOT EXISTS idx_overtime_company_date ON overtime_entry(company_id, date);

-- Leave
CREATE INDEX IF NOT EXISTS idx_leave_company_id ON leave(company_id);
CREATE INDEX IF NOT EXISTS idx_leave_employee_id ON leave(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_company_status ON leave(company_id, status);

-- AuditLog
CREATE INDEX IF NOT EXISTS idx_audit_log_company_id ON audit_log(company_id);

-- EmployeeDeduction
CREATE INDEX IF NOT EXISTS idx_deduction_company_id ON employee_deduction(company_id);
CREATE INDEX IF NOT EXISTS idx_deduction_employee_id ON employee_deduction(employee_id);

-- EmployeeAllowance
CREATE INDEX IF NOT EXISTS idx_allowance_employee_id ON employee_allowance(employee_id);

-- PayrollValidationResult
CREATE INDEX IF NOT EXISTS idx_validation_run_id ON payroll_validation_result(payroll_run_id);

-- FinalSettlement
CREATE INDEX IF NOT EXISTS idx_settlement_employee_id ON final_settlement(employee_id);
```
