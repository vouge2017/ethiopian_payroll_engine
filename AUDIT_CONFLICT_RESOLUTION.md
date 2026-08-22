# AUDIT CONFLICT RESOLUTION — EthioPayroll

**Date:** 2026-08-21
**Method:** Direct inspection of repository files. No code changes.
**Scope:** Reconcile claims against actual evidence.

---

## 1. Does `tests/test_concurrency.py` actually exist?

**CLAIM:** Concurrency test exists and proves only one approval succeeds.
**COUNTERCLAIM:** No such test file exists.

**ACTUAL EVIDENCE:**
```
$ ls tests/test_concurrency.py
ls: cannot access 'tests/test_concurrency.py': No such file or directory
```

```
$ grep -rn "threading\|Thread\|concurrent\|StaleDataError\|version_id" tests/
tests/test_notifications_webhooks.py:399:    @patch('payroll_engine.webhooks.threading.Thread')
(nothing related to concurrency or version_id)
```

**FINAL STATUS:** ❌ DOES NOT EXIST. No test for concurrent approval, `version_id`, or `StaleDataError` in any test file.

---

## 2. Does a production database migration for `version_id` exist?

**CLAIM:** `version_id` column added to PayrollRun model and deployed.
**COUNTERCLAIM:** No migration file exists.

**ACTUAL EVIDENCE:**
```
$ grep -rn "version_id" migrations/versions/
(no output)
```

86 migration files exist in `migrations/versions/`. None reference `version_id`.

The model code has:
```python
# models.py:834
version_id = db.Column(db.Integer, nullable=False, default=1)
# models.py:837
__mapper_args__ = {'version_id_col': version_id}
```

**FINAL STATUS:** ❌ NO MIGRATION EXISTS. The column is defined in code but no Alembic migration adds it to the database. If the production DB was created from scratch (not migrated), the column may exist. If it was migrated from an earlier schema, the column is missing.

---

## 3. Does `version_id` actually exist in the live PostgreSQL database?

**CLAIM:** Production database has `version_id` column.
**COUNTERCLAIM:** Cannot verify — no Render database access from this environment.

**ACTUAL EVIDENCE:**
- No migration file for `version_id`
- No Render CLI or database connection available
- No screenshot, query result, or Render dashboard evidence provided
- The app is reportedly running (no crash reports), which suggests the column may exist via `db.create_all()` or manual addition

**FINAL STATUS:** ⚠️ UNVERIFIABLE. Cannot confirm or deny. Requires direct database query:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'payroll_run' AND column_name = 'version_id';
```

---

## 4. Does the concurrency test actually execute two competing approval transactions?

**CLAIM:** Test proves concurrent approval safety.
**COUNTERCLAIM:** No such test exists.

**ACTUAL EVIDENCE:**
```
$ find tests/ -name "*concurr*" -o -name "*stale*" -o -name "*double_approv*" -o -name "*race*"
(no output)
```

```
$ grep -rn "threading\|Thread\|concurrent\|StaleDataError\|version_id" tests/
tests/test_notifications_webhooks.py:399:    @patch('payroll_engine.webhooks.threading.Thread')
(nothing related to approval concurrency)
```

**FINAL STATUS:** ❌ NO TEST EXISTS. Zero tests execute two competing approval transactions. Zero tests prove only one succeeds. Zero tests prove no duplicate records.

---

## 5. Does the full test suite actually complete without hanging?

**CLAIM:** Test suite passes cleanly after pytest deadlock fix.
**COUNTERCLAIM:** Cannot verify — pytest not installed in this environment.

**ACTUAL EVIDENCE:**
```
$ python3 -m pytest tests/ -q --tb=no
/usr/bin/python3: No module named pytest
```

`verify_status.py` output:
```
🧪 TESTS: ✅ ALL PASS
   Collected: 0
   Passed:    0
   Failed:    0
   Errors:    0
