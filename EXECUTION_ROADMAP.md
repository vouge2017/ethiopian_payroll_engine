# Execution Roadmap
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**Status:** Active
**Blueprint:** CUSTOMER_JOURNEY_BLUEPRINT.md v2.0 (frozen)

---

## Rule: No more blueprint expansion

The blueprint is production-grade. All future work converts it into artifacts that teams can use.

---

## Phases

| Phase | Deliverable | Priority | Outcome |
|-------|------------|----------|---------|
| 1 | Journey PRDs (10) | 🔴 Highest | Engineering knows exactly what to build |
| 2 | ADRs (Trust/Evidence/Calculation) | 🔴 Highest | Consistent architecture and technical decisions |
| 3 | Accountant Verification Package | 🔴 Highest | Validate Ethiopian compliance before pilot |
| 4 | Pilot Playbook | 🟠 High | Successful onboarding of first customers |
| 5 | UX/UI Specifications | 🟠 High | Designers and frontend work from one source |
| 6 | Test & Acceptance Suite | 🟠 High | QA validates business outcomes, not just code |
| 7 | Sales & Demo Kit | 🟡 Medium | Support pilot acquisition and investor demos |

---

## PRD Template

Every PRD follows this structure:

```
Journey ID
Business Objective
Customer Problem
Primary Actor
Supporting Actors
Trigger
Main Flow
Alternative Flows
Business Rules
Validation Rules
Trust Moments
Evidence Requirements
Notifications
Automation Rules
Permissions
Success Metrics
Acceptance Criteria
Edge Cases
Out of Scope
Dependencies
Related ADRs
```

---

## PRD List

| ID | Journey | Status |
|----|---------|--------|
| PRD-00 | Company Setup & Excel Migration | ✅ Complete |
| PRD-01 | Hire Employee | ✅ Complete |
| PRD-02 | Prepare Payroll | ✅ Complete |
| PRD-03 | Approve & Lock Payroll | Pending |
| PRD-04 | Pay Employees | Pending |
| PRD-05 | Government Filing | Pending |
| PRD-06 | Employee Payslip | Pending |
| PRD-07 | Employee Exit | Pending |
| PRD-08 | Government Audit | Pending |
| PRD-09 | Manager & HR Lifecycle | Pending |

---

## ADR List

| ID | Topic | Status |
|----|-------|--------|
| ADR-001 | Trust Architecture | Pending |
| ADR-002 | Evidence Layer | Pending |
| ADR-003 | Crosscheck Engine | Pending |
| ADR-004 | Payroll Lock & Snapshot | Pending |
| ADR-005 | Explain Panel | Pending |
| ADR-006 | Trust Score | Pending |
| ADR-007 | Audit Trail | Pending |
| ADR-008 | Industry Template Engine | Pending |
| ADR-009 | Automation Engine | Pending |
| ADR-010 | AI Explanation Layer | Pending |

---

## Requirements Traceability Matrix

| Journey | PRD | ADRs | UI | Tests | Status |
|---------|-----|------|----|-------|--------|
| J0 | PRD-00 | ADR-001, 002 | ⏳ | ⏳ | PRD done |
| J1 | PRD-01 | ADR-003 | ⏳ | ⏳ | PRD done |
| J2 | PRD-02 | ADR-003, 004, 005 | ⏳ | ⏳ | PRD done |
| J3 | PRD-03 | ADR-004, 005, 006 | ⏳ | ⏳ | Pending |
| J4 | PRD-04 | ADR-003 | ⏳ | ⏳ | Pending |
| J5 | PRD-05 | ADR-003, 007 | ⏳ | ⏳ | Pending |
| J6 | PRD-06 | ADR-005, 007 | ⏳ | ⏳ | Pending |
| J7 | PRD-07 | ADR-004 | ⏳ | ⏳ | Pending |
| J8 | PRD-08 | ADR-007 | ⏳ | ⏳ | Pending |
| J9 | PRD-09 | ADR-009 | ⏳ | ⏳ | Pending |

---

## 8-Week Execution Roadmap

| Week | Goal |
|------|------|
| 1 | Complete all 10 PRDs | ⏳ In progress (PRD-00, PRD-01 done) |
| 2 | Complete all core ADRs | Pending |
| 3 | UX specifications for all journeys | Pending |
| 4 | Accountant verification and revisions | Pending |
| 5 | Acceptance tests and QA scenarios | Pending |
| 6 | Pilot playbook and onboarding assets | Pending |
| 7 | Internal dry run with a complete payroll cycle | Pending |
| 8 | Launch pilot with selected Ethiopian companies | Pending |

---

## Foundation Documents (completed before PRD-02)

| Document | Status | Purpose |
|----------|--------|---------|
| PRD-TEMPLATE.md | ✅ Complete | 32-section template for all PRDs |
| DATA_MODEL.md | ✅ Complete | Entities, relationships, lifecycle states, naming conventions |
| BACKEND_ARCHITECTURE.md | ✅ Complete | REST conventions, auth, errors, performance, events |
| FRONTEND_DESIGN_SYSTEM.md | ✅ Complete | Screens, components, states, responsive, accessibility |
| ENGINEERING_QUALITY_STANDARDS.md | ✅ Complete | Security, testing, analytics, logging, rollout, definition of done |

---

*Execution started: 2026-07-28*
*First artifacts: PRD-00, PRD-01*
