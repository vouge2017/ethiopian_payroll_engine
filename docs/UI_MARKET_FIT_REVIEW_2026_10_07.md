# Candid product UX re-review — 7 October 2026

The previous delivery improved a narrow payroll flow. It did not complete the user's requested coherent, understandable, market-appropriate experience. Passing code checks and reduced page height were given too much emphasis in the handoff.

This review changes no application source. Nine freshly rendered synthetic views were inspected: login, registration, payroll review at desktop/narrow phone, phone preparation, payroll dashboard, employees, Amharic-selected review and employee home. Each screen returned HTTP 200 with no JavaScript page errors. A separate read-only navigation check confirmed that the actual issue-resolution link returns HTTP 404.

## Target and business job

PROJECT_RULES.md identifies Ethiopian SMEs and Tigist as the initial practitioner. The primary jobs are preparing monthly changes, understanding and reconciling the amounts, owner approval, obtaining outputs and an employee finding their own payslip. The roadmap specifically emphasizes trust when comparing with Excel, lost-work recovery and clear compliance context. These are product intentions, not proof of existing complete behavior or a five-minute result.

Owner, payroll preparer/accountant and employee experiences must support different decisions while sharing one recognizable system. New HR/manager controls require an established role/workflow; enterprise complexity should not replace a clear SME task path. Language preference, period/date basis, ETB readability and supported outputs are concrete local concerns. Do not assume every Ethiopian user has identical language, device or accounting experience.