```

This shows "Collected: 0" — pytest is not installed, so `verify_status.py` reports 0 tests collected (not 0 failures). The "ALL PASS" label is misleading when 0 tests ran.

86 test files exist (22,246 lines). The code is present. But we cannot confirm they run without hanging.

**FINAL STATUS:** ⚠️ UNVERIFIABLE. Test files exist. Pytest not available in this environment. Cannot confirm the deadlock fix works. Requires running `python3 -m pytest tests/ -q` in an environment with dependencies installed.

---

## 6. Was a real backup restore ever performed?

**CLAIM:** Backup/restore tested, 38 unit tests, live integration script ready.
**COUNTERCLAIM:** No restore has been performed.

**ACTUAL EVIDENCE:**
```
$ ls reports/
ls: cannot access 'reports/': No such file or directory
```

- `verify_backup_live.sh` exists — it is a SCRIPT, not evidence of execution
- `tests/test_backup_restore.py` exists — uses MOCKS (`@patch`, `mock_run`), not real PostgreSQL
- `verify_backup.py` exists — has `--full-cycle` flag, no evidence it was run
- No `reports/` directory exists (the script would create JSON reports here)
- No JSON report files found anywhere in the repo
- No Render log evidence of backup/restore activity

**FINAL STATUS:** ❌ NO RESTORE HAS BEEN PERFORMED. The tools exist. They have not been used against a real database.

---

## 7. Were RPO/RTO actually measured?

**CLAIM:** "RPO < 5m, RTO < 15m" (from hardening report).
**COUNTERCLAIM:** These numbers are unverified.

**ACTUAL EVIDENCE:**

`DISASTER_RECOVERY.md` contains:
```
| Scenario | RTO | RPO | Action |
| Server crash | ~2 min | 0 (auto-restart) | Render auto-restarts web service |
| Database corruption | ~30 min | Last backup | Restore from Render backup |
```

These are ESTIMATES in a documentation table, not measurements. No timing data, no test logs, no benchmark results exist.

The PITR section (added in this session) says:
```
Render's managed PostgreSQL supports continuous PITR
```

This describes Render's capability. It does not claim we measured or tested it.

**FINAL STATUS:** ❌ NOT MEASURED. RPO/RTO numbers are documentation estimates based on Render's published capabilities. No actual measurement has been performed. The claim "RPO < 5m, RTO < 15m" in the hardening report is not supported by evidence.

---

## 8. Which of the 34 statutory rules have actual human/source-document verification?

**CLAIM:** 34 rules verified against actual law.
**COUNTERCLAIM:** No human verification recorded.

**ACTUAL EVIDENCE:**

Proclamation reference files exist:
```
reference_data/proclamation_1156_2019/  (Labor Proclamation)
reference_data/proclamation_1268_2022/  (Pension Proclamation)
reference_data/proclamation_1395_2017/  (Tax Proclamation — note: filename says 2017, but code references 2025)
reference_data/proclamation_979_2016/   (Income Tax Proclamation)
```

Each contains:
- `full_text.txt` — proclamation text
- `01_*.md` — extracted summaries

`DIAGNOSTIC_ANSWERS.md` states:
```
| Tax brackets | ❌ PDF link exists but no human verification recorded |
| Pension employee 7% | ⚠️ Proclamation 1268/2022 cited but no human verification |
| Pension employer 11% | ⚠️ Same |
```

Line 790:
```
3. **No accountant verification** — No Ethiopian accountant has reviewed the tax calculations or filing formats.
```

Line 900:
```
2. **Legal risk** — Tax brackets and pension rates are from secondary sources.
```

**FINAL STATUS:** ⚠️ PROCLAMATION TEXTS EXIST, BUT NO HUMAN VERIFICATION IS RECORDED. The proclamation files are reference material. No named person has signed off verifying that the code's values match the proclamation text. The system's own documentation acknowledges this gap.

---

## 9. Which rules have actual ERCA filing evidence?

**CLAIM:** Verified against real ERCA filing for 146 employees.
**COUNTERCLAIM:** Filing exists but scope is limited.

**ACTUAL EVIDENCE:**

Real ERCA filing exists:
```
reference_data/real_erca_filing_sene.csv
```

Contents:
```
Employee Full Name, Start Date, End Date, Basic Salary, Transport Allowance,
Taxable Transport Allowance, Over Time, Other Taxable Benefit, Total Taxable, Tax withheld
```

146 rows of real employee data with actual tax calculations.

`VERIFICATION_PACKAGE.md` states:
```
**Verified against:** A real ERCA filing for Sene 2018 (June 2026) with 146 employees
— every employee's tax matched exactly.
```

**What the ERCA filing verifies:**
- ✅ Tax bracket calculations (tax withheld matches for 146 employees)
- ✅ ERCA column format (filing was accepted by portal)
- ✅ Total taxable calculation methodology

**What the ERCA filing does NOT verify:**
- ❌ Pension rates (pension not in ERCA filing columns)
- ❌ Overtime rates (overtime is a column, but rates not verified)
- ❌ Leave entitlements (not in ERCA filing)
- ❌ Severance (not in ERCA filing)
- ❌ Compliance deadlines (not in ERCA filing)
- ❌ Cash limit (not in ERCA filing)

**FINAL STATUS:** ✅ PARTIALLY VERIFIED. The real ERCA filing verifies tax bracket calculations and column format for 146 employees. It does NOT verify pension, overtime, leave, severance, deadlines, or cash limit.

---

## Summary Table

| # | Claim | Actual Status |
|---|-------|---------------|
| 1 | test_concurrency.py exists | ❌ DOES NOT EXIST |
| 2 | version_id migration exists | ❌ NO MIGRATION |
| 3 | version_id in production DB | ⚠️ UNVERIFIABLE |
| 4 | Concurrency test proves safety | ❌ NO TEST EXISTS |
| 5 | Test suite passes without hanging | ⚠️ UNVERIFIABLE (pytest not installed) |
| 6 | Backup restore performed | ❌ NEVER PERFORMED |
| 7 | RPO/RTO measured | ❌ NOT MEASURED |
| 8 | 34 rules human-verified | ❌ 0 OF 34 HUMAN-VERIFIED |
| 9 | ERCA filing evidence | ✅ TAX BRACKETS + FORMAT ONLY (2 of 34 rules) |

---

*Audit completed: 2026-08-21 19:52 GMT+8*
*No code, configuration, database, or documentation was changed.*
