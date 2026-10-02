# Implementation Checklist
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**Purpose:** Every feature must complete this checklist before it's considered done.

---

## How to Use

Copy this checklist into every PR. Check each item. If any item is missing, the PR should not be merged.

---

```
## Implementation Checklist

### PRD Compliance
- [ ] PRD reviewed and understood
- [ ] All relevant business rules implemented (BR-xxx-xx)
- [ ] All relevant validation rules implemented (VL-xxx-xx)
- [ ] State machine transitions implemented (SM-xxx)
- [ ] API contracts match PRD section 14
- [ ] Database changes match PRD section 15
- [ ] Permissions match PRD section 12

### Code Quality
- [ ] Code follows Engineering Quality Standards
- [ ] Type hints on all function signatures
- [ ] Docstrings on all public functions
- [ ] No hardcoded values (use configuration)
- [ ] Tenant isolation enforced (TenantQuery)
- [ ] Error handling uses Error Catalogue codes

### Testing
- [ ] Unit tests for business rules
- [ ] Unit tests for validation rules
- [ ] Integration tests for API endpoints
- [ ] Edge cases tested
- [ ] All tests passing

### Audit & Evidence
- [ ] Audit events added for all state changes
- [ ] Evidence requirements met (if calculation-related)
- [ ] Hash chain maintained

### Analytics
- [ ] Analytics events added (if user-facing)
- [ ] Event names match Analytics Catalogue

### Security
- [ ] Authentication required on all endpoints
- [ ] Authorization checked (role-based)
- [ ] Tenant isolation verified
- [ ] No sensitive data in logs
- [ ] CSRF protection on mutation endpoints

### Documentation
- [ ] PRD updated if behavior changed
- [ ] Business Rule Catalogue updated if new rules added
- [ ] Validation Catalogue updated if new validations added
- [ ] API Catalogue updated if new endpoints added
- [ ] Error Catalogue updated if new errors added
- [ ] Configuration Catalogue updated if new settings added
```

---

## Quick Reference

| Category | Document to Check |
|----------|------------------|
| Business rules | `BUSINESS_RULE_CATALOGUE.md` |
| Validation rules | `VALIDATION_CATALOGUE.md` |
| State machines | `STATE_MACHINE_CATALOGUE.md` |
| API contracts | `API_CATALOGUE.md` |
| Error codes | `ERROR_CATALOGUE.md` |
| Permissions | `PERMISSION_CATALOGUE.md` |
| Audit events | PRD section 26 |
| Analytics events | PRD section 25 |
| Evidence | `EVIDENCE_CATALOGUE.md` |
| Coding standards | `ENGINEERING_QUALITY_STANDARDS.md` |

---

*Nothing is done without this checklist.*
