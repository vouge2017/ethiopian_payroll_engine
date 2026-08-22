# CONSOLIDATED REMEDIATION PLAN — EthioPayroll

**Date:** 2026-08-21
**Status:** All P0/P1 items complete. P2 items documented for post-pilot.

---

## Phase 1: P0 — Critical (Production Blockers) ✅ COMPLETE

| # | Issue | Fix | Commit | Status |
|---|-------|-----|--------|--------|
| P0-0 | Database SSL drops | `?sslmode=require` on Render Postgres | Render Env Var | ✅ LIVE |
| P0-1 | 404 page crashes (500) | Fixed `url_for('employees.list_employees')` | `67a9c0f` | ✅ LIVE |
| P0-2 | Login lockout timezone TypeError | Removed duplicate `is_locked_out`, safe UTC handling | `93f3e14` | ✅ LIVE |
| P0-3 | MFA error flash missing | Descriptive flash message on invalid TOTP | `c43d940` | ✅ LIVE |

---

## Phase 2: P1 — High (Will Break with Real Users) ✅ COMPLETE

| # | Issue | Fix | Commit | Status |
|---|-------|-----|--------|--------|
| P1-1 | Payroll double-approval race | `version_id` + `StaleDataError` + `with_for_update()` | `34a82bd` | ✅ LIVE |
| P1-2 | Pytest suite deadlocks | Per-test `db.session.remove()` fixture | `9d5455b` | ✅ LIVE |
| P1-3 | No DR documentation | Render PITR protocol + dry-run restoration | `2941d45` | ✅ LIVE |

---

## Phase 3: P1 — Remaining Gaps ✅ ALL RESOLVED

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| H2 | Employee ID collision | `uq_employee_company_empid` unique constraint | ✅ Already existed |
| H3 | API no pagination | `page`/`per_page` with 200 cap | ✅ Already existed |
| M1 | `datetime.utcnow()` deprecation | Zero instances in codebase | ✅ Already clean |
| — | Missing notification/webhook tests | `test_notifications_webhooks.py` | ✅ Already existed |
| — | Portal rate limits | 3 POST endpoints rate-limited | ✅ Fixed (`f93dc4e`) |

---

## Phase 4: P2 — Medium (Post-Pilot Improvements)

| # | Issue | Impact | Effort | Priority |
|---|-------|--------|--------|----------|
| P2-1 | Statutory rule verification | 24 rules cited but unverified by human | 2 days (external) | After pilot |
| P2-2 | Court order cap — no legal citation | Validation references "statutory max 50%" without source | 1 hour | After pilot |
| P2-3 | Compliance deadlines — no legal citation | ERCA (25th), Pension (15th), Disbursement (5 days) unverified | 1 hour | After pilot |
| P2-4 | No minimum wage model | No guardrail preventing salary below minimum | 2 hours | After pilot |
| P2-5 | No max working hours enforcement | 48h/week limit not enforced | 2 hours | After pilot |
| P2-6 | No holiday calendar model | Public holidays not tracked | 4 hours | After pilot |
| P2-7 | No multi-level approval workflows | Only owner can approve payroll | 1 week | Scale phase |
| P2-8 | No shift/working schedule model | Assumes 26 days, 8 hours/day | 1 week | Scale phase |
| P2-9 | No department hierarchy | `department` is free-text field | 2 hours | Scale phase |
| P2-10 | No branch/location model | Single `company_id` only | 1 week | Scale phase |

---

## Phase 5: P3 — Low (Nice to Have)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| P3-1 | No response envelope on API list endpoints | Inconsistent API design | 2 hours |
| P3-2 | WhatsApp messages not Amharic | Employee notifications in English only | 4 hours |
| P3-3 | `referral.html` uses deprecated `document.execCommand` | Browser compat | 1 hour |
| P3-4 | No carry-forward leave configuration | Field exists, no UI/logic | 4 hours |
| P3-5 | No custom leave type definitions | `leave_type='custom'` accepted but no rules | 4 hours |

---

## Audit Findings (from AUDIT_REPORT.md)

### Critical (C1-C4) — All Fixed ✅

| # | Issue | Fix |
|---|-------|-----|
| C1 | `db.session.commit()` inside payroll transaction | Changed to `flush()` |
| C2 | Webhook thread safety | URL/secret resolved before thread spawn |
| C3 | TIN exposed in API | Removed from list endpoint |
| C4 | Undo approval missing row lock | Added `with_for_update()` |

### High (H1-H5) — All Fixed ✅

| # | Issue | Fix |
|---|-------|-----|
| H1 | N+1 query on employee import | Count once before loop |
| H2 | Employee ID collision | Unique constraint existed |
| H3 | API no pagination | Already implemented |
| H4 | `Employee.query.get()` without tenant check | Changed to `filter_by().first()` |
| H5 | Missing `IntegrityError` import | Restored |

---

## Deployment History

| Commit | Date | Description |
|--------|------|-------------|
| `67a9c0f` | 2026-08-15 | 404 error page fix |
| `93f3e14` | 2026-08-21 | Login lockout timezone fix |
| `c43d940` | 2026-08-21 | MFA flash message |
| `34a82bd` | 2026-08-21 | Payroll concurrency protection |
| `9d5455b` | 2026-08-21 | Pytest deadlock fix |
| `2941d45` | 2026-08-21 | PITR documentation |
| `f93dc4e` | 2026-08-21 | Portal rate limits |
| `e51ac4d` | 2026-08-21 | Pilot readiness report |

---

## Post-Pilot Roadmap

1. **Immediate (Week 1-2):** Send verification package to accountant, collect feedback
2. **Short-term (Month 1):** Address P2 items based on pilot feedback
3. **Medium-term (Month 2-3):** Multi-level approvals, holiday calendar, department hierarchy
4. **Long-term (Month 4+):** Multi-country support, SSO, SLA guarantees

---

*Plan created: 2026-08-21*
*Last updated: 2026-08-21*
