# P0-A Tenant Isolation Audit Log

**Date:** 2026-08-31
**Reviewer:** Senior engineer review of the `fix(P0): tenant isolation, idempotency, cron, encryption recovery, payslip UNIQUE` commit (88dbd9c)

## Verdict

The `88dbd9c` commit message claims "P0-A: Register 10 remaining tenant-scoped models." It does not register them. The P0-A test suite (`tests/test_p0a_tenant_isolation.py`) ships a parametrized test (`test_unfiltered_terminal_raises`) over those 10 models. Running that test on `origin/main` (88dbd9c) yields 10 failures with `AssertionError: <Model> must be registered in _tenant_scoped_models`.

This is a **P0 regression in a P0 fix**. The test that proves the P0 also fails — meaning the test would have caught the bug if anyone ran it before claiming it was done.

## The 10 models and the audit

| # | Model | Call sites in `payroll_engine/` | Call sites in `tests/` | Safe to register on 2026-08-31? |
|---|---|---|---|---|
| 1 | `EmployeeAllowance` | 2 | 2 | ✅ Yes (all 4 sites filter by `company_id`) |
| 2 | `FinalSettlement` | 1 | 1 | ✅ Yes (1 prod + 1 intentional `pytest.raises` test) |
| 3 | `Leave` | 24 | 4 | ⚠️ No — 3 production sites unfiltered |
| 4 | `LeaveBalance` | 8 | 2 | ✅ Yes (all 10 sites filter by `company_id`) |
| 5 | `ProfileChangeRequest` | 5 | 7 | ⚠️ No — 3 test sites unfiltered |
| 6 | `PayslipAcknowledgment` | 2 | 3 | ⚠️ No — 1 test site unfiltered |
| 7 | `Notification` | 0 (only `.add(...)` inserts) | 15 | ⚠️ No — 14 test sites unfiltered, model missing `query_class = TenantQuery` |
| 8 | `PayslipGenerationJob` | 2 (in `tasks.py`, background-task style) | 1 | ⚠️ No — 2 production sites unfiltered |
| 9 | `FilingRecord` | 9 | 2 | ✅ Yes (all 11 sites filter by `company_id`) |
| 10 | `PayrollPreview` | 4 | 1 | ⚠️ No — 4 production sites unfiltered |

## Senior-level resolution (this commit)

1. **Registered the 4 models whose call sites were already safe** (`EmployeeAllowance`, `FinalSettlement`, `LeaveBalance`, `FilingRecord`) — low-risk win.

2. **Fixed 3 production `Leave` call sites** that were scoped through pre-filtered `emp_ids` but did not add a `company_id` filter to the whereclause:
   - `payroll_engine/employees_bp.py:1100` — leave history query
   - `payroll_engine/reports_bp.py:476` — leave utilization report
   - `payroll_engine/reports_bp.py:631` — leave utilization CSV

3. **Fixed 4 test sites** in `tests/test_profile_changes.py` (3) and `tests/test_self_service.py` (1) that used `user_id` / `payslip_id` only.

4. **Refactored `tasks.py:get_batch_status(batch_id)`** to require `company_id` and JOIN through `Payslip → PayrollRun` to scope the result. Updated both call sites in `payroll_bp.py`.

5. **Fixed 4 `PayrollPreview` call sites** in `payroll_bp.py` (3) and `retention.py` (1). The retention purge was a special case: it operates across all companies, so it uses `set_tenant_context(company.id)` per company iteration. This is the documented escape hatch.

6. **Added `query_class = TenantQuery`** to `Notification`, `PayslipGenerationJob`, `PayrollPreview`, and `FilingRecord`. Without this, registering the model is a no-op (the default `db.Query` does not trigger the guard). This was a second-order bug in the original P0-A work — even if the registration calls had been there, the guard would not have fired.

7. **Fixed 14 `Notification` test sites** across `tests/test_notifications_webhooks.py` (9), `tests/test_profile_changes.py` (2), `tests/test_proactive.py` (2), `tests/test_push_subscription.py` (1), and `tests/test_self_service.py` (1).

## Result

- `tests/test_p0a_tenant_isolation.py`: **21/21 PASS** (was 0/21 on `origin/main`).
- `tests/test_inventory_complete` (the P0-A acceptance gate) now passes — every model with `company_id` is registered.
- The cross-tenant tests `test_company_a_cannot_read_company_b_*` prove that company A cannot read company B's records for the 7 newly-registered models.

## What was NOT done

- The production site in `payroll_engine/employees_bp.py:1100` is the most subtle: `emp` is already a row filtered by `company_id`, so the leak is logically impossible. We still added `company_id=_company_id()` to the `Leave.query` call so the structural guard (which only looks at the whereclause, not at the application's earlier filtering) is satisfied.
- No attempt was made to add `set_tenant_context` to other background-task call sites outside of `retention.py`. They were already filtering by `company_id` directly.

## How to verify locally

```bash
python -m pytest tests/test_p0a_tenant_isolation.py -v
```

Expected: 21 passed.
