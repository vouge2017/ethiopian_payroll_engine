# EthioPayroll — Production Readiness Audit

**Date:** 2026-07-17
**Auditor:** Senior Engineering Review
**Scope:** All files changed in P0–P3 delivery (20 commits, 42 files, 3,886 lines)
**Tests:** 506 passed, 3 skipped, 0 failed

---

## File-by-File Scores

| File | Error Handling | Input Validation | Security | Performance | Code Quality | Test Gaps |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| `api.py` | 7 | 8 | 6 | 7 | 7 | 6 |
| `payroll_bp.py` | 6 | 7 | 6 | 7 | 6 | 5 |
| `models.py` (ApiKey) | 7 | 7 | 7 | 8 | 7 | 7 |
| `payroll.py` (flow) | 8 | 8 | N/A | 8 | 8 | 8 |
| `webhooks.py` | 4 | 5 | 5 | 6 | 5 | 1 |
| `notifications.py` | 4 | 5 | 5 | 6 | 5 | 1 |
| `wizard_bp.py` | 6 | 7 | 7 | 4 | 6 | 7 |
| `portal_bp.py` | 6 | 7 | 7 | 7 | 7 | 4 |
| `settings_bp.py` | 7 | 6 | 7 | 8 | 7 | 5 |
| `auth.py` (referral) | 7 | 7 | 7 | 8 | 7 | 6 |

---

## 1. CRITICAL — will break in production or is a security risk

### C1: `notifications.py` line 25 — `db.session.commit()` inside payroll approval transaction

```python
def create_in_app_notification(...):
    ...
    db.session.commit()  # ← COMMITS EVERYTHING
```

**What's wrong:** Called from `approve_payroll()` which has its own transaction. The `commit()` flushes all pending changes from the approval flow before the approval service has finished. If anything fails after this point, you have a half-approved payroll with notifications already sent.

**Status:** ✅ FIXED — changed to `db.session.flush()`

### C2: `webhooks.py` line 74 — `Company.query.get()` in background thread

```python
def fire_webhook(company_id, event, data):
    company = Company.query.get(company_id)  # ← runs before thread, but fragile
```

**What's wrong:** The company lookup runs in the request thread (correct), but the URL/secret were passed as object references to the background thread. If the session closes before the thread reads them, it could fail.

**Status:** ✅ FIXED — resolve URL/secret before spawning thread

### C3: `api.py` line 155 — `list_employees()` returns TIN field

```python
'tin': e.tin,  # ← TAX IDENTIFICATION NUMBER EXPOSED
```

**What's wrong:** TIN is a sensitive tax identifier. Exposing it in a list endpoint means any API token with `list_employees` access gets every employee's TIN.

**Status:** ✅ FIXED — removed from list view

### C4: `payroll_bp.py` line 436 — Undo approval has no row-level lock

```python
run = PayrollRun.query.filter_by(...).first_or_404()
```

**What's wrong:** The approval endpoint uses `with_for_update()`. The undo endpoint doesn't. Two concurrent undo requests could both pass the checks and both delete payslips.

**Status:** ✅ FIXED — added `.with_for_update()`

---

## 2. HIGH — will break when real users hit it

### H1: `wizard_bp.py` line 71 — N+1 query on every employee import

```python
for i, emp_data in enumerate(employees):
    existing_count = Employee.query.filter_by(...).count()  # ← QUERY PER ROW
```

**What's wrong:** For 500 employees, this runs 500 COUNT queries.

**Status:** ✅ FIXED — count once before loop

### H2: `wizard_bp.py` line 69 — Employee ID collision on concurrent imports

```python
emp_id = f'EMP{(existing_count + imported + 1):03d}'
```

**What's wrong:** Two users importing at the same time could generate the same `emp_id`. No unique constraint on `(company_id, employee_id)`.

**Status:** ⚠️ NOT FIXED — requires model change + migration. Low probability for beta.

### H3: `api.py` line 148 — `list_employees()` has no pagination

```python
employees = Employee.query.filter_by(...).all()
```

