# Core payroll design blend — 7 October 2026

Implemented locally on `codex/monthly-payroll-ui`, baseline HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`. The patch is uncommitted; existing dirty work and the outer mobile checkout are preserved. This delivery changes six UI source files and does not change payroll calculations, server authorization, schemas or approved facts.

## User outcome

Preparation, review and approval now share warmer neutral surfaces, a distinctive editorial heading, clearer process steps and an emphasized net-pay summary. The established blue action color remains consistent across the application. Shared surface tokens also apply to other screens; the full platform has not been redesigned.

Phone preparation starts with compact employee rows showing identity and saved estimated net pay. Native disclosures expose the full inputs and deductions. Desktop editors start expanded for repeated work. Finding one employee opens their editor; users can collapse it again. Edited rows retain an unsaved indicator and identify the summary as the last saved net. Collapsing or filtering never disables or removes canonical submitted inputs. Invalid hidden inputs clear the filter and open their editor before native validation focuses the field. Without JavaScript, preparation editors remain expanded and normal form submission is available.

Review shows compact preserved rows with gross/net context and native keyboard-accessible breakdowns. Search, All employees / With review issues / Changed filters, result counts and clear/no-match recovery work without changing preserved payroll totals. Review issues use existing exception identifiers and active non-HINT validation employee primary keys; changed rows use the retained comparison. Global findings remain above the ledger. The filter controls are hidden without JavaScript; all native breakdowns remain available.

No simulated bank verification, speculative disbursement status, hardcoded trends, new department taxonomy or repeated decorative pulse was adopted. Labels describe owner review/approval; approval still does not send payment. The current step advances for pending approval and approved runs. Motion remains short press/saving feedback, with reduced motion respected.

## Before and after

Fresh matching fixtures: six synthetic employees, same payroll facts, Chrome at 390×844. Final compact-header receipt supersedes the earlier phone header captures.

| Observation | Before this slice | Final compact phone layout |
|---|---:|---:|
| Preparation page height | 5,073px | 1,934px |
| Save action position | 4,654px | 1,516px |
| Review page height | 4,337px | 3,282px |
| Review submit action position | 668px | 735px |
| Approval page height | 2,301px | 2,368px |

Preparation is about 62% shorter with all editors initially collapsed on phones. This is reduced initial scrolling, not a measured improvement in task completion time; expanded editing adds content and interaction steps. Richer shared summaries initially pushed the phone review action to 775px; compact step tiles reduced it to 735px. It remains slightly lower than before. Approval is 67px longer. Readability and identity must not be presented as reductions in every screen's length.

## Verification

- Final compact pass: 13 views, including 320/390px core screens, dark mode/reduced motion, 200% root text on 768px, actual signed-out login/registration and employee home. No detected document overflow, axe A/AA violations or JavaScript page errors.
- Preceding pass: 19 layouts at 1440/768/390/320px and dark/large-text/entry/portal variants. Separate stress pass: 12 layouts with long Amharic/Latin and unbroken names, literal special characters and large amounts. No detected overflow, axe violations or page errors. The later targeted compact pass verifies the changed phone header; no single fresh all-platform scan is claimed.
- Ten interaction groups pass in the final compact pass: compact startup/keyboard disclosure; all employees/fields retained in FormData; dirty review protection; real save of a filtered-out edit; hidden/collapsed invalid-field recovery; preparation no-match; review filters/clear/no-match; unchanged aggregate totals; keyboard review breakdown; actual accountant submission and owner re-authenticated approval.
- Disposable migrated PostgreSQL focused receipt: `43 passed, 92 warnings in 60.19s (0:01:00)`. Saving, server validation, approval/PDF/bank outputs and effective-role presentation are covered by the selected suites. This is a focused receipt, not the full suite or hosted CI.
- Final changed CSS Stylelint and JS syntax checks pass. Git whitespace check passes.
- The initial entry-screen captures followed authenticated redirects; their report is preserved as `report-initial.json`. Corrected signed-out checks pass in subsequent reports. The first attempt to start the browser fixture found the test database stopped; the existing task-only cluster was restarted and fresh fixtures succeeded.
- A new live synthetic preview was independently checked for rendered review/preparation, six employee rows, compact startup, no raw template text and no page errors.
- Independent read-only source review found no material regression in the six-file slice, confirming canonical input submission, invalid-field recovery, native keyboard disclosures and correct identifier mapping. This is source review, not practitioner acceptance.

Evidence: `local-evidence/stitch-blend-20261007/{blend-before,blend-after,blend-stress,blend-compact,blend-preview}/`, `tests.log`, `after.log`, `stress.log`, `compact.log`. Task-start source copies are in `source-before/` to distinguish this slice from preceding dirty UI work.

Live preview at delivery: `http://127.0.0.1:62787/synthetic-design/accountant` (accountant), `/synthetic-design/owner` (owner), `/synthetic-design/employee` (employee). Synthetic data only. Runner session `12094` and this task-only PostgreSQL cluster remain running for inspection; the runner's normal shutdown closes its fixture and drops its generated database. Use the latest preview.json if restarted.

## Now and next

This is available for a local internal walkthrough using synthetic data. The current preview URLs are recorded in `blend-preview/preview.json`; its runner remains alive for inspection. It is not a hosted tester environment or a deployed patch.

Next bounded work: verify first use through account/company/employee setup into the first payroll, and correct reachable empty/error/expired-session/retry states using these shared patterns. Then observe a preparer, owner and employee completing tasks without coaching on real devices; fix observed misunderstandings before extending visual polish to lower-priority screens.

The earlier approximately 80/100 was a provisional inspected-journey judgment. This delivery gives stronger measured layout and interaction evidence; it does not establish a new whole-platform score, 90-level acceptance, physical-device behavior, screen-reader conformance, translated UI acceptance or network-failure recovery. Additional tools, decorative animation, billing redesign and new roles are not prerequisites for this slice.
