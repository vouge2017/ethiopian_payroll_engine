# Product checkpoint - 2026-09-30

The code contains a substantial payroll product, but we have not yet proved one
complete accountant journey on the deployed release. Do not assign a completion
percentage or call it ready for real payroll. The next delivery target is an
accountant completing a synthetic monthly payroll and reconciling its outputs.

## Verified state

Reviewed feature source: `8c42ce1107ba8d5af7ee8395eae6a4e69c972007`.
GitHub CI: https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/36764061946

Python 3.11 isolated runner:
`TOTAL: 1242 passed, 0 failed, 0 errors, 26 skipped`; `TIME: 311.2s`.
Python 3.12 isolated runner:
`TOTAL: 1242 passed, 0 failed, 0 errors, 26 skipped`; `TIME: 287.9s`.
Python 3.12 coverage execution:
`1242 passed, 26 skipped, 20 warnings in 247.99s (0:04:07)`.
Both strict security selections passed. Separate PostgreSQL job:
`34 passed, 101 warnings in 8.56s`; actual migrations and rollback/upgrade passed.
The 26 native PG skips in the general suite are executed in that separate job.
Whole CI remains red: `Found 134 errors.` in lint; format check was skipped.
These results cover existing assertions, not every workflow or money invariant.

The public readiness response was database/self up. The last user-confirmed
Render release is `aa2e657`; the deployment SHA was not independently refreshed
today. Feature repairs have not been deployed by this agent.

Actual isolated Edge browser observations, public pages only:
- `/` redirects to login; login viewed at desktop and 390x844 phone sizes.
- Login is readable at those sizes; this is not an accessibility certification.
- `/diff/` returns HTTP 404, whereas feature source registers that route.
- Live login differs from the feature branch's onboarding template.
- No sign-in, account creation, upload, approval or live data changes occurred.
- Signed-in workflow and local feature UI have not been visually exercised.
- Screenshots: `D:/payroll-work-2026-09-30/output/playwright/live-login-desktop.png`
  and `live-login-mobile.png`; separate screenshots capture the Diff 404.

## Where the product stands

| Area | Implemented in source | What prevents a readiness claim |
|---|---|---|
| Payroll calculation | Tax/pension/overtime; company pay-item catalog, assignments and elements calculation | Legacy and elements paths coexist; all user entry paths have not been reconciled end to end |
| Employee/company access | Companies, employees, roles and tenant guards | Existing security cases pass; all routes/jobs/exports and company switching are not certified |
| Accountant workflow | Upload, prior-run reuse, spreadsheet, validation, review, approval and exports | Spreadsheet has the source-confirmed gaps below; no observed accountant trial |
| UI and UX | Task stepper, inline editing, issue explanations and review workspace | Public login only was visually checked; saved-state correctness and signed-in phone/keyboard flow remain open |
| Operations | Replacement database connects; fail-hard migration startup repaired on feature | Live schema, shared worker key, durable files/jobs and restore including keys are unverified |
| Payments and filing | Export and status routes | Live bank/wallet disbursement and electronic tax submission are not proven integrations |
| Regression checks | Hosted full suites and separate native PG gate pass | Global lint red; user-journey gaps can remain despite green assertions |

## Why the next task is the spreadsheet

Tigist identified preparing and checking the payroll spreadsheet as her repeated
task. This already exists, so finishing its behavior has more immediate value
than adding another dashboard, changing framework, or starting integrations.

Source findings at the reviewed SHA, not PostgreSQL or live reproductions:
1. Saved advances are rendered with `value="0"`; the GET rows omit the saved
   advance. Any editable input triggers autosave of the entire form, and the
   handler retires the active advance before recreating positive values. Thus an
   unrelated overtime edit after a reload can submit zero for a saved advance.
   Trace: `templates/payroll_spreadsheet.html`, `payroll_bp.py:1472`,
   `payroll_bp.py:1563`, `payroll_bp.py:1802`.
2. Absences and bonus are editable, with a promise that Save & Recalculate
   applies them. POST reads both but does not persist/use them; GET calculation
   does not read those submitted changes. Advance is likewise omitted from the
   displayed net calculation. These previews require reconciliation, not just
   a label change. Trace: `payroll_bp.py:1563` through spreadsheet GET calculation.
3. The spreadsheet offers save/recalculate, but no direct next action into the
   review/approval journey. Upload offers it as an Excel-like alternative.

## Ordered work, with an outcome for each slice

Effort is relative, not a delivery promise. Do not work across rows at once.

| Order | Work order | User value / reason | Acceptance evidence |
|---|---|---|---|
| 1 | Preserve saved advances across spreadsheet reloads and unrelated edits. | Small scope; directly prevents losing a payroll deduction | Real migrated PG: save, reload, unrelated OT edit, retry, independent persisted read, audit and foreign-tenant checks; local browser reproduces the journey |
| 2 | Make supported monthly edits produce matching preview and approved amounts. | Medium/larger scope; removes rechecking and misleading totals | Explicit period; valid edit survives reload; invalid edit identifies row; preview/persisted payslip/export reconcile; each money rule gets a separate PG slice |
| 3 | Complete one guided prepare-review-approve-download path using synthetic data. | Medium scope; turns existing screens into a usable product | Signed-in desktop/phone browser, clear next action, deliberate approval, repeated-click protection, matching downloads; observe Tigist and record her top three obstacles |
| 4 | Preserve committed payroll when PDF/job delivery fails. | Medium scope; protects trust when a worker or queue is unavailable | PG failure/retry after commit retains completed money records and their audit; delivery can recover without a second money effect |
| 5 | Prepare a controlled demo release and close gates before real customer data. | Several bounded tasks; makes tested code reachable and recoverable | Exact deployed SHA; real migration state/readiness; tenant route review including public Diff; matching worker key; durable artifacts; restore drill; lint findings triaged and repaired |

Payment integrations, multi-country work and a broad UI rewrite follow a
successful core trial. No paid infrastructure or external submission is implied.

For every repair report: problem, changed behavior, before/after evidence,
commit/deployment status and remaining limit. Use focused checks per slice;
run the whole suite for a release candidate or when a change warrants it.
