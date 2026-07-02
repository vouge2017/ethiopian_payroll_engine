# Status Reconciliation — Ethiopian Payroll Engine

**Date:** 2026-07-02
**Purpose:** Reconcile earlier "DONE" claims against what actually exists in the repo. Identify what went wrong in reporting so it doesn't happen again.

---

## The Short Version

Three items were reported as done or close-to-done that are not. The cause in all three cases is the same: **an earlier session reported the existence of code as evidence of completion, without verifying that the code actually enforces what it claims to enforce.**

There was no deception — there was a failure to distinguish between "code exists" and "code works as intended."

---

## Item 1: Backup Automation

### What Was Claimed
Backup automation was implied as working (restore was tested at 0.037s).

### What Actually Exists
**Nothing.** There is zero backup code in the repository:

- No backup scripts
- No cron jobs
- No celery beat schedule
- No backup service in `docker-compose.yml`
- No backup configuration anywhere

The `docker-compose.yml` has a `postgres_data` volume (so data persists across container restarts), but no mechanism to copy that data anywhere external.

### Why It Was Reported Wrong
The earlier session likely tested a **database restore** (reading from an existing dump file into a running Postgres instance) and reported the speed. That test is real — restoring from a dump into Postgres is fast. But the session never built the **other half**: the scheduled job that creates the dump in the first place.

The feedback's question — *"Where does this run in production?"* — was exactly right. There's no answer because there's no backup job to run.

### Status: **Not started. Zero code exists.**

---

## Item 2: Tenant Isolation (Structural Enforcement)

### What Was Claimed
Tests passed, isolation was working.

### What Actually Exists
A `company_scoped()` helper function in `main.py` (line 42-44):

```python
def company_scoped(query):
    return query.filter_by(company_id=current_user.company_id)
```

**This function is never called anywhere in the codebase.** Every single route manually writes `.filter_by(company_id=current_user.company_id)` by hand. There are ~20 such manual calls across `main.py` and `api.py`.

There is no:
- Base query class
- Repository pattern
- Session-level tenant scoping
- Model mixin that enforces filtering
- Any mechanism that makes an unfiltered query impossible

### Why It Was Reported Wrong
The earlier session likely ran tests that verified the **manual `.filter_by()` calls return correct results** — i.e., "when I filter by company_id, I only see my company's data." That's true. The tests pass because the filtering code is written correctly in each route.

But that's not what ADR-02 asked for. ADR-02 asked for **structural enforcement** — a system where you *cannot write* an unfiltered query on a tenant-scoped table. The session tested the happy path ("does filtering work?") without testing the failure path ("can someone accidentally skip filtering?").

The feedback's test 3 — *"Unfiltered query (danger case) ⚠️ WARN"* — is the key. The session found that an unfiltered query is possible, noted the warning, and then moved on. That warning should have been the trigger to build structural enforcement, not a footnote.

### Status: **Discipline-based only. No structural enforcement. The vulnerability ADR-02 was written to address still exists.**

---

## Item 3: employee_id Uniqueness Constraint

### What Was Claimed
Noted as a bug in prose, but not tracked or fixed.

### What Actually Exists
In `models.py` line 46:

```python
employee_id = db.Column(db.String(20), unique=True, nullable=False)
```

This is a **global unique constraint**. If Company A creates `EMP001`, no other company can use `EMP001`. This is wrong — employee IDs should be unique *within* a company, not across all companies.

The correct constraint would be a composite unique index on `(company_id, employee_id)`, which requires a `__table_args__` definition on the model and a database migration.

There is also **no migrations directory** — Alembic is not set up, so there's no migration to attach the fix to.

### Why It Was Reported Wrong
This one is straightforward. The session found the bug, mentioned it in conversation, and never turned it into a tracked item. It was a "note and move on" rather than "note, create ticket, fix, verify." The feedback correctly identified this as a process failure — findings mid-work need to go into the backlog, not just chat.

### Status: **Bug confirmed. Not fixed. Not tracked. No migration infrastructure exists.**

---

## Root Cause Analysis

All three failures share a pattern:

| What happened | What should have happened |
|---|---|
| Code was written | Code was written |
| Tests were run on the happy path | Tests were run on both happy and failure paths |
| "It works when I use it correctly" was reported as DONE | "It fails when someone uses it incorrectly, and that failure is prevented by the system" was required for DONE |

The earlier session was doing **feature verification** (does the code do what I built it to do?) when it should have been doing **acceptance testing** (does the code meet the acceptance criteria in the plan/ADR?).

Specifically:
1. **Backup:** Tested restore (one half), never built the scheduled backup (other half). Reported the test result without checking if the system under test was complete.
2. **Tenant isolation:** Tested that manual filtering works, didn't test that unfiltered queries are prevented. Reported tests passing without checking if the *right* tests existed.
3. **employee_id:** Found the bug, mentioned it verbally, didn't create a tracked work item. Assumed "noted" = "will be done."

---

## What Needs to Happen Now

Before anything else, these three items need real closure:

1. **Backup:** Build a scheduled backup mechanism (cron job, celery beat task, or platform-level scheduled job). Show the config where it runs in the target deployment environment, not a container workaround.

2. **Tenant isolation:** Build a base query class or model mixin where `Employee.query.all()` on a tenant-scoped table either:
   - Automatically scopes to the current tenant, or
   - Raises an error at query construction time, or
   - Is impossible to write (enforced by the ORM layer)
   
   Then re-run test 3 and show it fails to execute an unfiltered query.

3. **employee_id:** Change the constraint from global `unique=True` to a composite `UniqueConstraint('company_id', 'employee_id')`. Set up Alembic migrations. Write a test proving two tenants can each have `EMP001`.

---

## Reporting Rules Going Forward

To prevent this from happening again:

1. **"DONE" means the acceptance criteria are met, not that code exists.** Check the ADR/plan for specific criteria before marking done.
2. **Test the failure path, not just the happy path.** For security/isolation features, the failure path *is* the acceptance test.
3. **Findings during work get tickets, not just notes.** If a bug is found mid-task, it goes into the backlog with acceptance criteria before moving on.
4. **"Where does this run?" is a required question for infrastructure items.** Code that runs in a dev container doesn't count until it's configured in the actual deployment target.
