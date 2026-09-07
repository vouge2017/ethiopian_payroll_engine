# EthioPayroll Progress Tracker

Last updated: 2026-07-09 22:35 UTC

---

## Current State

| Metric | Value |
|--------|-------|
| Engine .py files | 19 (3 archived) |
| Test files | 23 (4,290+ lines) |
| Tests passing | 245 |
| Tests skipped | 1 |
| Tests failing | 0 |
| Templates | 20 |
| Routes | 36 |
| i18n keys | 169 (119 used) |
| Migrations | 15 |
| **Overall completion** | **~65%** |

---

## Audit Fixes (External Architecture & Security Audit)

| Fix | Status | Commit | Description |
|---|---|---|---|
| FIX 1: Money type | ✅ Done | c39354a | Float → Numeric(12,2), Decimal for all math |
| FIX 2: Row lock on approval | ✅ Done | (this commit) | with_for_update() + client-side button disable |
| FIX 3: Rate limiting | ✅ Done | (this commit) | Flask-Limiter: 5/min login, 10/min approve, 200/hr default |
| FIX 4: Database indexes | ✅ Done | (this commit) | 4 indexes on hot FKs |
| FIX 5: Encrypt bank/tin | ✅ Done | (this commit) | AES-256 via sqlalchemy-utils, DB_ENCRYPTION_KEY in render.yaml |

---

## What Changed This Session (2026-07-09)

### From earlier today:
1. ✅ Removed rule codes from validation UI — human messages + "What to do?" hints
2. ✅ Professional report formatting — ERCA, pension, bank reports styled
3. ✅ First-run wizard — 3-step welcome box on dashboard
4. ✅ Cash compliance FLAG for ETB 30,000 limit (7 tests)
5. ✅ Audit log for employee changes — edit route, logging, audit page (6 tests)
6. ✅ Deployment readiness fixes — render.yaml startCommand, migration defaults
7. ✅ FIX 1: Float → Numeric(12,2) for all money columns, Decimal math

---

## Honest Layer Assessment

| Layer | % | What works | What's missing |
|---|---|---|---|
| Engine | 80% | Tax, pension, overtime, severance, Decimal math | Expat exemption, proration, leave |
| Web UI | 65% | 36 routes, 20 templates, edit employee, audit log | Report styling, guided wizard |
| Translation | 85% | 169 keys, 119 used, 3 languages | 4 hardcoded strings, 50 unused keys |
| Security | 55% | CSRF, RBAC, tenant isolation, Decimal money, audit log | Encryption, rate limiting |
| Testing | 70% | 245 tests, E2E test, Decimal precision tests | 10 routes untested via web UI |
| UX | 60% | Demo mode, 3-field form, drill-down, wizard, audit page | Guided onboarding |
| Infrastructure | 40% | Dockerfile, render.yaml, auto-deploy, migrations | No CI/CD, no monitoring |
| **Overall** | **~65%** | | |

---

## NEXT TASKS (ordered by audit priority)

### Critical (audit fixes)
1. FIX 2: Row lock on payroll approval — prevent double-payment
2. FIX 3: Rate limiting — brute-force protection
3. FIX 4: Database indexes — performance
4. FIX 5: Encrypt bank_account/tin — compliance

### High Priority
5. Remove 50 unused i18n keys
6. Privacy policy + Terms of Service
7. 10 untested web routes

### Medium Priority
8. Automated backups
9. Expat pension exemption
10. HTTPS enforcement (Talisman)

### Low Priority
11. Salary proration for mid-month hires
12. Leave management
13. CI/CD pipeline

---

## What NOT to Build

- Celery/Redis (archived, don't revisit)
- Disbursement stub (build real Telebirr or delete)
- Notification stub (delete)
- Complex RBAC (3 roles is enough)
- Multi-level approval chains (SMEs don't need them)
- Offline-first architecture (different product)
- ML anomaly detection (Phase 2+)
