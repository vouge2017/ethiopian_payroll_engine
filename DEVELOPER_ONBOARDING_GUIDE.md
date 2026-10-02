# Developer Onboarding Guide
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**For:** New engineers joining the project

---

## Day 1: Read These (in order)

| # | File | Time | Why |
|---|------|------|-----|
| 1 | `EXECUTIVE_PROJECT_BRIEF.md` | 10 min | Understand the product |
| 2 | `OPERATING_MANUAL.md` | 20 min | The handbook — vision, principles, journey map |
| 3 | `WORKFORCE_OPERATING_SYSTEM_PRINCIPLES.md` | 5 min | 10 rules that govern everything |
| 4 | `FUNCTIONAL_SPECIFICATION.md` | 30 min | How the product actually behaves |
| 5 | `PRD-TEMPLATE.md` | 5 min | How PRDs are structured (32 sections) |

**Total: ~70 minutes.** After this, you understand the product.

## Day 2: Understand the Architecture

| # | File | Time | Why |
|---|------|------|-----|
| 6 | `ARCHITECTURE_DECISIONS.md` | 30 min | 22 decisions — why things are the way they are |
| 7 | `DATA_MODEL.md` | 15 min | Database entities and relationships |
| 8 | `BACKEND_ARCHITECTURE.md` | 10 min | API standards, error model, conventions |
| 9 | `ENGINEERING_QUALITY_STANDARDS.md` | 10 min | Coding standards, testing strategy |
| 10 | `FRONTEND_DESIGN_SYSTEM.md` | 10 min | UI components, patterns, responsive design |

## Day 3: Understand the Rules

| # | File | Time | Why |
|---|------|------|-----|
| 11 | `BUSINESS_RULE_CATALOGUE.md` | 15 min | 116 business rules — the law of the system |
| 12 | `VALIDATION_CATALOGUE.md` | 10 min | 74 validation rules |
| 13 | `STATE_MACHINE_CATALOGUE.md` | 10 min | 8 state machines — lifecycles |
| 14 | `PERMISSION_CATALOGUE.md` | 5 min | RBAC matrix |
| 15 | `API_CATALOGUE.md` | 10 min | All endpoints |
| 16 | `ERROR_CATALOGUE.md` | 10 min | All error codes |

## Day 4: Your First Task

1. Pick a PRD for the feature you're implementing
2. Read the full PRD (all 32 sections)
3. Check the `IMPLEMENTATION_CHECKLIST.md` — every item must be done
4. Check the `OPEN_QUESTIONS.md` — are there blockers?
5. Start coding

## How Documents Are Organized

```
Foundation (frozen — don't change without approval)
├── Operating Manual
├── Principles
├── ADRs
└── Customer Journey Blueprint

Catalogues (frozen — don't change without approval)
├── Business Rules
├── Validation Rules
├── State Machines
├── Notifications
├── Analytics
├── Evidence
├── Payment
├── Permissions
├── APIs
└── Errors

PRDs (frozen after approval — changes need product approval)
├── PRD-00 through PRD-09
└── PRD-TEMPLATE

Reference (living documents — update as needed)
├── Functional Specification
├── Configuration Catalogue
├── Decision Flow Catalogue
├── Compliance Matrix
├── Traceability Matrix
├── Decision Matrix
├── Developer Playbook
└── Domain Model
```

## How to Add a New Feature

1. **Read the relevant PRD** — it defines what to build
2. **Check the Business Rule Catalogue** — it defines the rules
3. **Check the Validation Catalogue** — it defines what to validate
4. **Check the State Machine Catalogue** — it defines lifecycles
5. **Check the API Catalogue** — it defines endpoints
6. **Implement** — follow Engineering Quality Standards
7. **Test** — write tests for every rule and validation
8. **Document** — update relevant catalogues if you added new rules

## How to Submit Changes

1. Create a branch from `main`
2. Implement the feature
3. Write tests (unit + integration)
4. Update documentation if needed
5. Fill out the PR checklist (Definition of Done)
6. Submit PR for review

## Coding Standards (Quick Reference)

- **Python 3.11+**, Flask, SQLAlchemy
- **Type hints** on all function signatures
- **Docstrings** on all public functions
- **Tests** for every business rule and validation
- **Tenant isolation** — every query must include `company_id`
- **Audit logging** — every state change must create an AuditLog entry
- **Error handling** — use error codes from `ERROR_CATALOGUE.md`

## Key Commands

```bash
# Run the app
python run.py

# Run tests
python -m pytest

# Database migration
flask db migrate -m "description"
flask db upgrade

# Seed demo data
python seed_staging.py
```

---

*This guide gets you productive in 3 days. After that, the Developer Playbook has detailed how-to guides for everything else.*
