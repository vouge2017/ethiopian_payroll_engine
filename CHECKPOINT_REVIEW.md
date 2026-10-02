# ETHIOPAYROLL — HARD CHECKPOINT REVIEW

**Date:** 2026-07-15
**Reviewer:** Technical co-founder / lead architect (adversarial mode)
**Repo:** `vouge2017/ethiopian_payroll_engine`
**Branch:** `main` (commit `1d6a6f2`)

---

## Executive Summary

This codebase has strong calculation math (Decimal throughout, pension-before-tax enforced structurally) and decent domain modeling. But it has a **broken test suite** (202 errors out of 384 claimed tests), a **3040-line monolith** `main.py` that was supposed to be split into blueprints, **no authentication recovery path** (no password reset), and **multiple false-confidence claims** in prior session reports. The product ends at "download a file" — there's no payment integration, no notification system, and no MFA on a system that approves money movement.

**Honest readiness:** This is a working prototype, not a product. It can demo. It cannot go to real users.

---

## 1. NEEDED BUT NOT BUILT AT ALL

### 1.1 Password Reset / Account Recovery

**Zero code.** No forgot-password flow, no email verification, no SMS OTP. If Tigist forgets her password, she's locked out permanently. The only recovery path is direct database manipulation.

**Impact:** Critical. No real user will adopt a system they can get locked out of.

**Evidence:** `auth.py` has `login`, `register`, `logout`, `change_password`, `google_login`, `google_callback`, `google_register`. No `forgot_password`, no `reset_password`, no `verify_email`.

### 1.2 MFA / Two-Factor Authentication

**Zero code.** Payroll approval — which moves real money — is protected only by a password re-check (`main.py` line 893: `if not password or not current_user.check_password(password)`). No TOTP, no SMS code, no hardware key support.

**Password strength is weak:** `password_policy.py` accepts `ethiopia2025` (12 chars, letters + digits, not in top-50 list). Doesn't require uppercase, special characters, or minimum entropy. Also accepts `addis2026`, `tigist123`, etc.

**Impact:** Critical for a financial system. A compromised password = full payroll access.

### 1.3 Notification System

**Zero production code.** `_archived/notification.py` is a `print()` stub:

```python
def send_notification(subject, body, recipients=None):
    print("=== NOTIFICATION ===")
    print(f"Subject: {subject}")
    ...
    return True
```

No email, no SMS, no push, no in-app notifications. When payroll completes, nobody gets told. When a leave request is submitted, the manager has to check the portal manually. When a compliance deadline approaches, only someone looking at the dashboard sees the banner.

**Impact:** High. Real payroll workflows require async notification.

### 1.4 Disbursement / Payment Rail Integration

**Zero production code.** `_archived/disbursement.py` has an in-memory stub using a Python dict (`_intents = {}`) — data lost on restart. The bank file generation (`bank_file.py`, 490 lines) produces files for CBE/Dashen/Awash/Telebirr, but there's no API integration. The flow ends at "download a file."

**Impact:** High. The product is a calculator + PDF generator, not a payroll system. Without payment integration, the accountant still manually uploads bank files.

### 1.5 Data Export / Migration Path

No way for a company owner to export their full employee list, payroll history, or compliance data to CSV/Excel from the UI. The ERCA and pension reports are specific formats — there's no general "export everything" option.

**Impact:** Medium. Locks users in. If Tigist wants to switch systems or hire an accountant who uses different software, there's no exit path.

### 1.6 Employee Self-Registration

Employees cannot create their own accounts. An admin must: (1) create an employee record, (2) create a user account, (3) link them via `/link-employee-user`. For a 50-person company, this is 150 admin operations.

**Evidence:** `main.py` line 2925: `_get_linked_employee()` checks `current_user.id` against `Employee.user_id`. No self-service link endpoint.

**Impact:** Medium. Scales badly. Creates support burden.

### 1.7 Search

