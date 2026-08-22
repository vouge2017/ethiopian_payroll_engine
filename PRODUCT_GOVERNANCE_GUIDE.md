# Product Governance Guide
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**Purpose:** Who can change what, and how

---

## Decision Authority Matrix

| Decision Type | Who Approves | Process |
|--------------|-------------|---------|
| **Architecture changes** | Product Owner + Tech Lead | New ADR required |
| **Ethiopian payroll rules** | Product Owner + Accountant | Update Business Rule Catalogue, get written confirmation |
| **PRD changes** | Product Owner | Update PRD, notify team |
| **New features** | Product Owner | PRD required before development |
| **Breaking API changes** | Tech Lead | ADR required, versioning plan |
| **Database schema changes** | Tech Lead | Migration required, DATA_MODEL.md updated |
| **Security changes** | Product Owner + Security Review | ADR required |
| **UI/UX changes** | Product Owner | Design review required |
| **Configuration changes** | Product Owner | Update Configuration Catalogue |
| **Legal/compliance changes** | Accountant + Product Owner | Compliance Matrix updated, written confirmation |

---

## What Requires an ADR

An Architecture Decision Record is required when:
- Changing how the system calculates payroll
- Changing how payments work
- Changing the audit/hash chain mechanism
- Changing tenant isolation
- Changing authentication/authorization
- Changing encryption approach
- Adding a new country/jurisdiction
- Changing the approval workflow
- Any change that affects data integrity

**How to create an ADR:**
1. Write the ADR following the format in `ARCHITECTURE_DECISIONS.md`
2. Include: Context, Decision, Consequences, Alternatives, Risk
3. Submit for review by Product Owner + Tech Lead
4. After approval, add to the ADR document

---

## What Requires Accountant Review

Any change that affects:
- Tax calculation (brackets, rates, relief)
- Pension calculation (rates, base, ceiling)
- Overtime calculation (rates, limits)
- Leave calculation (days, pay)
- Severance calculation (formula, cap)
- ERCA report format
- Pension report format
- Any legal citation or proclamation reference

**Process:**
1. Document the change
2. Send to accountant with the relevant section of the Compliance Matrix
3. Get written confirmation (email, screenshot, voice note)
4. Record confirmation in the Decision Log
5. Update Compliance Matrix status

---

## What Requires Product Approval

Any change that affects:
- User-facing behavior
- Business rules
- Validation rules
- API contracts
- Permission model
- Notification behavior
- Error messages
- Report formats

**Process:**
1. Document the proposed change
2. Identify affected PRDs, rules, and catalogues
3. Submit to Product Owner
4. After approval, update all affected documents

---

## Document Change Rules

| Document | Change Authority |
|----------|-----------------|
| Operating Manual | Product Owner only |
| Principles | Product Owner only (frozen) |
| ADRs | Product Owner + Tech Lead |
| PRDs | Product Owner |
| Business Rule Catalogue | Product Owner (+ Accountant for legal rules) |
| Validation Catalogue | Product Owner |
| State Machine Catalogue | Product Owner |
| Other Catalogues | Tech Lead |
| Reference Documents | Any contributor |
| Decision Log | Any contributor |
| Open Questions | Any contributor |

---

## Breaking Change Protocol

When a change would break existing behavior:

1. **Document** the change in the Decision Log
2. **Assess** impact: which PRDs, rules, tests, APIs are affected?
3. **Create ADR** if architectural
4. **Get approval** from Product Owner
5. **Version** the API if external (ADR-018)
6. **Update** all affected documents
7. **Notify** the team
8. **Add migration** if database changes needed
9. **Update tests** to cover new behavior
10. **Verify** Compliance Matrix still accurate

---

## Weekly Governance Review

Every week, review:
- Open Questions (any blockers?)
- Decision Log (any decisions pending?)
- Compliance Matrix (any rules unverified?)
- Definition of Ready (any tasks ready to start?)
- Definition of Done (any PRs ready to merge?)

---

*Governance prevents drift. Drift is expensive.*
