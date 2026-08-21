# FINAL PILOT EVIDENCE CHECK — EthioPayroll

**Date:** 2026-08-21
**Auditor:** System Audit
**Instruction:** Read-only verification. No code, config, DB, or documentation changes.

---

## 1. Git Ancestry

**Claim:** Latest production commit `e51ac4d` contains all hardening commits.

**Verification:**

| Commit | Description | Ancestor of HEAD? |
|--------|-------------|-------------------|
| `67a9c0f` | 404 error page fix | ✅ YES |
| `93f3e14` | Login lockout timezone | ✅ YES |
| `c43d940` | MFA flash message | ✅ YES |
| `34a82bd` | Payroll concurrency | ✅ YES |
| `9d5455b` | Pytest deadlock fix | ✅ YES |
| `2941d45` | PITR documentation | ✅ YES |

**Result:** ✅ VERIFIED — All 6 commits are ancestors of HEAD. Linear history confirmed.

**Note:** HEAD is actually `0f4986a` (2 commits ahead of `e51ac4d`), but `e51ac4d` also contains all 6 commits.

---

## 2. Hardening Fix Verification Chains

### P0-1: 404 Error Handling

| Link | Evidence | Status |
|------|----------|--------|
| Source code | `404.html:39` uses `url_for('employees.list_employees')` | ✅ |
| Test | `test_input_validation.py` has 4 tests for 404 on deleted/missing resources | ⚠️ INDIRECT — tests 404 responses but not the specific `url_for` fix |
| Commit | `67a9c0f` — 1 file changed, 1 insertion | ✅ |
| Deployed | Commit is ancestor of HEAD | ✅ |
| Production evidence | None — no screenshot, curl test, or Render log provided | ❌ UNVERIFIED |

**Chain status:** ⚠️ CODE VERIFIED, PRODUCTION UNVERIFIED

---

### P0-2: Login Lockout Timezone

| Link | Evidence | Status |
|------|----------|--------|
| Source code | `models.py:1668` — single `is_locked_out` method, UTC handling present | ✅ |
| Test | `test_lockout.py` — `test_lockout_after_max_attempts`, `test_lockout_remaining_decreases`, `test_lockout_message_after_max_failures` | ✅ |
| Commit | `93f3e14` — removed duplicate method | ✅ |
| Deployed | Commit is ancestor of HEAD | ✅ |
| Production evidence | None — no log showing timezone handling in production | ❌ UNVERIFIED |

**Chain status:** ⚠️ CODE + TEST VERIFIED, PRODUCTION UNVERIFIED

---

### P0-3: MFA Error Flash

| Link | Evidence | Status |
|------|----------|--------|
| Source code | `auth.py:580` — `flash('Invalid authentication code...')` | ✅ |
| Test | `test_mfa.py` — `test_mfa_verify_page_loads`, `test_mfa_verify_sets_session_flag` | ⚠️ INDIRECT — tests MFA flow but not the specific flash message text |
| Commit | `c43d940` — 1 file changed, 1 insertion | ✅ |
| Deployed | Commit is ancestor of HEAD | ✅ |
| Production evidence | None — no screenshot of flash banner | ❌ UNVERIFIED |

**Chain status:** ⚠️ CODE VERIFIED, PRODUCTION UNVERIFIED

---

### P1-1: Payroll Approval Concurrency

| Link | Evidence | Status |
|------|----------|--------|
| Source code | `models.py:834` — `version_id` column; `models.py:837` — `__mapper_args__`; `payroll_bp.py:892` — `StaleDataError` handling | ✅ |
| Test | **NO TEST EXISTS** for `version_id`, `StaleDataError`, or concurrent approval | ❌ |
| Commit | `34a82bd` — 2 files changed, 17 insertions | ✅ |
| Deployed | Commit is ancestor of HEAD | ✅ |
| Production evidence | None | ❌ UNVERIFIED |

**Chain status:** ❌ CODE VERIFIED, NO TEST, PRODUCTION UNVERIFIED

---

### P1-2: Pytest Deadlock Fix

| Link | Evidence | Status |
|------|----------|--------|
| Source code | `conftest.py:41` — `_db_session_cleanup` fixture with `db.session.remove()` | ✅ |
| Test | N/A — this IS the test infrastructure fix | N/A |
| Commit | `9d5455b` — 1 file changed, 13 insertions | ✅ |
| Deployed | Commit is ancestor of HEAD | ✅ |
| Production evidence | N/A — test infrastructure, not production code | N/A |