No search functionality anywhere. No employee search, no payroll run search, no audit log search. The employee list page has a department filter dropdown (`main.py` line 317) but no text search. For 200+ employees, finding someone requires scrolling.

**Impact:** Medium. Basic usability gap.

---

## 2. BUILT BUT NOT SATISFACTORY

### 2.1 Password Policy (`password_policy.py`)

**50 lines.** Accepts passwords like:
- `ethiopia2025` — 12 chars, letters + digits, not in top-50 list ✅ (should fail: predictable pattern)
- `addis2026` — same issue
- `tigist1` — 7 chars ❌ (correctly rejected: too short)
- `aaaaaaaa1` — not all-same (has a digit), not sequential ✅ (should fail: obvious pattern)
- `password!` — not in top-50 list (top-50 has `password` but not `password!`) ✅ (should fail)

**What's missing:** No uppercase requirement, no special character requirement, no dictionary word check, no keyboard pattern check (`qwerty`, `asdfgh`), no repetition detection beyond all-same-character. The top-50 list is static and tiny.

### 2.2 Tax Bracket Caching (`tax.py` line 36)

```python
_brackets_cache = {}
```

Module-level dict with **no TTL, no size limit, no invalidation**. If an admin updates `TaxRule` in the database, the cached brackets persist until process restart. The comment says "rules rarely change during a request" but the cache is **per-process, not per-request**.

**Impact:** If Ethiopia changes tax brackets (they do — Proclamation 1395/2025 was recent), the system serves stale brackets until the gunicorn workers restart. No admin UI will fix this without a deploy.

### 2.3 Compliance Scoring (`compliance.py`)

`compute_compliance_score()` defaults `disbursement_date` to `today` when not provided. The `approve_payroll` route (line ~1030) calls:

```python
score, status = compute_compliance_score(payroll_date=run_date_str)
```

It never passes a `disbursement_date`. So the compliance score is **always green** because the system assumes disbursement happened on the same day as payroll. The score displayed on the dashboard is meaningless.

**Impact:** False confidence. Tigist sees a green 100% compliance score and thinks everything is fine, even if she hasn't actually disbursed salaries.

### 2.4 PDF Payslip (`pdf.py`, 239 lines)

Fixed-layout PDF using `reportlab`. Hardcoded template. No company logo, no configurable fields, no Amharic/English toggle. The payslip header says "Payslip / የደመወዝ ደብዳቤ" but the company name is the only customization.

**Impact:** Medium. Ethiopian businesses expect branded payslips. This looks like a system-generated receipt, not a professional document.

### 2.5 Employee Portal Overtime Calculation (`main.py` lines 2960-2980)

```python
ot_entries = OvertimeEntry.query.filter_by(
    employee_id=emp.id, company_id=_company_id()
).all()  # Fetches ALL overtime entries ever
ot_pay = sum(calculate_overtime_pay(emp.basic_salary, e.hours, e.overtime_type) for e in ot_entries)
```

Fetches all overtime entries for the employee's entire history, then filters by month in Python. Should be a single DB query with `OvertimeEntry.date >= month_start`.

**Impact:** Low now (small datasets), but grows linearly with employee tenure.

### 2.6 Validation Engine Silent Failure (`validation.py` lines 417-419)

```python
except Exception:
    # Database not available during tests or CSV-only validation
    pass
```

The `_check_active_deductions` function catches ALL exceptions and silently discards them. If the database is unreachable, if a model import fails, if there's a schema mismatch — deduction validation vanishes. A payroll run could proceed with invalid deductions and nobody would know.

**Impact:** High. This is the validation layer — the last safety net before money moves. Silent failure here defeats the purpose.

### 2.7 Historical Import (`main.py` lines 1044-1187)

The import reads CSV rows and creates payroll runs, but doesn't validate that `employee_id` values match existing employees. If someone imports with wrong IDs, the YTD data is corrupted with no way to fix it. No rollback mechanism, no preview step.

### 2.8 Flash Message Bug in Approval (`main.py` line ~1030)

