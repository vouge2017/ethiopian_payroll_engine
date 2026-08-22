# Weekly Progress Report Template
### Ethiopian Workforce Operating System
**Purpose:** Track progress, surface blockers, maintain visibility

---

## How to Use

Fill this out every Friday. Send to the product owner. Keep it short — facts, not essays.

---

## Template

```
# Week of {date}

## Completed This Week
- {feature/task} — {PRD reference} — {status}

## Tests
- Passing: {count}
- Failing: {count}
- Coverage: {percentage}

## Bugs Fixed
- {bug description}

## Blockers
- {what's blocking you} — {what you need to unblock}

## Risks
- {risk} — {mitigation}

## Decisions Needing Approval
- {decision} — {your recommendation} — {deadline}

## Assumptions Made
- {assumption} — {impact if wrong}

## Next Week
- {planned work} — {PRD reference} — {estimated days}

## Design Impact (for completed features)
- Documents updated: {list}
- PRD sections implemented: {list}
- Business rules affected: {list}
- APIs changed: {list}
- Database tables changed: {list}
- Tests added: {count}
- Assumptions needing confirmation: {list}
```

---

## Example

```
# Week of 2026-08-04

## Completed This Week
- Payment batch creation — PRD-04, section 7 — Done
- Bank file generation — PRD-04, section 14 — Done

## Tests
- Passing: 645
- Failing: 0
- Coverage: 78%

## Bugs Fixed
- Bank account validation incorrectly rejected Telebirr numbers starting with7

## Blockers
- ERCA report format not verified — need accountant feedback

## Risks
- PDF generation timeout at 1000+ employees — needs background workers

## Decisions Needing Approval
- Should we support M-Pesa as a payment method? — Recommend yes for Kenya expansion

## Assumptions Made
- Pension is calculated on basic salary, not gross (awaiting accountant confirmation)

## Next Week
- Implement retry workflow for failed payments — PRD-04, section 7 — 3 days
- Add payment batch status tracking — PRD-04, section 13 — 2 days

## Design Impact
- Documents updated: API_CATALOGUE.md, ERROR_CATALOGUE.md
- PRD sections implemented: 7, 14
- Business rules affected: BR-04-01 through BR-04-09
- APIs changed: POST /api/payroll/{id}/payment-batch, POST /api/payment-batch/{id}/generate
- Database tables changed: payment_batch (new), payslip (added payment fields)
- Tests added: 12
- Assumptions needing confirmation: Pension base (basic vs gross)
```

---

*Consistent weekly reports make everything easier — reviews, planning, debugging, onboarding.*