**Chain status:** ✅ VERIFIED (test infrastructure only)

---

## 3. Concurrency — Deep Verification

### 3.1 Does `version_id` exist in production DB?

**Cannot verify.** No migration file for `version_id` was found in `migrations/versions/`. The column exists in the model code (`models.py:834`), but:

- ❌ No Alembic migration adding `version_id` to `payroll_run` table
- ❌ No evidence that `flask db migrate` or `flask db upgrade` was run on production
- ❌ Cannot confirm the column exists in the Render PostgreSQL database

**Risk:** If the column doesn't exist in the DB, SQLAlchemy will fail on any query involving `PayrollRun`. However, the app is reportedly running, which suggests either:
- The column was added manually, OR
- SQLAlchemy is not yet exercising the `version_id` path, OR
- The migration exists but wasn't committed to this repo

### 3.2 Is the production app running the versioned model?

**Cannot verify.** The code is on `main` and Render auto-deploys from `main`. If the migration hasn't run, the app would crash on startup (SQLAlchemy would fail to map the model). Since no crash is reported, the column likely exists — but this is inference, not evidence.

### 3.3 Does a concurrency test exist?

**NO.** Searched all test files for:
- `version_id` — not found in tests
- `StaleDataError` — not found in tests
- `concurrent` — not found in tests (except `test_leave_balance.py` which tests double-counting, not concurrency)
- `with_for_update` — not found in tests

**No test proves:**
- Two competing approval transactions
- Only one succeeds
- No duplicate audit/ledger records

### 3.4 Concurrency Verdict

| Requirement | Status |
|-------------|--------|
| `version_id` in code | ✅ |
| `StaleDataError` handling in code | ✅ |
| Migration for `version_id` | ❌ NOT FOUND |
| Test for concurrent approval | ❌ NOT EXISTS |
| Proof only one approval succeeds | ❌ NOT EXISTS |
| Proof no duplicate records | ❌ NOT EXISTS |

**Verdict:** ❌ CONCURRENCY NOT VERIFIED — Code exists but no test proves it works. No migration evidence.

---

## 4. Backup / Restore

### 4.1 Has an actual restore been performed?

**NO.**

Evidence:
- `verify_backup_live.sh` is a **script** that WOULD perform a restore if run. It has not been run.
- `tests/test_backup_restore.py` uses **mocks** (`@patch('verify_backup.count_rows')`, `mock_run`). No real PostgreSQL is touched.
- `verify_backup.py` has `--full-cycle` flag but no evidence it was executed against a real database.
- No JSON report file exists in `reports/` directory.
- No Render log showing backup/restore activity.

### 4.2 RPO/RTO Claims

The report claims "RPO < 5m, RTO < 15m." These numbers are:

- ❌ NOT MEASURED
- ❌ NOT TESTED
- Based on Render's marketing materials for PITR, not actual verification

### 4.3 Backup Verdict

**Classification: BACKUP AVAILABLE — RESTORE UNVERIFIED**

Render likely takes automatic daily snapshots. Continuous PITR requires Standard+ plan (unverified). No restore has been attempted or documented.

---

## 5. Legal / Compliance Verification Levels

### Level 1: Source-Document Verification
Rules checked against actual proclamation text by a human.

| Rule | Proclamation | Verified? |
|------|--------------|-----------|
| Tax brackets (6) | 1395/2025, Art. 11 | ⚠️ Cited, cross-checked against ERCA filing, NO human verification of proclamation text |
| Pension employee 7% | 1268/2022, Art. 10 | ⚠️ Cited, NO human verification |
| Pension employer 11% | 1268/2022, Art. 10 | ⚠️ Cited, NO human verification |
| Pension ceiling (none) | 1268/2022 | ⚠️ Cited, NO human verification |
| Overtime rates (4) | 1156/2019, Art. 68 | ⚠️ Cited, NO human verification |
| Overtime limits (2) | 1156/2019, Art. 89 | ⚠️ Cited, NO human verification |
| Leave entitlements (8) | 1156/2019, various | ⚠️ Cited, NO human verification |
| Severance (2) | 1156/2019, Art. 40-42 | ⚠️ Cited, NO human verification |
| Cash limit | 1395/2025, Art. 81 | ⚠️ Cited, NO human verification |
| Compliance deadlines (3) | NO CITATION | ❌ |
| Court order cap | NO CITATION | ❌ |