After approving payroll, the flash message says:

> "Payroll ready for review! {count} employees, compliance score {score}%. Review and approve to process."

But the payroll was **just approved** — it should say "Payroll processed" or "completed." This is copy-pasted from the upload flow and never corrected. A user seeing "ready for review" after clicking "Approve" will be confused.

---

## 3. BUILT BUT NOT ACTUALLY WORKING PROPERLY

### 3.1 THE TEST SUITE IS BROKEN

**This is the most important finding in this review.**

Running `pytest -q` produces:
```
1 failed, 181 passed, 1 skipped, 206 warnings, 202 errors
```

The 202 errors are all `ModuleNotFoundError: No module named 'authlib'`. The Google OAuth dependency (`authlib`) is imported at app creation time (`__init__.py` line 109):

```python
from authlib.integrations.flask_client import OAuth
```

This import runs unconditionally — not guarded by a try/except or a config check. Every test that creates an app context fails. The `requirements.txt` lists `Authlib>=1.3.0` but it wasn't installed in this environment.

**The progress tracker claims "384 passed, 1 skipped, 0 failing."** This is **false** in the current state. Either:
- The tests were run in a different environment with authlib pre-installed
- The test count was inflated by a prior session
- The dependency was installed in a venv that wasn't captured

**Verdict:** You cannot trust any "tests passing" claim from prior sessions until this is fixed and re-verified.

### 3.2 TenantQuery Not Registered for UserCompany

`UserCompany` is used in `get_role_for_company` (`models.py` line ~268):

```python
def get_role_for_company(self, company_id):
    uc = UserCompany.query.filter_by(user_id=self.id, company_id=company_id).first()
    return uc.role if uc else self.role
```

But `UserCompany` is **NOT** registered with `TenantQuery.register_model()`. The `__init__.py` registers `Employee`, `PayrollRun`, `AuditLog`, `OvertimeEntry`, `EmployeeDeduction` — but not `UserCompany`.

This means `UserCompany` queries can leak cross-tenant data if someone forgets the `company_id` filter. The structural isolation claim doesn't cover all tenant-scoped models.

### 3.3 Leave Balance Double-Counting Risk

`leave_service.py` `approve_leave` (line ~200):

```python
balance.taken = (balance.taken or 0) + leave.days_requested
```

But `get_leave_balance` for annual leave (line ~100) also calls `get_leave_taken` which sums from the `Leave` table:

```python
taken = get_leave_taken(company_id, employee.id, leave_type, year, db_session)
balance.taken = taken
```

These two update paths can diverge. If `get_leave_balance` is called between the `approve_leave` flush and the next query, the increment from `approve_leave` gets overwritten by the DB sum. This is a race condition that could cause leave balance to show incorrect values during concurrent operations.

### 3.4 Approval Flow Has No Transaction Boundary

`approve_payroll` (`main.py` lines 871-1044) does **5 separate `db.session.commit()` calls** in one request:

1. Status → `processing` (line 938)
2. Status → `completed` + audit log (line 1021-1030)
3. Delete draft (line 1035)
4. (Inside the try block, multiple flushes)

If the process crashes between commit 2 and commit 3, you have a payroll run stuck in "completed" status with the draft still in the database. If it crashes between commit 1 and commit 2, it's stuck in "processing" with some payslips generated and others not. There's no recovery mechanism.

### 3.5 Rate Limiting Is Per-Worker

Flask-Limiter defaults to in-memory storage. With gunicorn running 4 workers (common for production), each worker has its own rate limit counter. Login brute-force gets `5 attempts × 4 workers = 20 attempts/minute`, not 5.

**Evidence:** The test warning is explicit:
```
UserWarning: Using the in-memory storage for tracking rate limits as no storage was explicitly specified.
```

No Redis or database-backed rate limit storage is configured in `__init__.py` or `config.py`.

---

## 4. NOT COMPLETED

### 4.1 Blueprint Split

