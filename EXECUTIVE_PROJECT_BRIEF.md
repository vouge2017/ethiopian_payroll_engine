# Executive Project Brief
### Ethiopian Workforce Operating System
**Date:** 2026-07-28
**For:** Engineering team, stakeholders, partners

---

## What This Is

A payroll and workforce management platform for Ethiopian businesses. It handles everything from hiring an employee to passing a government audit — tax calculation, pension, payslips, bank files, ERCA filing, leave management, and employee self-service.

## Why It's Different

Ethiopian businesses currently run payroll in Excel. Excel has no audit trail, no tamper detection, no proof that numbers are correct. When ERCA audits them, they dig through WhatsApp messages and paper records.

This platform makes every number provable. Every tax calculation shows the formula, the inputs, the law citation, and who approved it. Once payroll is locked, it cannot be changed — corrections create new records, not edits.

## Architecture Principles

1. **Immutable after approval** — locked payroll cannot be modified
2. **Every number explainable** — formula, inputs, law, timestamp, approver
3. **Payments separate from payroll** — payment failures don't reopen payroll
4. **Corrections are additive** — never destructive, always auditable
5. **Configuration over customization** — change values, not code
6. **One employee, one lifecycle** — single source of truth

## MVP Scope

10 customer journeys, fully documented:

| Journey | PRD | Status |
|---------|-----|--------|
| Company Setup | PRD-00 | Spec complete |
| Hire Employee | PRD-01 | Spec complete |
| Prepare Payroll | PRD-02 | Spec complete, code exists |
| Approve & Lock | PRD-03 | Spec complete, code exists |
| Pay Employees | PRD-04 | Spec complete |
| Government Filing | PRD-05 | Spec complete, code exists |
| Generate Payslips | PRD-06 | Spec complete, code exists |
| Workforce Lifecycle | PRD-07 | Spec complete, code exists |
| Audit & Compliance | PRD-08 | Spec complete |
| Employee Self-Service | PRD-09 | Spec complete, code exists |

## What's Frozen

These documents are authoritative and should not be changed without explicit approval:

- Operating Manual
- Workforce Operating System Principles
- ADRs (22 architectural decisions)
- Business Rule Catalogue (116 rules)
- Validation Catalogue (74 rules)
- State Machine Catalogue (8 state machines)

## What's Still Evolving

- Experience Architecture (UX specs — not yet built)
- Pilot Package (onboarding guides — not yet built)
- Operational Documentation (deployment, monitoring — not yet built)

## Top Priorities

| Priority | Work | Status |
|----------|------|--------|
| P1 | Verify tax/pension math with real accountant | Verification package ready to send |
| P2 | Pilot with one real Ethiopian business | Outreach not yet started |
| P3 | Implement remaining PRD features | Spec complete, code partial |
| P4 | Build Experience Architecture | Not started |
| P5 | Operational documentation | Not started |

## Codebase

- **171 files**, 44 engine modules
- **28 database models**, 295 columns
- **640+ tests** passing
- **Flask + SQLAlchemy + PostgreSQL** (SQLite for dev)
- **Deployed on Render** (Docker)

## Key Files to Read First

| File | Purpose |
|------|---------|
| `OPERATING_MANUAL.md` | Start here — the handbook |
| `WORKFORCE_OPERATING_SYSTEM_PRINCIPLES.md` | 10 rules that govern everything |
| `FUNCTIONAL_SPECIFICATION.md` | How the product behaves |
| `PRD-TEMPLATE.md` | How PRDs are structured |
| `ENGINEERING_QUALITY_STANDARDS.md` | Coding standards |

---

*This document is the first thing every engineer should read.*
