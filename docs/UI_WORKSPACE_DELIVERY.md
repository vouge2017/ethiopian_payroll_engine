# Monthly workspace delivery — 2026-10-08

Implemented locally on `codex/monthly-payroll-ui`, baseline/HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`; uncommitted. This delivery follows the stricter market-fit review and preserves the checkout's earlier dirty work.

## What users gain

| Previous gap | Delivered behavior |
|---|---|
| Core monthly pages displayed only Gregorian context | Preparation, saved review and approval show the actual monthly start/end dates in both calendars; the shared authenticated shell shows today's dual date separately |
| Desktop collapse existed only as unused styling | Keyboard-operable Collapse/Expand control, retained accessible link names and correct content offset; existing phone menu retained |
| Phone names squeezed beside salary metadata; Edit label hidden | Name and employee reference receive the full row; explicit Edit inputs action, with salary metadata inside the editor |
| Comparison context buried away from the decision | Actual prior-approved gross/net deltas beside totals, changed-person count before the ledger, and individual explanations beside the person's pay |
| Advisory missing-phone warning dominated review | Native expandable finding with the employee, consequence and specific Add phone number action; blocking/high findings remain expanded |
| Employee reference used in an integer-PK route, producing 404 | Company-resolved employee primary key used for issue links; alphanumeric and numeric-looking references covered |
| Useful Stitch lessons scattered across discussion | [UI_DESIGN_STANDARD.md](UI_DESIGN_STANDARD.md) records shared decisions and the next page order |

The visual direction retains warm surfaces, distinct headings, readable tabular amounts, blue actions and dark net-pay emphasis. Findings, retained saved figures and approval/payment wording remain grounded in actual state. Payroll arithmetic, authorization rules, approval forms and historical facts were not changed by this slice. New roles, payment verification and billing behavior were not invented.

## Evidence

Receipts: `local-evidence/workspace-20261007/`; reviewable source changes against the task-start copies: `D:/ethiopian_payroll_engine/output/payroll-workspace-2026-10-08/changes.patch`.

- Initial navigation regression reproduced before repair (`red.log`): `2 failed, 3 deselected, 4 warnings in 14.87s`.
- Focused migrated PostgreSQL run (`green.log`): `2 failed, 43 passed, 96 warnings in 93.52s (0:01:33)`. Both failures were a test assertion incorrectly expecting the reference ID in the edit form after the correct URL already returned 200.
- Corrected assertion checks the actual employee name in that form; affected cases rerun (`green-links.log`): `2 passed, 3 deselected, 4 warnings in 9.44s`. All selected cases have passing receipts across those runs; there is no single final all-case run.
- Existing calendar converter unit tests (`calendar.log`): `15 passed, 4 warnings in 3.97s`.
- `workspace-after/report.json`: 19 rendered layouts plus a collapsed-sidebar state; 14 interaction groups including actual save, hidden inputs, validation recovery, issue resolution, filtering, keyboard disclosure, accountant submission and owner re-authenticated approval. No detected document overflow, checked axe A/AA violations or JavaScript page errors. Dark/reduced-motion and enlarged-text layouts included.
- Final review wording and approval company context were recaptured on 2026-10-08 (`workspace-final/report.json`): six preparation/review/approval desktop and phone layouts, no detected overflow, checked axe violations or page errors. This final render does not repeat the 14 earlier interaction groups. The prior usage-limit approval failure was resolved on resume; the render completed with exit code 0.
- Independent source/render review found no material regression in the inspected slice; its minor absent-employee guidance issue was corrected to point to the full change record as well as employee rows. Approval now retains visible company context on phones. This is bounded peer review, not practitioner acceptance.
- Changed Python Ruff/format and changed CSS Stylelint passed in the implementation pass; final whitespace check passed on resume.

## Practical limits and next work

The shared monthly components and shell are more consistent; the entire platform is not yet unified. No new 80/90 score or whole-platform stability claim is warranted. The phone review still requires scrolling: the final six-person fixture is 3,433px tall, with Submit to owner at 3,119px. Preparation is 2,248px, with Save at 1,830px. Added date/name context increases height versus the preceding compact version; user observation must determine whether action placement needs another adjustment.

Next, verify one uncoached owner/preparer walkthrough on a real phone and record confusion. The next implementation slice is login/invitation/company setup plus dashboard and employee editing, using the same system and recovery patterns; then employee home/payslip/profile. Full critical-path Amharic/Oromo copy, screen-reader testing, network/session recovery, production performance and real-device acceptance remain open. Existing login/register/employee-home scans are evidence of inspected layouts, not completed redesigns of those flows.

No commit, hosted CI, merge, deployment or practitioner acceptance is claimed. Screenshots use synthetic data and are saved evidence, not a persistent live tester environment.