**Status: Not started.** `main.py` is **3040 lines** with **60+ route functions**. The progress tracker says "Phase 3: Standardize Shared Logic (NEXT)" and "Phase 4: Blueprint Split." Neither has begun.

Every session makes this file worse. The approval flow alone is 170 lines of inline business logic (lines 871-1044) that should be in a service.

### 4.2 Service Layer

`services/` has 4 files:
- `payroll_workflow.py` (180 lines) — CSV parsing + draft creation
- `leave_service.py` (245 lines) — leave balance + request/approve/reject
- `settlement_service.py` (195 lines) — final settlement calculation
- `allowance_service.py` (175 lines) — allowance management

But the bulk of business logic is still in route handlers:
- `approve_payroll` (170 lines) — inline in `main.py`
- `add_employee` (110 lines) — inline in `main.py`
- `add_deduction` (165 lines) — inline in `main.py`
- `terminate_employee` (100 lines) — inline in `main.py`

The services exist for **new** features but legacy routes weren't refactored.

### 4.3 Allowance Migration

`allowance_service.py` has `migrate_legacy_allowances()` that converts the single `Employee.allowances` field into granular `EmployeeAllowance` records. But there's **no migration UI, no migration route, no admin command**. Old employees with the legacy field will forever use the fallback path in `get_effective_allowances()`.

### 4.4 i18n Completion

- 169 keys total, 119 used, **50 dead keys** cluttering the codebase
- `i18n_om.py` (Afaan Oromoo, 201 lines) exists but no evidence of native speaker review
- No Amharic quality review
- No RTL layout support for Amharic/Oromoo text in templates

### 4.5 Audit Log Hash Chain

Migration `a25e900abcde_add_audit_log_hash_chain.py` exists (suggesting tamper-evident audit was planned), but the `AuditLog` model in `models.py` has no `previous_hash` or `hash` column. The migration name is aspirational; the implementation doesn't exist.

---

## 5. REMAINING WORK — RE-PRIORITIZED BY ACTUAL IMPACT

| Priority | Item | Why This Order |
|----------|------|----------------|
| 1 | Fix test suite (202 errors) | Can't verify anything else until this works |
| 2 | Password reset flow | Zero users will adopt a system they can get locked out of |
| 3 | Blueprint split (main.py → 5 modules) | 3040-line file is a maintenance hazard causing bugs |
| 4 | MFA / 2FA | Payroll approval with password-only is a financial liability |
| 5 | Compliance scoring fix | Current score is always green (false confidence) |
| 6 | Notification system | Nobody gets told when anything happens |
| 7 | Rate limiter → Redis backend | Current per-worker limits are 4× too permissive |
| 8 | Transaction boundary in approval | 5 commits in one request = partial failure risk |
| 9 | PDF payslip customization | Branded payslips expected by Ethiopian businesses |
| 10 | Disbursement integration | Product ends at "download a file" |
| 11 | Employee self-registration | Scales badly without it |
| 12 | Search functionality | Basic usability for 100+ employees |
| 13 | Data export / migration path | Prevents lock-in |
| 14 | i18n completion + quality review | 50 dead keys, no native review |
| 15 | CI/CD pipeline | 384 tests with no automated way to run them on push |

---

## 6. OVERBUILT / OVERENGINEERED

### 6.1 TenantQuery (`models.py` lines 66-180)

**115 lines** of recursive SQL clause-walking, thread-local context managers, and structural enforcement. For a product with **zero multi-tenant deployments** and **zero background workers**.

- `set_tenant_context()` / `clear_tenant_context()` / `tenant_context()` — designed for Celery workers. Celery is archived (`_archived/celery_app.py`).
- `_clause_has_column()` — recursively walks SQLAlchemy clause trees. 30 lines of reflection code.
- `_tenant_scoped_models` — a class-level set that requires manual registration.

**Should it exist?** Eventually, yes. **Should it have been built before MFA, password reset, or notifications?** No. This is infrastructure for a scale that doesn't exist yet, built while basic user-facing features are missing.

