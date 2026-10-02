# EthioPayroll — Post-Accountant Improvement Plan
**Created:** 2026-07-23
**Current Score:** ~6.3/10
**Target After All Items:** ~7.0/10

## Status

| # | Item | Status | Effort | Score Impact |
|---|------|--------|--------|-------------|
| 1 | Composite DB indexes | ✅ Done | 30 min | Performance 4→5 |
| 2 | Brute-force account lockout | ⏳ Pending | 1 hour | Security 8→8.5 |
| 3 | Onboarding tour | ❌ Removed — Quick Start wizard already exists | — | — |
| 4 | OpenAPI/Swagger docs | ⏳ Pending | 2 hours | Maintainability 8→9 |
| 5 | JSON structured logging | ⏳ Pending | 30 min | Observability 7→7.5 |
| 6 | Async PDF for single downloads | ⏳ Pending | 3 hours | Performance 5→6 |

## Blocked on Accountant (biggest lever)

| # | Item | Impact | Status |
|---|------|--------|--------|
| A1 | ERCA filing format verification | Compliance 5→8 | 📋 Package ready to send |
| A2 | 34 statutory rules verification | Compliance 8→9, Business 6→9 | 📋 Checklist ready |

**Accountant verification alone moves Compliance from 5→9 and Business Readiness from 6→9.**
This is the single highest-impact item and it's not in our hands.

---

## Item 1: Composite DB Indexes ✅

**Problem:** Hot queries scan full tables. Missing composite indexes on frequently filtered columns.

**Indexes added:**
- `Employee(company_id, is_deleted)` — used in almost every query
- `PayrollRun(company_id, status)` — used for filtering runs
- `Payslip(payroll_run_id, employee_id)` — used for payslip lookups
- `OvertimeEntry(company_id, date)` — used for monthly overtime
- `Leave(employee_id, status, start_date)` — used for leave queries

**Files:** `payroll_engine/models.py`, migration file

---

## Item 2: Brute-Force Account Lockout ⏳

**Problem:** Only rate limiting (5/min) on login. No account lockout after repeated failures.

**Approach:**
- Track failed login attempts per phone number in `SystemSetting` (already exists model)
- After 5 failures in 15 minutes → lock account for 30 minutes
- Show "Account locked. Try again in X minutes." message
- Reset counter on successful login
- Log lockout in audit trail

**Files:** `payroll_engine/auth.py`, `payroll_engine/models.py`
**Tests:** Lock after 5 failures, reset on success, unlock after timeout

---

## Item 4: OpenAPI/Swagger Docs ⏳

**Problem:** API has zero documentation. Third-party integrators can't use it.

**Approach:**
- Write a static `openapi.yaml` covering all `/api/v1/` endpoints
- Serve Swagger UI at `/api/v1/docs`
- Serve raw spec at `/api/v1/openapi.json`
- Don't rewrite existing routes — add docs route only
- Version-controlled, easy to maintain

**Files:** `payroll_engine/static/openapi.yaml`, `payroll_engine/api.py` (add docs route)
**Tests:** `/api/v1/docs` loads, `/api/v1/openapi.json` returns valid spec

---

## Item 5: JSON Structured Logging ⏳

**Problem:** Logs are plain text. Hard to parse, filter, or alert on in production.

**Approach:**
- Logging infrastructure already exists: `RequestIdFilter`, `_configure_logging()`
- Just swap `logging.Formatter` to `pythonjsonlogger.JsonFormatter` in production
- Keep plain text in development
- Fields: timestamp, level, message, module, request_id, method, path
- Keep existing logger calls — they still work, just formatted differently

**Files:** `payroll_engine/__init__.py`, `requirements.txt`, `requirements-lock.txt`
**Tests:** JSON format in production mode, plain text in dev mode

---

## Item 6: Async PDF for Single Downloads ⏳

**Problem:** Single payslip download generates PDF synchronously (28ms/emp). Will timeout at large companies.

**Approach:**
- `_ensure_pdf()` currently generates inline
- If Redis available: enqueue single PDF via RQ, show "Generating..." page, auto-refresh
- If Redis unavailable: keep inline (same as now)
- Reuse existing `PayslipGenerationJob` model and status page pattern

**Files:** `payroll_engine/pdf.py`, `payroll_engine/payroll_bp.py`, `payroll_engine/templates/pdf_generating.html`
**Tests:** Single PDF enqueued when Redis available, falls back to inline when not

---

## Score Projection

| Category | Current | After All Items | Ceiling |
|----------|---------|-----------------|---------|
| Architecture | 8 | 8 | 9 |
| Compliance | 5 | 5 (→9 with accountant) | 9 |
| Security | 8 | 8.5 | 9 |
| Performance | 4 | 6 | 7 |
| UX | 7.5 | 7.5 | 8.5 |
| Scalability | 3 | 3 | 5 |
| Maintainability | 8 | 9 | 9 |
| Observability | 7 | 7.5 | 8 |
| Business Readiness | 6 | 6 (→9 with accountant) | 9 |
| Enterprise | 3 | 3 | 4 |
| **Overall** | **6.3** | **~6.8** | **7.8** |
