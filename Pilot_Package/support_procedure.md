# Pilot Support Procedure

**Pilot support email:** support@ethiopayroll.com
**Pilot coordinator:** [name, phone]
**Engineering on-call:** [name, phone] (during business hours EAT)

## Response time targets

| Severity | Description | First response | Resolution target |
|---|---|---|---|
| **P0** | Cannot run payroll at all; data loss; security incident | 30 min | 4 hours |
| **P1** | One critical step blocked (e.g., approval, bank file generation) | 2 hours | 1 business day |
| **P2** | Workaround available, but a feature is broken | 1 business day | 3 business days |
| **P3** | Cosmetic / minor | 3 business days | Next release |

## How to report

1. **Email** `support@ethiopayroll.com` with subject `[PILOT] <one-line summary>`
2. **Include** the company name, the payroll period, and screenshots if UI-related
3. **Do NOT include** real employee names, TINs, or bank account numbers in the first email. Use IDs (`EMP-PLT-001`) or scramble the PII. Sensitive PII goes only over the encrypted channel (Step 4 below)
4. **For data-sensitive bugs** (anything that touches payroll numbers, TINs, bank accounts), use the encrypted channel: request the GPG key from the pilot coordinator
5. **For outages** (system unreachable, 5xx errors, cron not firing), mark the email `[PILOT][P0]` and CC the engineering on-call

## What the support team will ask you

Have these ready:

- Company name and pilot period
- The exact step you were on (which page, which button)
- The browser, OS, and the timestamp (with timezone)
- For calculation bugs: a screenshot of the EthioPayroll calculation narrative and your Excel cell references
- For data bugs: the employee ID (not the PII) and what you expected vs what you saw
- The Render request ID if you have one (visible in the browser Network tab)

## What the support team will NOT do

- Will not access your account without written permission and a support window
- Will not run payrolls for you
- Will not push code changes without a pilot-coordinator-approved ticket
- Will not share your data with anyone outside the support team

## Escalation

If a P0 is not acknowledged within 30 minutes during business hours, call the engineering on-call directly.

## Out of scope for pilot support

- Filing the actual ERCA / PSSA returns (you do this out of band)
- Sending the bank file to the bank (you do this out of band)
- Recovering Excel files from your local computer
- Any non-EthioPayroll software (Excel, your accounting tool, your email client, your bank portal)

## Data handling

- All pilot data is treated as production data
- Support engineers access pilot data only through approved audit-logged sessions
- All support interactions are logged in `/settings/audit-log` with the operator ID
- On pilot closure, all pilot data is retained for 90 days then deleted per the data retention policy
