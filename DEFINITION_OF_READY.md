# Definition of Ready
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**Purpose:** A task is not ready for development until all criteria are met

---

## Criteria

Before starting work on any feature, verify ALL of the following:

```
## Definition of Ready — {Feature Name}

### Requirements
- [ ] PRD exists and has been reviewed
- [ ] PRD has all 32 sections (or explicitly marks sections as N/A)
- [ ] Business rules identified (BR-xxx-xx references)
- [ ] Validation rules identified (VL-xxx-xx references)
- [ ] State machine transitions identified (SM-xxx)
- [ ] API contracts defined (section 14)
- [ ] Database changes defined (section 15)
- [ ] Acceptance tests defined (section 28)

### Dependencies
- [ ] All dependencies identified and available
- [ ] No blocking open questions (check OPEN_QUESTIONS.md)
- [ ] Required configuration settings identified (CONFIGURATION_CATALOGUE.md)
- [ ] Required evidence definitions identified (EVIDENCE_CATALOGUE.md)

### Design
- [ ] Screen specifications defined (section 8)
- [ ] Component specifications defined (section 9)
- [ ] Mobile behavior defined (if user-facing)
- [ ] Accessibility requirements defined (if user-facing)

### Permissions
- [ ] Permission matrix defined (section 12)
- [ ] Role requirements confirmed

### Testing
- [ ] Acceptance tests written (section 28)
- [ ] Edge cases identified (section 21)
- [ ] Test data available
```

---

## What Happens If Not Ready

If any criterion is missing:
1. Add the question to `OPEN_QUESTIONS.md`
2. Notify the product owner
3. Do NOT start development
4. Wait for the answer

---

*Developing without readiness is guessing. Guessing is expensive.*
