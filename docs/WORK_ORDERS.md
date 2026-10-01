# Focused delivery work orders

We own the technical investigation and implementation. The product owner supplies
the user problem, policy decisions and user feedback; expert prompting is not a
prerequisite. STATUS.md remains the evidence record. Update this board when work
is verified, not when a plan or test collection exists.

## Current target

An accountant can prepare one month, explain changes and deductions, approve
once, and obtain outputs that agree. Demonstrate this with synthetic data before
calling a real-money pilot ready. No completion percentage is justified today.

| Order | Work order | State / acceptance |
|---|---|---|
| 1 | Save and apply worksheet absence and bonus values without losing other edits. | Verified locally: saved monthly inputs, audited transaction, validation and recalculated estimate; 16 worksheet PG cases pass; not deployed |
| 2 | Connect the saved worksheet to a payroll review with matching amounts. | Next: snapshot the selected month and inputs; review, approval and output agree on PG; repeated approval has one effect |
| 3 | Observe Tigist preparing and checking one synthetic monthly payroll. | Pending: desktop/phone browser journey; record completion, confusing steps and her three largest obstacles |
| 4 | Keep committed payroll correct when PDF or queue delivery fails. | Pending: PG commit/failure/retry evidence and recoverable delivery |
| 5 | Close release blockers and deploy an identified demo build. | Pending: current CI/lint, route ownership, schema readiness, shared worker key, durable artifacts and restore drill; record exact deployed SHA |

The current worksheet is an estimate and does not create an approved payroll.
Absences mean additional unpaid days outside recorded approved leave; daily
worker adjustment policy is not implemented. All remaining product areas in
docs/product-checkpoint-2026-09-30.md stay open unless a specific acceptance case
is recorded. Bank/wallet and electronic filing integrations follow the core trial.

## Reusable instruction

> Continue the next unfinished work order in docs/WORK_ORDERS.md. Own the technical
> decisions and finish one user outcome at a time. First show the problem through
> the actual user path, then make the smallest correct repair. For money, prove
> tenant ownership, persistence, audit, rollback and retries on real migrated
> PostgreSQL. Exercise changed screens in a browser with synthetic data. Run
> focused checks; use the full suite when the change or release requires it.
> Keep STATUS.md and this board accurate. Commit and push each verified slice
> on feature/elements-architecture. Report what users gained, exact checks,
> commit/deployment status, limits and the next task. Ask me only for a missing
> business decision, access or spending approval; keep progressing independently.

## Checkpoints and completion

Before each slice: name the user consequence, scope and acceptance evidence in
one short update. Do not add unrelated work to repair a green check. If a bounded
check fails or stalls, report the reason and revise the slice visibly.

After each slice: report changed behavior, before/after evidence, checked SHA,
push and deployment status, remaining limits and the next work order. A local
fix is not a deployed fix; a passing component test is not a successful user
trial. Do not say production-ready while required release checks remain open.
