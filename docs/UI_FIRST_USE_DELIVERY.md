# First employee to payroll preparation — 2026-10-08

Local and uncommitted in `D:\ethiopian_payroll_engine\payroll-pr8-integration`,
branch `codex/monthly-payroll-ui`, HEAD
`2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`. No upstream is configured.
Outer mobile work and earlier dirty changes remain intact.

## Delivered outcome

The welcome/onboarding visual direction now continues into the initial dashboard.
An empty workspace explains one immediate action: add the first employee. After
employees are added, that action becomes preparation of the first payroll. A
three-step progress panel explains company setup, employees and preparation.
New workspaces no longer show an unevidenced compliance score, empty charts or
report links that point nowhere. Existing workspaces with payroll history keep
their dashboard content. Company identity and the shared dual-calendar header
remain visible.

After saving the first employee, the unfiltered active employee list offers a
direct preparation action, alongside a secondary Add employee action. The copy
explains that preparation does not send payments. This avoids a return to the
dashboard just to discover the next step.

The visual choices adapt the supplied Stitch reference: warm paper, restrained
serif headings, comfortable spacing and a clear dominant action. The progress
panel stacks on phones; controls retain native links and visible keyboard focus.
No reference testimonials, payout integrations or calculator claims are copied.

This slice owns `first-use.css`, `first_use_styles.html`, `first_workspace.html`,
the initial-dashboard branch, the one-employee continuation panel in
`employees.html`, scoped contrast fixes in `workspace.css`, and
`test_pg_first_employee.py`. It preserves and verifies concurrent local employee
form, route, list and shared-workspace changes. Those changes are not attributed
to this slice. Payroll arithmetic, approval and payment behavior were not edited
by this slice.

## Verification

Evidence: `local-evidence/first-use-20261008/` (local, ignored, synthetic data).

- Final focused PostgreSQL run: `11 passed, 19 warnings in 21.34s` in
  `tests-access-verified.log`. It combines four new first-employee cases with seven
  employee-workspace regressions. The fixtures create unique disposable databases
  and run Alembic to head. Coverage includes retained entries after rejected
  phone/FIN/duplicate-ID submissions, exact saved Decimal salary/allowances,
  role rejection, company scoping, edit recovery, legacy full names, filtered
  pagination, owner-only deactivation visibility and archived employee IDs.
- `browser-report.json` and `browser-access-verified.log`: 22 layouts, nine real
  interaction checks, no detected document overflow, checked axe A/AA violations
  or JavaScript page errors. Widths 320, 390, 768 and 1440; selected dark-mode and
  200% text layouts. Chrome performs real CSRF-enabled signup/company setup,
  native required-field/FIN rejection, an actual server validation error, a
  corrected save, and both working preparation links with the employee present.
- Screenshot inspection confirms desktop hierarchy and phone stacking. The
  mobile preparation action appears before the longer progress explanation.
- Ruff check/format for the new test, Stylelint for first-use/shared-workspace
  CSS and source whitespace checks pass. Existing warnings are deprecations,
  not silently discarded.

Earlier receipts are retained: `3 failed, 1 passed, 5 warnings in 11.40s` exposed
validation recovery before the concurrent form repair; `4 passed, 5 warnings in
11.66s` verified those cases afterwards. `1 failed, 9 passed, 18 warnings in
25.57s` preceded the legacy-name test alignment and an additional archived-ID
regression. The final run above supersedes that selection. A resumed sandbox run
had `4 warnings, 11 errors in 23.94s` and Chrome localhost access denial; the
approved local-access reruns above completed. These are not product failures or
successful test receipts. Earlier dark-mode contrast failures and their final
successful rerun are also preserved.

`first-use-slice.diff` isolates this slice using explicitly reconstructed
baselines that retain concurrent changes. `tracked-current.diff` is the verbatim
Git diff for the touched tracked files against HEAD; it includes earlier work.
Neither is a staged change or a commit. Source-before snapshots retain observed
starting files; they must not be treated as ownership of every subsequent edit.

## Limits and next action

This is local implementation and focused verification. No hosted CI, commit,
merge, deployment, physical-device test, screen-reader audit or practitioner
acceptance is claimed. Automated axe checks do not establish full WCAG
compliance. The new first-use narrative remains English; critical Amharic/Oromo
copy, invitations and uncertain-network/session recovery remain open.

Temporary synthetic loopback preview: `http://127.0.0.1:62811/welcome`. It requires
normal registration/company setup to reach this dashboard, is not phone-accessible
from another device, and is not a stable hosted tester environment.

Next: observe one uncoached owner/preparer from welcome through first employee
and payroll review on a real phone; record hesitation and wrong turns, then make
the smallest evidenced language or recovery improvement. Do not replace this
with another whole-system visual rewrite or a new acceptance score.
