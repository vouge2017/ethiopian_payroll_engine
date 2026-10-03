# Focused delivery work orders

## CURRENT AUTHORITATIVE STATE - 2026-10-03

Accepted baseline: remote main `9670a92487c705a6614e3c6df67aff24d29c7bcf`
contains merged PR #8 and #10. Schema: 77 revisions, one head `f4a5b6c7d8f3`.
Local PostgreSQL receipts remain slice-specific. Exact-main hosted PostgreSQL,
standalone migrations and lint/format pass; full Python 3.11 has
`TOTAL: 1550 passed, 11 failed, 0 errors, 116 skipped`, Python 3.12 cancelled.
GitGuardian passed on PR #10 head `90779cb`; merge SHA has no separate scan.
Deployment/restore and founder/Tigist verification are open.

12. Prepare the ordinary monthly payroll journey using existing comparison and checks, then STOP.

First repair the two stale CI test contracts. Close the individual PDF control,
unsupported worksheet Undo and completed-review label. Connect previous approved
facts to saved-review changes and exceptions; exercise desktop/phone using
synthetic data. Reuse existing services, keep statutory policy unchanged, expose
threshold decisions, and report founder/Tigist trial scripts. No further
correction categories, AI, bank execution, statutory submission, HRMS expansion
or production deployment. The latest user instruction authorizes this bounded
slice and supersedes the earlier reconciliation-only stop below.

See STATUS.md for source/CI/deployment distinctions. Historical orders and
receipts below are retained; stale pending instructions do not override this
current section.

### Order 12 local acceptance - 2026-10-03

Delivered on `feature/monthly-payroll-journey`: three results/review control fixes,
existing frozen previous-period comparison, exceptions and saved checks.
`136 passed, 104 warnings in 80.49s (0:01:20)` affected cases;
`57 passed, 20 warnings in 20.60s` final recheck (overlap). Ruff passes.
Desktop/390px accountant-to-owner approval, PDF and bank download were exercised
with synthetic data; outputs agree and payment stays Pending.
Review branch hosted checks, merge, practitioner acceptance and deployment remain
separate. [Report and trial scripts](MONTHLY_PAYROLL_JOURNEY_2026-10-03.md).
**STOP:** no further work order begins automatically.

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
| 2 | Connect the saved worksheet to a payroll review with matching amounts. | Core verified locally: PG review/approval/output/retry evidence and browser approval; closing results download control, unsupported Undo button and completed-state label before founder sign-off; not deployed |
| 3 | Observe Tigist preparing and checking one synthetic monthly payroll. | Founder first: local browser trial prepared; desktop/phone review inspected; founder feedback and Tigist observation still pending |
| 4 | Keep committed payroll correct when PDF or queue delivery fails. | Worksheet and legacy money now survive queue failure; legacy service, durable commit, audit, one loan recovery and safe retry verified on PG; 20 PDF/delivery/journey checks pass. Durable handoff and full legacy user trial remain open |
| 5 | Close release blockers and deploy an identified demo build. | Local Ruff and 201-file formatting gates now pass; 95 affected and 63 native PG checks pass (focused selections). Pending: published-commit CI, GitGuardian, main reconciliation, schema readiness, shared worker key, durable artifacts and restore drill; record exact deployed SHA |
| 6 | Reconcile accounting exports to approved payroll and reject unsafe files. | Locally verified: 55 unit/export, 19 PG accounting/worksheet and 57 accounting/role/security cases pass (overlap); removed foreign membership denied; trial account mapping only, not deployed |
| 7 | Make the register and statutory reports consume approved historical facts. | Register locally verified: 23 PG register/accounting/worksheet cases pass; approved/locked saved amounts and retained worksheet identity, including removed employees; browser review and statutory identity/classification remain open |
| 8 | Fix reproduced calculation/input defects and protect legacy approval failures. | Settlement dates, deduction context and overtime locally verified: 69 engine/service/deduction and 25 calculation/PG journey cases pass (overlap); legacy queue failure closed under order 4. Invalid money/partial import closed: 40 parser/workflow/Diff/native PG valid-invalid CSV/Excel checks pass. Exemption caps and joining/exit policy remain open |
| 9 | Close company-access gaps and connect previous-period review checks. | Diff authorization locally verified: 25 access/role/isolation and 8 mocked comparison/XLSX checks pass; private results require matching user and active company; removed membership denied. Previous-period worksheet checks remain open |

Save updates the estimate; Review saved payroll freezes it for owner approval. Approval does not send money.
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

## 2026-10-03 checkpoint — PR #8 and restored main

Code conflicts and combined migrations are reconciled. Final native PostgreSQL
selection: `93 passed, 262 warnings in 186.20s (0:03:06)`; security/tenant gate:
`173 passed, 1 skipped, 41 warnings in 205.76s (0:03:25)`. Ruff passes.
See [reconciliation evidence](PR8_RECONCILIATION_2026-10-03.md) for full scope and
the initial broad-suite failures followed by successful targeted rechecks.

Reconciliation is published to PR #8. All hosted Python 3.11/3.12, PostgreSQL,
standalone migration and lint checks passed at `c121558`. The owner supplied
Ignored / Test credential status for GitGuardian incident 37741140 on 2026-10-03.
Next gate: verify the fresh scan triggered by this status checkpoint; direct
GitHub rerequest returned HTTP 404. Recovery PR #9 is already merged. PR #8
merging and deployment are separate remaining actions.

## 2026-10-03 checkpoint — approved-payroll corrections

10. Save and approve evidenced taxable overtime/bonus corrections while preserving approved originals.

Verified locally on `feature/approved-payroll-corrections`, based on merged main
`9a46f28`: `118 passed, 132 warnings in 142.72s (0:02:22)` for affected workflows;
`39 passed, 5 warnings in 97.16s (0:01:37)` for the final correction selection.
Ruff passes. Actual PostgreSQL migrations, concurrent approvals, retry/conflict
behavior, active membership, audit rollback, frozen PDF/bank output and a
CSRF-enabled desktop/phone journey are covered. See
[evidence and limits](PAYROLL_CORRECTIONS_2026-10-03.md), including the intermediate
test-fixture failure and successful focused recheck. Selections overlap.

Older records without complete calculation context require historical review;
salary/pension/deduction/net-only corrections remain outside this slice.
PR #8 reconciliation and GitGuardian are complete. This new branch still needs
hosted checks and review; production deployment is separate.

11. Finish the three existing results/review UI defects and run the synthetic practitioner journey.
## Current Priority Override - 2026-10-03

Reconcile recovery `c2b636f` with hardening `e1d5e37`, report verified evidence,
then **STOP**. This latest user instruction overrides the reusable continuation
instruction and any next-order suggestion below.

Delivered in merged PR #8 at `9a46f2880188c7bb473bd3ac1c42fd89053bf839`.
Both source inputs remain in its ancestry; hosted Python 3.11/3.12,
PostgreSQL, standalone migrations and lint all passed at that SHA.
See [acceptance receipts and exact checks](PR8_RECONCILIATION_2026-10-03.md#priority-override-review-and-stop-checkpoint---2026-10-03).

Current main `9670a92` also includes subsequently merged correction PR #10;
this review does not undo that merge or authorize further correction work.
No later work order may begin until the reconciliation result is reviewed.
