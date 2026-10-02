# Definition of Done
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**Purpose:** Nothing is done until every criterion is met — include in every PR

---

## Criteria

```
## Definition of Done — {Feature Name}

### Implementation
- [ ] All business rules implemented (BR-xxx-xx)
- [ ] All validation rules implemented (VL-xxx-xx)
- [ ] State machine transitions implemented (SM-xxx)
- [ ] API contracts match PRD section 14
- [ ] Database changes match PRD section 15
- [ ] Permissions match PRD section 12

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Acceptance tests pass (PRD section 28)
- [ ] Edge cases tested (PRD section 21)
- [ ] No test regressions

### Audit & Evidence
- [ ] Audit events added for state changes (PRD section 26)
- [ ] Evidence implemented (if calculation-related)
- [ ] Hash chain maintained

### Analytics
- [ ] Analytics events added (PRD section 25)

### Security
- [ ] Authentication on all endpoints
- [ ] Authorization checked
- [ ] Tenant isolation verified
- [ ] No sensitive data in logs
- [ ] CSRF on mutations

### Documentation
- [ ] PRD updated if behavior changed
- [ ] Catalogues updated if new rules/validations/APIs/errors added
- [ ] Configuration Catalogue updated if new settings added
- [ ] Implementation Checklist completed
```

---

## Quick Copy-Paste (for PRs)

```
## Definition of Done

- [ ] Business rules implemented
- [ ] Validation rules implemented
- [ ] State machine implemented
- [ ] API matches PRD
- [ ] Database matches PRD
- [ ] Permissions match PRD
- [ ] Tests pass (unit + integration + acceptance)
- [ ] Edge cases tested
- [ ] Audit events added
- [ ] Analytics added
- [ ] Security verified
- [ ] Documentation updated
```

---

*This checklist goes in every PR. No exceptions.*