**Source-document verification: 0 of 34 rules confirmed by human reading proclamation text.**

### Level 2: Automated Test Verification
Rules with test coverage that validates calculation output.

| Rule | Test File | Status |
|------|-----------|--------|
| Tax brackets | `test_tax*.py` | ✅ Tests exist |
| Pension rates | `test_pension*.py` | ✅ Tests exist |
| Overtime rates | `test_overtime*.py` | ✅ Tests exist |
| Leave entitlements | `test_leave*.py` | ✅ Tests exist |
| Severance | `test_severance*.py` | ✅ Tests exist |
| Cash limit | `test_validation*.py` | ✅ Tests exist |

**Automated test verification: ~30 of 34 rules have test coverage.**

### Level 3: Accountant Verification
Rules confirmed correct by a licensed Ethiopian accountant.

**Accountant verification: 0 of 34 rules.** `VERIFICATION_PACKAGE.md` has not been sent.

### Level 4: Auditor Verification
Rules confirmed by independent audit.

**Auditor verification: 0 of 34 rules.**

### Level 5: ERCA Filing Verification
Rules validated against an actual accepted ERCA filing.

| What | Status |
|------|--------|
| Tax brackets | ✅ Cross-checked against Sene 2018 filing (146 employees) — tax matched |
| ERCA column format | ✅ Filing accepted by portal |
| Other rules | ❌ Not cross-checked against filing |

**ERCA filing verification: 2 of 34 rules.**

---

## 6. Final Pilot Gate

### Blockers

| # | Issue | Severity | Resolution Required |
|---|-------|----------|---------------------|
| 1 | No migration for `version_id` | HIGH | Create and run migration, or confirm column exists in production DB |
| 2 | No concurrency test | HIGH | Write test proving only one approval succeeds in concurrent scenario |
| 3 | No restore has been performed | MEDIUM | Run `verify_backup_live.sh` against test database, or explicitly document limitation |
| 4 | RPO/RTO claims unverified | MEDIUM | Remove numeric claims or measure them |
| 5 | Accountant review not sent | BLOCKING (external) | Send `VERIFICATION_PACKAGE.md` |

### Decision

**PILOT BLOCKED**

Reason: Items 1-2 are code-level gaps that could cause data corruption in a real concurrent scenario. Item 3 means we cannot guarantee recoverability. Items 4-5 are documentation/compliance gaps.

### Conditions for PILOT GO

The pilot may proceed ONLY when ALL of the following are true:

1. **Engineer confirms** `version_id` column exists in production Render PostgreSQL (manual check via Render dashboard or `psql` connection)
2. **OR** a migration is created, committed, and run on production
3. **Concurrency test** is written and passes — proves two competing approvals result in exactly one success and zero duplicates
4. **Backup limitation** is explicitly documented: "No restore has been performed. Render automatic backups are available. Recovery time is estimated, not measured."
5. **RPO/RTO claims** are removed or qualified: "Render provides automatic backups. PITR available on Standard+ plans. Actual recovery time has not been measured."
6. **Accountant review** is sent (external dependency — does not block code work)
7. **First payroll** is manually verified by engineer before and after approval
8. **No legal certification claim** — the system is a tool, not a certified payroll system. Users are responsible for compliance.

---

## Summary

| Category | Status |
|----------|--------|
| Git ancestry | ✅ VERIFIED |
| 404 fix | ⚠️ CODE VERIFIED, PRODUCTION UNVERIFIED |
| Login lockout fix | ⚠️ CODE + TEST VERIFIED, PRODUCTION UNVERIFIED |
| MFA flash fix | ⚠️ CODE VERIFIED, PRODUCTION UNVERIFIED |
| Concurrency fix | ❌ CODE EXISTS, NO TEST, NO MIGRATION, NO PROOF |
| Pytest fix | ✅ VERIFIED |
| Backup/restore | ❌ BACKUP AVAILABLE, RESTORE UNVERIFIED |
| Statutory rules | ⚠️ 30/34 HAVE TESTS, 0/34 HUMAN VERIFIED, 2/34 ERCA VERIFIED |
| Accountant review | ❌ NOT SENT |

---

*Evidence check completed: 2026-08-21 19:38 GMT+8*
*No code, configuration, database, or documentation was changed during this check.*