**What's wrong:** A company with 1000 employees returns all 1000 in one JSON response.

**Status:** ⚠️ NOT FIXED — acceptable for beta, must fix before scale.

### H4: `notifications.py` line 116 — `Employee.query.get()` without tenant check

```python
emp = Employee.query.get(leave.employee_id)
```

**What's wrong:** `.get()` bypasses the SoftDeleteQuery tenant isolation.

**Status:** ✅ FIXED — changed to `.filter_by(id=..., is_deleted=False).first()`

### H5: `api.py` line 5 — `IntegrityError` was removed but is used

**Status:** ✅ FIXED — restored the import

---

## 3. MEDIUM — code smell, technical debt

### M1: `datetime.utcnow()` deprecated (codebase-wide)

Used in 15+ files. Should be `datetime.now(datetime.UTC)`.

**Status:** ⚠️ NOT FIXED — pre-existing, not introduced by P0–P3.

### M2: `wizard_bp.py` line 69 — Dead code: duplicate name check does nothing

```python
existing = Employee.query.filter_by(..., name=name).first()
if existing:
    emp_id = f'EMP{...}'  # Same as line above
```

**Status:** ✅ FIXED — removed dead check

### M3: `api.py` `_get_company_id()` — fragile fallback

If `current_user.company_id` is None, returns None. Relies on `company_required` decorator.

**Status:** ⚠️ NOT FIXED — pre-existing pattern.

---

## 4. LOW — nice to have, not urgent

| Issue | Status |
|---|---|
| No response envelope on API list endpoints | Not fixed |
| WhatsApp messages not Amharic | Not fixed |
| `referral.html` uses deprecated `document.execCommand` | Not fixed |

---

## 5. MISSING

| What | Impact | Status |
|---|---|---|
| No test for `notifications.py` | Zero coverage | ⚠️ |
| No test for `webhooks.py` | Zero coverage | ⚠️ |
| No test for portal leave request | Untested | ⚠️ |
| No pagination on employee API | Breaks at scale | ⚠️ |
| No unique constraint on `(company_id, employee_id)` | Duplicate IDs possible | ⚠️ |
| No rate limit on portal leave request | Spammable | ⚠️ |
| No rate limit on adjustment creation | Spammable | ⚠️ |

---

## 6. DEAD CODE

| File | Line | What | Status |
|---|---|---|---|
| `payroll_bp.py` | 476 | `import os` (redundant, already at top) | ✅ FIXED |
| `wizard_bp.py` | 69-73 | Duplicate name check (did nothing) | ✅ FIXED |

---

## Fixes Applied

| Fix | File | Change |
|---|---|---|
| C1 | `notifications.py:25` | `commit()` → `flush()` |
| C2 | `webhooks.py:74` | Resolve URL/secret before thread spawn |
| C3 | `api.py:155` | Removed `tin` from list response |
| C4 | `payroll_bp.py:436` | Added `.with_for_update()` |
| H1 | `wizard_bp.py:71` | Count once before loop |
| H4 | `notifications.py:116` | `query.get()` → `filter_by().first()` |
| H5 | `api.py:5` | Restored `IntegrityError` import |
| M2 | `wizard_bp.py:69` | Removed dead duplicate name check |
| Dead | `payroll_bp.py:476` | Removed redundant `import os` |

---

## Final Verdict: **Ship with fixes**

**Minimum fixes applied above.** All critical issues resolved.

**Remaining items acceptable for beta (3–5 real users):**
- H2: Employee ID collision — low probability, add unique constraint before scale
- H3: API pagination — add before >100 employees per company
- M1: `datetime.utcnow()` — cleanup pass, not urgent
- Missing tests for notifications/webhooks — add before production

**Do NOT ship without:**
- ✅ C1–C4 fixes (applied)
- ✅ H1 fix (applied)
- ✅ H4 fix (applied)

**Next steps before production:**
1. Add tests for `notifications.py` and `webhooks.py`
2. Add unique constraint on `(company_id, employee_id)`
3. Add pagination to employee list API
4. Fix `datetime.utcnow()` deprecation (codebase-wide)
