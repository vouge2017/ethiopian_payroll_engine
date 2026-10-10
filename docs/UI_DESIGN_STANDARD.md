# EthioPayroll interface decisions

The initial market is Ethiopian SMEs: an owner, a payroll preparer and employees. The interface must make the company, period, amounts, changes, findings and next action understandable. Design quality includes readability, personality, language, useful motion and recovery, alongside working controls.

## Shared rules

- Show today's Ethiopian and Gregorian dates separately from the selected payroll period. Convert actual start/end dates with existing helpers; never substitute month names or change calculation periods.
- Use one calm financial identity: warm neutral surfaces, dark emphasis for net pay, familiar blue actions, readable Ethiopic/Latin typography and aligned tabular figures. Semantic colors communicate actual states.
- Keep company context visible when phone navigation hides it. Provide labeled phone navigation and a working, accessible desktop collapse control; icon-only links retain accessible names and tooltips.
- Put factual comparisons and concise findings before a decision. Show individual change explanations beside the employee's amounts. Distinguish blockers, items requiring review and advisory information.
- Phone rows preserve readable identity and an explicit Edit action. Secondary salary metadata belongs inside the editor. Desktop supports efficient repeated editing. Closing/filtering never omits submitted inputs.
- Use native controls, visible focus and clear labels; respect reduced motion. Saving feedback reflects actual server success. Errors explain recovery; uncertain outcomes must never claim success.
- Preserve role authority, company ownership, statutory arithmetic and approved facts. Display improvements do not create new payment or verification capabilities.

## Page order and acceptance

| Page/flow | Priority | Work |
|---|---|---|
| Preparation, review, approval | Now | Dual periods, readable rows, decision context, working issue actions and shared navigation |
| Login, registration, invitation, company setup | Next | One visual language; finish first-use, validation, expired-session and recovery paths |
| Dashboard, employees/edit/import | Next | Clear next task, factual status, trustworthy import/Excel transition and error recovery |
| Employee home, payslip, profile | Next | Clear period, net-pay explanation, labeled document actions and selected-language consistency |
| Results/downloads, filing, attendance, settings, Help | Following | Extend proven components; verify the important tasks and states |
| Billing, upgrades, platform admin, new HR/manager roles | Existing supported scope only | Do not invent functionality or roles for a design checklist |

Use actual rendered desktop/phone/tablet views, keyboard access, long names, large amounts, dark mode and enlarged text. Test real saving, resolving findings and approval, not just appearance. Real devices, screen readers, translations and uncoached users are separate acceptance evidence. Local checks do not establish deployment or whole-platform stability.
