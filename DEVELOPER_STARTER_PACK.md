# Developer Starter Pack
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**For:** MimoClaw engineering team

---

## What This Is

A curated set of documents for the engineering team. Not all 74 documents — just the ones they need to make good engineering decisions.

**Read time: ~3 hours total.** After that, you understand the product, the architecture, the rules, and how to contribute.

---

## Starter Pack Contents

### Tier 1: Read First (Day 1)

| # | Document | Time | Purpose |
|---|----------|------|---------|
| 1 | `EXECUTIVE_PROJECT_BRIEF.md` | 10 min | What this product is and why it exists |
| 2 | `OPERATING_MANUAL.md` | 20 min | The handbook — vision, principles, journey map, document map |
| 3 | `WORKFORCE_OPERATING_SYSTEM_PRINCIPLES.md` | 5 min | 10 rules that govern everything |
| 4 | `PRD-TEMPLATE.md` | 5 min | How PRDs are structured (32 sections) |

### Tier 2: Understand the System (Day 2)

| # | Document | Time | Purpose |
|---|----------|------|---------|
| 5 | `FUNCTIONAL_SPECIFICATION.md` | 30 min | How the product behaves across 10 modules |
| 6 | `ARCHITECTURE_DECISIONS.md` | 30 min | 22 architectural decisions — why things are the way they are |
| 7 | `DATA_MODEL.md` | 15 min | Database entities and relationships |
| 8 | `BACKEND_ARCHITECTURE.md` | 10 min | API standards, error model, conventions |
| 9 | `ENGINEERING_QUALITY_STANDARDS.md` | 10 min | Coding standards, testing strategy |

### Tier 3: Know the Rules (Day 3)

| # | Document | Time | Purpose |
|---|----------|------|---------|
| 10 | `BUSINESS_RULE_CATALOGUE.md` | 15 min | 116 business rules |
| 11 | `VALIDATION_CATALOGUE.md` | 10 min | 74 validation rules |
| 12 | `STATE_MACHINE_CATALOGUE.md` | 10 min | 8 state machines |
| 13 | `PERMISSION_CATALOGUE.md` | 5 min | RBAC matrix |
| 14 | `API_CATALOGUE.md` | 10 min | All endpoints |
| 15 | `ERROR_CATALOGUE.md` | 10 min | All error codes |

### Tier 4: Know How to Work (Day 4)

| # | Document | Time | Purpose |
|---|----------|------|---------|
| 16 | `DEVELOPER_ONBOARDING_GUIDE.md` | 10 min | How to get started |
| 17 | `DEVELOPER_PLAYBOOK.md` | 20 min | How to add features, rules, APIs, tests |
| 18 | `IMPLEMENTATION_CHECKLIST.md` | 5 min | Checklist for every PR |
| 19 | `DEFINITION_OF_READY.md` | 5 min | When can I start? |
| 20 | `DEFINITION_OF_DONE.md` | 5 min | When is it finished? |
| 21 | `PRODUCT_GOVERNANCE_GUIDE.md` | 10 min | Who can change what |

### Tier 5: Ongoing Reference

| # | Document | Purpose |
|---|----------|---------|
| 22 | `CONFIGURATION_CATALOGUE.md` | Every configurable setting |
| 23 | `DECISION_FLOW_CATALOGUE.md` | System decision logic |
| 24 | `COMPLIANCE_MATRIX.md` | Law → implementation mapping |
| 25 | `DOMAIN_MODEL.md` | Business concepts explained |
| 26 | `DECISION_MATRIX.md` | Why products behave as they do |
| 27 | `TRACEABILITY_MATRIX.md` | End-to-end traceability |
| 28 | `WEEKLY_PROGRESS_REPORT_TEMPLATE.md` | How to report progress |
| 29 | `OPEN_QUESTIONS.md` | Where to ask questions |
| 30 | `DECISION_LOG.md` | Where to record decisions |

### PRDs (Reference as Needed)

| Document | Journey |
|----------|---------|
| `PRD-00-COMPANY-SETUP-MIGRATION.md` | Company Setup |
| `PRD-01-HIRE-EMPLOYEE.md` | Hire Employee |
| `PRD-02-PREPARE-PAYROLL.md` | Prepare Payroll |
| `PRD-03-APPROVE-LOCK-PAYROLL.md` | Approve & Lock |
| `PRD-04-PAY-EMPLOYEES.md` | Pay Employees |
| `PRD-05-BANK-FILE-GOVERNMENT-FILING.md` | Government Filing |
| `PRD-06-GENERATE-PAYSLIPS.md` | Generate Payslips |
| `PRD-07-WORKFORCE-LIFECYCLE.md` | Workforce Lifecycle |
| `PRD-08-COMPLIANCE-AUDIT.md` | Audit & Compliance |
| `PRD-09-EMPLOYEE-SELF-SERVICE.md` | Employee Self-Service |

---

## What NOT to Read

Don't read these unless specifically asked:
- `DIAGNOSTIC_ANSWERS.md` (historical)
- `AUDIT_REPORT_*.md` (historical)
- `SESSION_SUMMARY_*.md` (historical)
- `VERIFICATION_PACKAGE.md` (for accountant, not developers)
- `ERCA_EXPORT_GUIDE.md` (for accountants)

---

## Quick Reference Card

```
Need to know...          → Read this
─────────────────────────────────────────
What the product does    → EXECUTIVE_PROJECT_BRIEF.md
How it works             → FUNCTIONAL_SPECIFICATION.md
Why it's built this way  → ARCHITECTURE_DECISIONS.md
What the rules are       → BUSINESS_RULE_CATALOGUE.md
What to validate         → VALIDATION_CATALOGUE.md
How things change state  → STATE_MACHINE_CATALOGUE.md
Who can do what          → PERMISSION_CATALOGUE.md
What APIs exist          → API_CATALOGUE.md
What errors are possible → ERROR_CATALOGUE.md
How to add a feature     → DEVELOPER_PLAYBOOK.md
What to check in a PR    → DEFINITION_OF_DONE.md
Who decides what         → PRODUCT_GOVERNANCE_GUIDE.md
```

---

*30 documents. 3 hours. Then you're ready to build.*
