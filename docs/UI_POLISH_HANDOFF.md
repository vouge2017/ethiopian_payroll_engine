# UI/UX improvement delivery — 6 October 2026

The actual application now has a more coherent monthly payroll journey. Preparation, review and owner approval share a visual system; employee search and interaction feedback are functional. This is implemented locally on `codex/monthly-payroll-ui`, based on HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`. The patch is uncommitted. The checkout already contained UI work, which was preserved.

## What users will notice

| Area | Delivered change | Practical value |
|---|---|---|
| Composition and color | Existing blue identity, quiet neutral surfaces, readable semantic colors, consistent focus rings and restrained shadows | Financial amounts and decisions receive attention; warnings retain meaning |
| Shared layout | One reusable step indicator and four-part financial summary across preparation, review and approval | Users recognize the same process rather than relearning each screen |
| Preparation | Name/ID search, no-match feedback, visibly edited fields, saving feedback and protection against duplicate submission | Find a person quickly and understand whether an edit has been saved |
| Search safety | Filtering keeps every canonical input in the submission; invalid hidden fields are revealed | Searching cannot silently omit employees or hide a validation problem |
| Review | Preserved aggregate totals and the role-appropriate next action near the top; mobile findings precede full employee amounts | Understand the payroll and find the next action without scrolling through every detail |
| Review density | Supporting causes, recommendations, employee change details and nonblocking hints expand on demand | Less repetition while amounts, issue impact, flags and blockers remain available |
| Confirmation | Calm approval panel, consistent money formatting, clearer password/action copy and explicit irreversible consequence | Approval feels deliberate and understandable |
| Entry | Sign-in copy covers payroll staff, owners and employees; account recovery replaces a support link that returned anonymous users to login | Users see an entry point appropriate to their work |
| Accessibility | Password toggles are keyboard reachable with announced state; employee payslip links have names; contrast defects repaired | Controls are understandable beyond their icon/color |
| Employee portal | Amounts retain cents instead of rounding to whole birr | Displayed pay remains precise |
| Motion | Short press/color feedback and saving indicator; existing reduced-motion rules respected | The product responds without delaying frequent tasks |

No new frontend framework, package, animation library or calculation engine was introduced. Displayed financial totals use existing server facts. Native forms, server validation, explicit saved-review refresh and owner re-authentication remain the operational foundation.

## Measured results

The before and after browser fixtures use the same six synthetic employees and saved monthly facts. These are local Chrome observations, not real-user completion times.

| Observation | Before | After |
|---|---:|---:|
| Phone review action position from page top | 4,649 px | 681 px |
| Desktop review action position | 1,936 px | 439 px |
| Phone review full-page height | 4,878 px | 4,350 px |
| Phone preparation full-page height | 4,947 px | 5,086 px |
| Registration contrast violations detected | 1 category | 0 |
| Employee portal violations detected | Contrast + unnamed links | 0 |

Preparation is slightly longer because readable labels and search occupy space. Its remaining weakness is whole-team traversal on phones. Search improves targeted edits; it does not solve large-list efficiency. This is a concrete next design problem, not something to conceal behind the score.

- Final batched Playwright/axe run: **12 layouts**, 1440px desktop and 390px phone where applicable; **zero detected page overflow, axe A/AA violations or JavaScript page errors**. Additional 320px preparation check passed.
- **11 interaction assertions passed**: keyboard password visibility; search retains all six employee inputs; no-match feedback; dirty edits prevent review; actual native save/reload; hidden-invalid-field recovery; Back clears busy state; accountant submits; owner confirms and approves; 320px layout; reduced-motion transitions.
- Final compact confirmation rows were separately checked on desktop and phone after a visual refinement. Receipt is in `local-evidence/visual-polish-20261006/confirm/`.
- PostgreSQL/Alembic regressions: initial **24 passed, 1 failed, 50 warnings in 45.81s**. The failure expected an ungrouped display value (`4310.15`) after the UI adopted `4,310.15`. Updated only that display assertion; affected full approval/PDF/bank journey then **1 passed, 2 warnings in 5.92s**. All 25 selected cases have passing receipts; there was no subsequent single all-25 run.
- The selected cases include effective-role navigation, removed membership, owner/accountant confirmation, legacy company-label consistency, monthly links, preserved comparison/blockers, real saving, submission/approval, explicit refresh and PDF/bank agreement. Test fixtures apply real migrations to disposable PostgreSQL databases.
- JS syntax, both changed CSS files' Stylelint, changed Python Ruff/format and Git whitespace checks pass.
- Independent read-only peer review identified hidden-invalid-field and stale-busy-state issues; both were fixed and exercised. It confirmed the fixes and found no remaining material concern in this bounded scope.

Automated accessibility checks do not establish WCAG conformance. Full keyboard traversal, screen readers, zoom, dark mode, language variants, physical devices, slow-network recovery and larger employee datasets still need broader validation. No new performance trace was collected. Earlier Lighthouse results remain historical and cannot certify this patch.

## Candid score

The earlier **69/100** referred to the inspected local journey; **65/100** referred to the separate standalone concept. They were approximate judgments, not measured completion percentages. The concept is not the current application.

Using the same agreed 100-point rubric, the current inspected journey is provisionally **about 80/100**. The independent visual assessment is **about 8/10**, up from 6.5–7/10. Neither score covers the entire platform.

| Dimension | Maximum | Provisional now | What would support a 90-level result |
|---|---:|---:|---|
| User value and clarity | 15 | 13 | Observe first-use orientation and correct understanding of saved, approved and paid states |
| Usability and efficiency | 20 | 16 | Compact whole-team editing, clear first-run recovery, observed unassisted core-task completion |
| Visual design and hierarchy | 15 | 12 | Extend the system across remaining core screens and refine long phone flows |
| Consistency/design system | 10 | 8 | Inventory and align all component/error/loading/empty states across reachable flows |
| Accessibility/inclusivity | 10 | 7 | Complete manual keyboard, screen-reader, zoom and local-language acceptance |
| Responsive behavior | 10 | 8 | Physical phones, tablet/landscape, on-screen keyboards, long names and larger lists |
| Reliability and feedback | 10 | 8 | Exercise connection loss, expired sessions, uncertain save outcomes and recoverable failures |
| Payroll trust and decision safety | 10 | 8 | Practitioner reconciles preserved review, approved outputs and role-correct tasks |
| Total | 100 | 80 | Evidence across these dimensions; no critical defect may be averaged away |

Performance, maintainability and business outcomes remain explicit evidence within this rubric: shared components reduce drift; network/rendering costs require measurement; successful first payroll and reduced assistance require user observation. The seven original categories total 90; the agreed additional 10 is payroll trust and decision safety. We are not silently switching scorecards to manufacture a higher result.

## Design references and market judgment

The uploaded references provide useful directions, not validated products. The following scores judge visible design only; screenshots cannot prove working controls, accessibility or payroll reliability.

| Reference | Visual judgment | Useful direction | Limit for this project |
|---|---:|---|---|
| Image 1: readiness dashboard | ~8/10 | Clear next action, readiness and actionable issues | Secondary activity/resources compete for space; needs role and Ethiopian context |
| Image 2: employee mobile | ~8/10 | Net pay emphasis, readable breakdown and inline explanation | Estimate-to-final pay differences need explanation; US tax copy is unsuitable |
| Image 3: operations | ~8/10 | Severity, owner, deadline and resolution action | Multi-country command-center scope exceeds this SME pilot |
| Image 4A: guided review | ~8.5/10 | Best first-user orientation, checks before approval | Still needs working recovery and responsive/state evidence |
| Image 4B: dense review | ~8/10 | Efficient desktop scanning and filtering | More demanding for first-time or phone users |

We adopted guided orientation with optional detail rather than choosing one density for every role/device.

Current market documentation supports separate preparation/approval permissions and employee self-service: [Gusto payroll approvals](https://support.gusto.com/article/240829150046240/set-up-approvals-for-payroll-for-admins), [Gusto employee self-service](https://gusto.com/product/payroll/employee-self-serve), and [Deel worker self-service](https://developer.deel.com/api/embedded/eor-overview). Our design inference is to borrow task separation, clear review states and access to one's own documents. These pages do not establish a competitive usability score or Ethiopian compliance. Global HR breadth and automated payment claims are not pilot requirements.

Applied [Impeccable improvement guidance](https://impeccable.style/docs/improve-design/) and [polish guidance](https://impeccable.style/docs/polish/) to hierarchy, readable density, states and consistency. Impeccable was read from its published skill/reference source; it was not installed locally. The [Taste skill](https://www.tasteskill.dev/docs) emphasizes visual discipline but its current landing-page scope excludes data-table/multi-step product UI, so it informed restraint rather than dictating this dashboard. [Emil Kowalski's motion guidance](https://emilkowal.ski/ui/you-dont-need-animations) supports subtle feedback and avoiding unnecessary animation in repeated workflows. Local frontend-design, accessibility, Playwright, payroll review and independent-review capabilities supported implementation and verification.

## Next delivery direction

1. **Reduce phone traversal.** Explore a compact employee overview with explicit row expansion/editing; keep all employees included, dirty-state recovery and readable financial totals. Confirm realistic employee-list sizes with pilot users before choosing pagination or bulk controls.
2. **Finish the first-run journey.** Verify actual registration/invitation, company setup, employee entry/import, first payroll, empty states and recovery. Current registration work fixes visual/keyboard issues; it is not an end-to-end SMS/email acceptance receipt.
3. **Align remaining operational screens.** Audit dashboard, employee edit, attendance, results/downloads, settings, Help, permission-denied and session-expired views against the same tokens/components. Billing/upgrade and account deletion must reflect existing supported behavior; do not add features simply to complete a checklist. HR/manager/platform-admin flows need separate role definitions before presenting new controls.
4. **Exercise the state matrix.** Empty/loading/error/saved/dirty/busy/blocked/flagged/pending/approved/permission-denied/expired-session/connection-loss states, plus destructive actions and uncertain outcomes. Confirm retry or recovery produces the intended result.
5. **Measure tester readiness.** Use a named reviewed build and synthetic data first. Observe a preparer saving changes, an owner resolving findings/approving, and an employee finding a payslip. Record task completion, time, hesitation, help needed and misunderstanding. Treat the existing “phone in five minutes” product aspiration as a target to validate, not an achieved result.

An internal synthetic walkthrough is supported by the local evidence. A deployed or practitioner-accepted pilot is not established. This patch has no new hosted checks, commit, deployment or user-observation receipt. Release decisions remain separate.

## Evidence and implementation locations

- Screenshots and JSON: `local-evidence/visual-polish-20261006/{before,after,confirm}/`.
- Test receipts: `tests.log`, `tests-final.log` in that evidence folder.
- Browser runner: `local-evidence/run_visual_polish.py`; assertions: `local-evidence/visual-polish-qa.cjs`. Synthetic sign-in shortcuts exist only in the ignored local runner, not application code.
- Shared finish: `payroll_engine/static/css/product-polish.css`.
- Journey layout: `payroll_engine/static/css/monthly-payroll.css` and `templates/components/monthly_payroll.html`.
- Behavior: `payroll_engine/static/js/monthly-payroll.js`.
- A separate before/after gallery is published as a local artifact in the outer workspace output folder.

No further product decision was needed for these reversible UI changes. The next useful human input is observation from the founder/Tigist and a representative employee, with their device, language and realistic team size.