**Cost:** Every new model requires thinking about whether to register it. `UserCompany` wasn't registered (section 3.2). The abstraction creates cognitive overhead without delivering user value.

### 6.2 EmployeeAllowance Model (`models.py` lines 370-490)

**120 lines.** 10 allowance types, per-type tax treatment, exempt caps with percentage-of-salary basis, regulatory references, effective/end dates, calculation basis (fixed vs percentage).

In practice, the system uses exactly **two**: transport (partial exempt) and "other" (taxable). The other 8 types (hardship, housing, communication, per_diem, medical, food, education, uniform) have **zero records** anywhere in the codebase. The `migrate_legacy_allowances` function creates a single "General Allowance" record.

**Cost:** The `calculate_payroll` function (payroll.py) has a 20-line branch for `allowance_records` vs legacy `allowances`. Every employee query now potentially hits the `EmployeeAllowance` table. The schema supports a 500-employee corporation; the product serves 10-person SMEs.

### 6.3 The `_archived/` Directory

5 files totaling ~300 lines:
- `celery_app.py` — Celery worker configuration
- `disbursement.py` — Telebirr stub
- `notification.py` — print() stub
- `telegram.py` — Telegram bot stub
- `whatif.py` — What-if calculator (superseded by `impact.py`)

These should be **deleted**, not archived. They're not documentation — they're dead code that will confuse anyone who reads the repo. If they're needed later, they're in git history.

### 6.4 Migration Helper (`migration.py`, 306 lines)

Standalone functions like `migrate_employee_fields`, `migrate_phone_field`, `migrate_overtime_entries`. Imported by some tests but never called in production routes. This is dead code that should be a Flask management command or deleted.

---

## 7. BUILT BUT TOO SIMPLE / WILL BREAK AT SCALE

### 7.1 Synchronous PDF Generation in Approval Flow

`approve_payroll` (`main.py` line ~985):

```python
for emp_data in employees_data:
    ...
    pdf_path = generate_payslip(emp_data)
    ...
```

Generates PDFs sequentially in the request thread. For 50 employees: ~10 seconds. For 500 employees: ~100 seconds. Render's default gunicorn timeout is 30 seconds. **This will timeout and leave payroll in "processing" status with no way to recover.**

### 7.2 Module-Level Tax Cache With No Invalidation

`tax.py` line 36: `_brackets_cache = {}`

No size limit. No TTL. No invalidation on `TaxRule` update. In a long-running gunicorn process serving multiple companies, this grows forever AND returns stale data if brackets change.

### 7.3 Rate Limiter Storage

As noted in section 3.5, in-memory rate limiting with multiple workers = 4× the intended limit. But it's worse than that: each worker restart resets its counter. An attacker can trigger worker restarts (e.g., by sending requests that cause OOM) to reset rate limits.

### 7.4 No Pagination on Employee/Payslip Queries

`list_employees` (`main.py` line 317) does:

```python
employees = Employee.query.filter_by(...).all()
```

`.all()` loads every employee into memory. For 10 employees: fine. For 1000 employees: memory spike, slow response, potential OOM on a 512MB Render instance.

The template has a `_pagination.html` partial, but it's not used by the employee list route.

### 7.5 No Connection Pooling Configuration

`config.py` has no `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_POOL_TIMEOUT`, or `SQLALCHEMY_POOL_RECYCLE` settings. SQLAlchemy defaults to 5 connections. With gunicorn running 4 workers, that's 20 connections. PostgreSQL's default `max_connections` is 100. At 5 concurrent users, you're already at 20% capacity before any other service connects.

---

## 8. WHAT HASN'T BEEN SHOWN

### 8.1 `retention.py` (107 lines)

Never mentioned in any progress tracker or assessment. Contains `purge_expired_payslip_pdfs`, `purge_expired_drafts`, `purge_expired_uploads`. Configurable retention periods via environment variables. Deletes files and audit-logs the purge.

