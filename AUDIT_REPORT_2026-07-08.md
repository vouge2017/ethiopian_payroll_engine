# 🔍 ETHIOPIAN PAYROLL ENGINE — BRUTAL HONESTY AUDIT

**Date:** July 8, 2026  
**Commit:** `9c4148a`  
**Auditor:** AI (automated codebase inspection)

---

## VERIFICATION SUMMARY

| What the tracker says | What actually exists |
|---|---|
| 197 tests passing | ✅ TRUE — 197 pass, 0 fail |
| 21 engine files | ✅ TRUE — 21 .py files, 4,718 lines |
| 16 test files | ❌ Actually 17 test files, 3,075 lines |
| "Employee portal complete" | ⚠️ Partially true — routes exist, data linking is fragile |
| "Role system complete" | ✅ Mostly true |
| "~25% completion" | ✅ Honest — about right |

---

## AUDIT 1: WHAT EXISTS (Engine Files)

| File | Lines | Purpose | Status |
|---|---|---|---|
| `main.py` | 1158 | Flask routes (all web UI) | ✅ Active |
| `models.py` | 517 | SQLAlchemy models | ✅ Active |
| `bank_file.py` | 403 | Bank CSV/XLSX generation | ✅ Active |
| `validation.py` | 259 | Pre-payroll validation | ✅ Active |
| `reports.py` | 244 | ERCA/pension Excel reports | ✅ Active |
| `pdf.py` | 209 | PDF payslip (Amharic font) | ✅ Active |
| `compliance.py` | 201 | Deadline tracking + scoring | ✅ Active |
| `api.py` | 176 | REST API endpoints | ✅ Active |
| `ethiopian_calendar.py` | 174 | Gregorian→Ethiopian converter | ✅ Active |
| `overtime.py` | 145 | Overtime calculation | ✅ Active |
| `i18n_om.py` | 133 | Afaan Oromoo strings | ✅ Active |
| `auth.py` | 125 | Login/register/phone auth | ✅ Active |
| `i18n.py` | 105 | Language system | ✅ Active |
| `payroll.py` | 97 | Core payroll calculation | ✅ Active — THE critical module |
| `pension.py` | 86 | Pension calculation | ✅ Active |
| `__init__.py` | 78 | Flask app factory | ✅ Active |
| `severance.py` | 161 | Severance calculator | ⚠️ **ORPHANED** — never called from main.py |
| `celery_app.py` | 158 | Celery background tasks | ⚠️ **ORPHANED** — no broker |
| `disbursement.py` | 106 | Telebirr stub | ⚠️ **ORPHANED** — in-memory only |
| `notification.py` | 35 | Email/Telegram stub | ⚠️ **ORPHANED** — prints to console |

**Orphaned modules: 4**

---

## AUDIT 2: TEST RESULTS

```
collected: 197
passed:    197
failed:    0
warnings:  215 (datetime.utcnow() deprecation + SQLAlchemy legacy API)
```

⚠️ First run failed with 13 errors — `flask-migrate` missing from `__init__.py` import. No `requirements.txt` exists. The project is un-installable from a clean environment.

---

## AUDIT 3: FEATURE-BY-FEATURE

### ✅ REAL FEATURES (work as claimed)

| Feature | Details |
|---|---|
| **Tax calculation** | 2025 brackets (Proclamation 1395/2025), DB-configurable, bilingual explanation |
| **Pension** | 7% employee / 11% employer, basic salary only |
| **Deduction order** | Pension → Taxable → Tax → Net (enforced in calculate_payroll) |
| **Overtime** | 1.25x/1.5x/2x/2.5x per Labor Proclamation 1156/2019 Art. 68, 20h/month limit |
| **Ethiopian calendar** | JDN-based, Pagume 5/6 leap year handling, verified correct |
| **Amharic PDF** | NotoSansEthiopic font in /fonts/, bilingual payslip labels |
| **Afaan Oromoo** | 79 strings in Qubee script |
| **Phone login** | 09XX, 07XX, +251 formats supported |
| **Role system** | owner / accountant / employee, multi-company via UserCompany |
| **Soft deletes** | is_deleted, deleted_at, deleted_by, preserves payroll history |
| **Audit trail** | AuditLog on payroll create/approve/reject, IP recorded |
| **Compliance dashboard** | ERCA (8th), pension (15th), PSSSA (10th) deadlines with countdown |
| **Reports** | ERCA Excel, pension report, bank file (CBE/Dashen/Awash/Telebirr) |
| **Mobile responsive** | responsive.css with @media queries, hamburger menu |
| **Approval flow** | Password re-auth, rejection with reason, audit logged |
| **Tenant isolation** | TenantQuery enforces company_id on all scoped models |