[HST's official payroll page](https://www.hst-et.com/services/technology/payroll-management-system) advertises Amharic localization, mobile access, employee payslips/history and role-based access. This supports treating those as relevant local competitive expectations; it is not hands-on evidence that HST implements them well or a reason to import its entire feature set.

## Material findings

| Priority | Observed problem | User consequence | Required correction |
|---|---|---|---|
| P1 | The missing-phone Fix This link is `/employees/SHEET1/edit`; actual read-only GET returns 404. The edit route requires an integer employee primary key. | A tester cannot resolve the issue through the offered action. Prior happy-path checks missed this. | Generate the link from the corresponding company-scoped employee PK; preserve the reference ID for comparison/filtering. Verify nonnumeric and numeric-reference cases. |
| P1 | 320px preparation identity is about 91px wide; ordinary two-word names occupy two lines, alongside recurring basic/allowance metadata. Edit text is hidden on phones, leaving a plus icon. | Shorter initial pages still feel cramped and make editing less recognizable. | Put employee identity across the row, show a visible Edit action and net pay, and move salary metadata into the expanded editor. Test scanning and edits, not only page height. |
| P1 | Review foregrounds Submit to owner before explaining the meaningful monthly changes. Gross/net deltas are in prose farther down, while summary cards omit them. | Users see permission to continue before enough context to understand the decision. | Put an evidenced prior-period comparison and changed-employee count beside totals before the next action; surface individual change explanations in each affected row. |
| P1 | Amharic selection still leaves core heading, totals, instructions, action labels and bottom navigation in English in the inspected view. | Language selection promises more than the core flow currently provides. | Make the selected-language behavior honest and consistent across the critical journey; validate translations and script rendering with a reader. Avoid copying hardcoded bilingual claims. |
| P2 | One advisory phone issue consumes a large card; description and Impact repeat the same outcome. Separate check-note and change cards make phone review 3,282px long. | Optional profile information dominates the payroll decision and increases scanning effort. | Distinguish blockers from optional notes, summarize each once and expand supporting explanation. Keep blockers prominent and actionable. |
| P2 | Review has an editorial serif/warm canvas; login retains a lilac multi-panel presentation; employee home retains older metric cards and icon-only document actions. | The slice does not yet establish a deliberately consistent product identity across roles and entry points. | Adopt one typography/palette/component specification and review complete journeys together, with intentional role/device variations. |
| P2 | Saved/estimated/preserved terminology, employee period `2018-12`, repeated money blocks and generic Fix This copy need explanation. | People transitioning from spreadsheets have to infer which month, amount or state is being shown. | Plain task copy, explicit period/calendar labels from existing facts, action-specific text and clear draft/review/approved/payment meanings. |
| P1 before handoff | The previously shared localhost preview stopped; it is not a reliable external tester link. First-use and uncertain-save/session recovery are not accepted end to end. | A tester handoff could fail even while saved screenshots and selected tests look good. | Prepare an identified reviewed tester build and stable environment, then walk the full first-use and recovery paths. Deployment remains separate. |

The link issue predates the blend; the UI work did not create it. The failing user action was nevertheless missed in the claimed core-flow coverage. This is a functional finding, not a request to change tax calculation or tenant authorization.

## What Stitch contributed and what we took too little of

Keep rejecting invented statutory seals, automatic payment readiness, wallet verification from a typed phone number and fictional sparkline data. Those claims need real supporting behavior.

Reconsider the useful ideas that were reduced too far: comparison at the decision point; employee-specific change context; concise status/findings; a coherent warm financial identity; and a reachable action surface designed around the task. These are not unnecessary work. A real two-period delta can be shown with existing retained comparison facts even if a historical chart is unsupported. An issue editor can feel direct while saving through the current authorized route.

Motion should reinforce a successful save, changed field or opened detail and respect reduced motion. Continuous verification pulses and decorative state changes do not establish trust. Trust comes from understanding the amounts, recovering from mistakes and seeing truthful feedback.

## Correction direction

One integrated monthly workspace: company and period → totals plus evidenced changes → concise blocking/optional findings → readable employee ledger with contextual changes → the role-appropriate action. Keep the action easy to reach after decision context, with reserved space if an action footer is used.

Prioritize the broken resolution link and narrow-phone identity first. Then recompose the review decision around actual comparisons and concise findings. Apply the same system to entry, employee management and employee payslip access; finish first-use, error/session/retry behavior before external tester claims. Use real-device and uncoached user observation to judge whether less scrolling produces easier work.

No broad new features, tax rewrite, fake integrations or full billing redesign are needed to correct these gaps. The next work should be a coherent correction to the critical task, not another isolated color pass or a new design-tool installation.

## Score correction

The prior approximately 80/100 was a provisional limited-journey assessment, not a whole-platform or tester-readiness score. This broader product review does not support increasing it toward 90.

Independent product critique: desktop visual execution about 7.5/10; narrow-phone scanning about 6.5/10; first-use decision clarity about 6.5–7/10. Stitch's desktop aesthetic direction remains approximately 8–8.5/10, with prototype accessibility and truthfulness defects already recorded. These are subjective judgments of specified aspects; they do not constitute a new aggregate product score or competitor ranking.

Independent code-safety approval remains useful evidence for the bounded patch. It is distinct from product/design approval. Existing passing regression receipts remain historical evidence of the cases they actually cover; they did not exercise the failing Fix This link.

## Evidence

- `local-evidence/critical-ux-review-20261007/report.json`: nine rendered views, HTTP status, headings, action positions, employee row dimensions and link targets.
- `navigation-report.json`: actual authenticated issue link GET status 404.
- Fresh screenshots in the same folder, including `prepare-320.png`, `review-am-390.png`, `login-1440.png` and `employee-390.png`.
- Supplied Stitch files remain unchanged; previous fresh render and source assessment are in `output/payroll-stitch-assessment-2026-10-07/`.
- Reviewed checkout remains `codex/monthly-payroll-ui`, baseline HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`, dirty/uncommitted. No new product implementation, commit or deployment in this re-review.

The automatic permission review timed out once for the synthetic render run; the permitted retry succeeded. The old preview and task database had stopped; the existing task-only cluster was restored and new disposable fixtures completed. No unavailable browser run is reported as successful.