**Risk:** If `RETENTION_PAYSLIP_PDF_DAYS` is set to 0 or a very small number, payslips could be deleted immediately after generation. The code has no safety floor. Also, `purge_expired_payslip_pdfs` sets `company_id=0` in the audit log — this won't be visible in any tenant-scoped audit query.

### 8.2 `impact.py` (255 lines)

Management impact calculator. Imported only by `api.py` (4 endpoints). Has `preview_salary_raise`, `preview_new_hire`, `preview_termination`, `preview_allowance_change`. These are API-only — no UI template. The web UI has `impact_calculator.html` (579 lines, the largest template) but I see no route that renders it with actual data.

**Risk:** Dead code? Or a feature that was built for the API but never wired into the web UI?

### 8.3 `celery_worker.py` (root level)

```python
# Celery worker — not used in production (archived)
```

A file at the repo root that's explicitly marked as not used. Should be deleted.

### 8.4 `wsgi.py` (referenced in `render.yaml`)

```yaml
startCommand: flask db upgrade && gunicorn --bind 0.0.0.0:$PORT wsgi:app
```

I don't see this file examined. If it doesn't exist or has issues, the Render deployment is broken.

### 8.5 The `attendance` Relationship

`Employee` model has:

```python
attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
```

But there's no `Attendance` model in `models.py`. This relationship references a model that doesn't exist. It won't fail until someone tries to access `employee.attendance_records`, at which point SQLAlchemy will raise an error.

### 8.6 `Flask-Babel` in requirements.txt

`requirements.txt` lists `Flask-Babel>=4.0.0` but the codebase uses a custom `i18n.py` / `i18n_om.py` system instead. Flask-Babel is installed but never used — dead dependency.

### 8.7 The `demo.py` Hardcoded Data

```python
'basic_salary': 10000, 'allowances': 2000,
'bank_or_telebirr': 'dashen:2000987654321',
'bank_account': '2000987654321',
```

Demo employees have hardcoded bank account numbers. If someone deploys the demo mode and forgets to disable it, these fake bank accounts could end up in real bank files.

---

## 9. DESKTOP vs PWA vs HYBRID — RECOMMENDATION

**Position: PWA-first, with a future desktop wrapper if needed.**

**Justification against what's in the repo:**

1. **The employee portal already exists as web.** `employee_portal/dashboard.html`, `payslips.html`, `payslip_detail.html`, `profile.html` — 4 templates, all Jinja2, all served by Flask routes. The portal depends on `current_user` session auth. Rebuilding this as a desktop app means rewriting all of it.

2. **The accountant workflow is web-native.** CSV upload, spreadsheet editor, payroll confirmation — all are form-based HTTP flows. The spreadsheet template (`payroll_spreadsheet.html`, 206 lines) uses HTML tables with inline editing. Desktop-first would mean Electron wrapping a web UI — all the overhead of a browser with none of the reach.

3. **Ethiopian internet is mobile-first.** Tigist's employees check payslips on their phones. A desktop app requires every employee to install software. A PWA works in Chrome on a $100 Android phone.

4. **The Flask stack is already deployed as a web service.** `render.yaml` configures a web service with gunicorn. The entire infrastructure assumes HTTP. Going desktop means abandoning Render and building a different deployment model.

5. **The "max result" argument for desktop is wrong here.** Desktop-first makes sense for offline-heavy, compute-intensive, or native-UI applications. Payroll is none of these. It's a CRUD app with a calculation engine. The web is the right delivery model.

6. **The one valid desktop argument — offline — is already not built.** The progress tracker lists "Offline mode" as "Not Built." If offline is needed later, a PWA with service workers gets you 80% there without a desktop wrapper.

**What to build:**
- Add `manifest.json` and a service worker for PWA installability
- Add `beforeinstallprompt` handling to the base template
- This is ~2 days of work and gives Tigist's employees an app-like experience on their phones

---

## 10. PRIORITIZED PUNCH LIST — TOP 5