### ⚠️ FRAGILE FEATURES (exist but broken/hacky)

| Feature | Problem |
|---|---|
| **Employee self-service portal** | Finds employee by matching `current_user.phone` against `bank_or_telebirr` LIKE query. No `user_id` FK on Employee. If phone doesn't match bank field → employee sees nothing. |
| **Translation system** | i18n *works* but only **5 of ~126** template strings use `_()`. Rest are hardcoded English. Coverage: **~4%**. |
| **verify_status.py** | Reports "0 collected, 0 passed" internally then says "ALL PASS" — misleading |

### ❌ ORPHANED CODE (nobody calls these)

| Module | Status |
|---|---|
| `severance.py` | Well-written (Art. 40-42, 12-month cap) but zero routes, zero UI, zero template references |
| `celery_app.py` | No Redis broker, no worker, SMEs don't need async for 50-employee payrolls |
| `disbursement.py` | In-memory dict simulating Telebirr — does nothing |
| `notification.py` | `print()` to console — not wired into any flow |

---

## AUDIT 4: TRANSLATION COVERAGE

| Template | `_()` calls | Hardcoded English |
|---|---|---|
| base.html | 5 | ~10 |
| dashboard.html | 0 | ~15 |
| add_employee.html | 0 | ~8 |
| employees.html | 0 | ~5 |
| employee_detail.html | 0 | ~12 |
| payroll_confirm.html | 0 | ~8 |
| payroll_results.html | 0 | ~10 |
| payroll_runs.html | 0 | ~6 |
| reports.html | 0 | ~8 |
| auth/login.html | 0 | ~6 |
| auth/register.html | 0 | ~8 |
| employee_portal/*.html | 0 | ~20 |

**Coverage: ~4%** — the i18n system works, templates don't use it.

---

## AUDIT 5: EMPLOYEE MODEL GAPS

| Required Field | Status |
|---|---|
| id | ✅ |
| company_id | ✅ |
| employee_id | ✅ |
| name | ✅ |
| tin | ✅ |
| basic_salary | ✅ |
| allowances | ✅ |
| is_deleted | ✅ |
| deleted_at | ✅ |
| deleted_by | ✅ |
| **phone** | ❌ **MISSING** |
| **bank_account** | ❌ MISSING (has `bank_or_telebirr` — different semantics) |
| **department** | ❌ **MISSING** |
| **position** | ❌ **MISSING** |
| **start_date** | ❌ **MISSING** |

**5 of 15 fields missing.** No `user_id` FK on Employee — the portal links via phone string matching.

---

## THE HARD QUESTIONS

### 1. ACTUAL completion percentage?

**~30%.** Engine layer is strong (~70%). Web UI functional (~50%). Data model has gaps, translation barely started, employee-user linking is a hack.

### 2. SINGLE BIGGEST blocker for a real accountant?

**No `requirements.txt`.** The app won't start without `flask-migrate` which isn't documented. Beyond that: missing `department`, `position`, `start_date`, `phone` on Employee — fields every Ethiopian payroll form requires.

### 3. What 3 things to build next?

1. **Fix Employee model** — add `phone`, `department`, `position`, `start_date`, `bank_account`, `user_id` FK. The portal phone-matching hack will break in production.
2. **Create `requirements.txt`** — test `pip install -r requirements.txt && pytest` from clean env. Project is currently un-installable.
3. **Wire severance into "Terminate Employee"** — code is 90% done, needs one route and one button.

### 4. What to STOP building?

- **Celery** — delete `celery_app.py` or move to archive
- **Disbursement stub** — either build real Telebirr or delete
- **Notification stub** — `print()` to console helps nobody

---

## BOTTOM LINE

**Grade: B-**

Strong engine. Correct math. Real legal references. Decent tests. Honest self-assessment. But not usable by a real accountant today — data model gaps, missing requirements file, and a fragile employee portal linking mechanism stand between "impressive prototype" and "deployable product."
