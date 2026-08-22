# Developer Starter Pack v2
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**For:** MimoClaw engineering team

---

## How to Use This

Read the **Required** section (2-3 hours). Everything else is reference — look it up when you need it.

---

## Required (Read Before Coding)

| # | Document | Time | What It Teaches |
|---|----------|------|-----------------|
| 1 | `EXECUTIVE_PROJECT_BRIEF.md` | 10 min | What this product is |
| 2 | `OPERATING_MANUAL.md` | 20 min | Vision, principles, journey map |
| 3 | `FUNCTIONAL_SPECIFICATION.md` | 30 min | How the product behaves |
| 4 | `ARCHITECTURE_DECISIONS.md` | 30 min | Why things are the way they are |
| 5 | `ENGINEERING_QUALITY_STANDARDS.md` | 10 min | Coding standards |
| 6 | Your assigned PRD (see Current Sprint) | 20 min | What you're building |
| 7 | `DEVELOPER_PLAYBOOK.md` | 20 min | How to add features |

**Total: ~2.5 hours.** Then start coding.

---

## Current Sprint

| Priority | Feature | PRD | Status |
|----------|---------|-----|--------|
| P1 | Prepare Payroll | PRD-02 | Code exists, needs review |
| P2 | Approve & Lock | PRD-03 | Code exists, needs review |
| P3 | Pay Employees | PRD-04 | PRD complete, not implemented |
| P4 | Government Filing | PRD-05 | PRD complete, code partial |
| P5 | Generate Payslips | PRD-06 | Code exists, needs review |
| P6 | Workforce Lifecycle | PRD-07 | Code exists, needs review |
| P7 | Audit & Compliance | PRD-08 | PRD complete, not implemented |
| P8 | Employee Self-Service | PRD-09 | Code exists, needs review |

**Start with your assigned PRD. Don't jump ahead.**

---

## Before You Start (Checklist)

Before writing any code, answer these:

```
- [ ] Which PRD am I implementing?
- [ ] Which ADRs apply? (check PRD header)
- [ ] Which Business Rules apply? (PRD section 10)
- [ ] Which Validation Rules apply? (PRD section 11)
- [ ] Which State Machine applies? (PRD section 13)
- [ ] Which APIs are affected? (PRD section 14)
- [ ] Which database tables change? (PRD section 15)
- [ ] Which acceptance tests must pass? (PRD section 28)
- [ ] Are there open questions? (check OPEN_QUESTIONS.md)
```

If any answer is missing, add it to `OPEN_QUESTIONS.md` and ask before proceeding.

---

## Engineering Expectations

Every completed feature must include:

| Component | Required |
|-----------|----------|
| Code implementation | ✅ |
| Database migration (if needed) | ✅ |
| API endpoints | ✅ |
| Validation rules | ✅ |
| Business rules | ✅ |
| State machine transitions | ✅ |
| Audit events | ✅ |
| Analytics events | ✅ |
| Error handling | ✅ |
| Tests (unit + integration) | ✅ |
| Documentation updates | ✅ |

**Nothing ships without all of these.**

---

## Before You Open a PR (Checklist)

```
## PR Checklist

### What Changed
- Feature: {name}
- PRD: {PRD-xx, sections implemented}

### Business Rules
- [ ] BR-{xx}-{yy}: {rule description}
- [ ] BR-{xx}-{yy}: {rule description}

### Validation Rules
- [ ] VL-{xx}-{yy}: {rule description}
- [ ] VL-{xx}-{yy}: {rule description}

### APIs
- [ ] {METHOD} {endpoint}: {what changed}

### Database
- [ ] {table}: {what changed}

### Tests
- [ ] {test file}: {what was tested}

### Documentation Updated
- [ ] PRD updated (if behavior changed)
- [ ] Business Rule Catalogue (if new rules)
- [ ] Validation Catalogue (if new validations)
- [ ] API Catalogue (if new endpoints)
- [ ] Error Catalogue (if new errors)

### Assumptions
- {any assumptions needing product confirmation}
```

---

## Working Agreement

1. **PRDs are the source of truth** for feature behavior. If the PRD says one thing and the code says another, the PRD wins.
2. **ADRs explain why** a design exists. Don't bypass them without approval.
3. **New business logic requires** corresponding Business Rules and Validation Rules in the catalogues.
4. **Every change affecting workflows or APIs** must update the relevant documentation.
5. **If Ethiopian legal requirements are unclear**, stop and ask. Don't assume.
6. **Product decisions require product owner approval** before implementation.
7. **If you find a bug**, fix it and add a regression test. Don't just patch.
8. **If you're unsure about anything**, add it to `OPEN_QUESTIONS.md` and ask.

---

## Current Implementation Status

| Module | Status | Notes |
|--------|--------|-------|
| Authentication | ✅ Complete | Phone+OTP, password, OAuth, MFA |
| Employee Management | ✅ Complete | CRUD, import, validation |
| Payroll Calculation | 🟡 90% | Core works, needs cross-check engine |
| Approval Workflow | 🟡 80% | Basic flow works, needs confidence report |
| Payment Engine | 🔴 Not started | PRD complete, code not written |
| Government Filing | 🟡 70% | ERCA report exists, needs filing tracking |
| Payslip Generation | ✅ Complete | PDF generation, acknowledgment |
| Employee Portal | 🟡 80% | Dashboard, payslips, leave, profile |
| Termination & Settlement | 🟡 70% | Severance works, needs settlement flow |
| Audit & Compliance | 🟡 60% | Hash chain exists, needs audit packages |
| Multi-tenancy | ✅ Complete | TenantQuery enforced |
| Encryption | ✅ Complete | Bank account + TIN encrypted |

---

## Reference Documents (Look Up When Needed)

| Document | When You Need It |
|----------|-----------------|
| `BUSINESS_RULE_CATALOGUE.md` | "What's the rule for this?" |
| `VALIDATION_CATALOGUE.md` | "What should I validate?" |
| `STATE_MACHINE_CATALOGUE.md` | "What states does this entity have?" |
| `PERMISSION_CATALOGUE.md` | "Who can do this?" |
| `API_CATALOGUE.md` | "What endpoints exist?" |
| `ERROR_CATALOGUE.md` | "What error code should I use?" |
| `CONFIGURATION_CATALOGUE.md` | "Is this configurable?" |
| `DECISION_FLOW_CATALOGUE.md` | "How does the system decide this?" |
| `COMPLIANCE_MATRIX.md` | "What law requires this?" |
| `DOMAIN_MODEL.md` | "What does this business concept mean?" |
| `TRACEABILITY_MATRIX.md` | "Where does this come from?" |
| `DEFINITION_OF_READY.md` | "Can I start this?" |
| `DEFINITION_OF_DONE.md` | "Is this finished?" |
| `PRODUCT_GOVERNANCE_GUIDE.md` | "Who approves this change?" |

---

## Communication

- **Questions** → Add to `OPEN_QUESTIONS.md`
- **Decisions** → Add to `DECISION_LOG.md`
- **Progress** → Fill `WEEKLY_PROGRESS_REPORT_TEMPLATE.md` every Friday
- **Blockers** → Raise immediately, don't wait

---

*Read the7 required documents. Check the sprint. Start coding. Ask questions.*