### 1. FIX THE TEST SUITE
**Why first:** You cannot verify any other claim until this works. 202 errors = 202 untested code paths. Fix the `authlib` import (guard it with try/except or add it to the test environment), re-run, and get the real pass count. If it's not 384, the prior session's claims were inflated.

**Effort:** 1 hour.

### 2. PASSWORD RESET FLOW
**Why second:** No real user will adopt a system they can get locked out of. This is the #1 blocker for any pilot. Build: email-based reset with time-limited tokens (Flask-Login's `confirm_token` pattern). Even a simple "admin can reset any password" route is better than nothing.

**Effort:** 1 day.

### 3. BLUEPRINT SPLIT (main.py → 5 modules)
**Why third:** The 3040-line main.py is the root cause of most "built but not satisfactory" issues. Business logic is mixed with HTTP handling because there's no clean separation point. Split into: `employees.py`, `payroll.py`, `reports.py`, `settings.py`, `portal.py`. Each gets its own service module. This unblocks everything else.

**Effort:** 2-3 days.

### 4. FIX THE 5 REAL BUGS
These were found by reading the code, not by running tests:
- Flash message says "ready for review" after approval (`main.py` line ~1030)
- Compliance score always green (`compliance.py` default disbursement_date)
- `Attendance` model referenced but doesn't exist (`models.py` line ~340)
- Silent `except Exception: pass` in validation (`validation.py` line 417)
- Tax cache never invalidates (`tax.py` line 36)

**Effort:** 2 hours.

### 5. MFA / TOTP
**Why fifth:** A payroll system that approves money movement with only a password — and that password is `ethiopia2025` — is a liability. Add TOTP via `pyotp` + QR code in the user settings page. Require MFA for the `owner` role on the approval endpoint.

**Effort:** 2 days.

---

## APPENDIX: VERIFIED TEST RESULTS

```
Command: python3 -m pytest -q
Result:  1 failed, 181 passed, 1 skipped, 206 warnings, 202 errors
Runtime: ~8 seconds
Error:   ModuleNotFoundError: No module named 'authlib'
```

Tests that actually pass (181): tax, pension, overtime, severance, calendar, i18n, bank file, compliance, validation, payroll calculation, phone auth.

Tests that error (202): everything that creates an app context (routes, auth, tenant isolation, services, deductions, e2e, employee portal, security, roles, etc.).

The "384 passed" claim from the progress tracker is unverifiable and likely false in the current environment state.

---

## APPENDIX: FILE METRICS

| File | Lines | Status |
|------|-------|--------|
| `main.py` | 3040 | Monolith, needs split |
| `models.py` | 1076 | Overengineered for current scale |
| `bank_file.py` | 490 | Solid, domain-correct |
| `reports.py` | 460 | Functional |
| `validation.py` | 443 | Silent failure risk |
| `api.py` | 363 | Clean, well-structured |
| `auth.py` | 327 | Missing password reset |
| `leave.py` | 316 | Good domain modeling |
| `migration.py` | 306 | Dead code |
| `payroll.py` | 296 | Strong — single entry point |
| `__init__.py` | 270 | Hard OAuth import |
| `impact.py` | 255 | API-only, no UI wiring |
| `pdf.py` | 239 | Minimal, needs customization |
| `tax.py` | 235 | Cache invalidation issue |
| `i18n.py` | 231 | 50 dead keys |
| `demo.py` | 209 | Hardcoded bank data |
| `compliance.py` | 201 | Always-green score |
| `ethiopian_calendar.py` | 174 | Solid |
| `retention.py` | 107 | Never mentioned, untested |
| `password_policy.py` | 57 | Too permissive |
| `security.py` | 75 | Good (redirect safety, CSV injection) |
| `services/` (4 files) | 795 | New features only, legacy not refactored |

**Total engine:** ~9,828 lines across 25 Python files
**Total tests:** 6,935 lines across 37 files (but 202 error out)
**Templates:** 35 HTML files, 4,684 total lines

---

*End of checkpoint review.*
