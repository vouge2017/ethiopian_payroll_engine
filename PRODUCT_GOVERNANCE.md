# Product Governance Framework
### Ethiopian Payroll & Workforce Platform
**Effective: 2026-07-28**

---

## The Shift

This project is no longer a software project.

It is a product company.

Engineering proved we can build payroll software.
Now we prove that Ethiopian businesses trust it enough to replace Excel.

---

## Layer Framework (Not Deletion — Prioritization)

The 50% challenge was misunderstood. It is a thinking exercise, not a development task.

The question is: **"If we had to launch in 60 days, what would we keep?"**

The answer reveals three layers:

### Layer 1 — Core Product (Must Never Fail)

These determine whether payroll can run this month.

- Employee management (name, salary, department, bank, TIN)
- Payroll calculation (tax, pension, net pay)
- Leave management (annual, sick, maternity, unpaid — directly affects payroll)
- Overtime (manufacturing, hotels, construction, hospitals need this)
- ERCA report generation
- Bank file generation
- Payroll approval workflow
- Audit trail

**Rule:** Freeze nothing in Layer 1. Fix, improve, and verify continuously.

### Layer 2 — Valuable Features (Important but not payroll-blocking)

- Attendance import
- Accounting export
- Reports and analytics
- Employee portal improvements
- Loan tracking
- Severance calculation
- Compliance deadlines
- Holiday calendar

**Rule:** Freeze until Layer 1 is trusted by customers. Then unfreeze based on customer feedback.

### Layer 3 — Scale Features (Help later, not now)

- API
- AI experiments
- MFA
- Google OAuth
- Scheduled reports
- PWA improvements
- Multi-company management
- Staging environment

**Rule:** Freeze completely. These matter for scale, not for trust.

### Key Insight: MVP Depends on Target Customer

If targeting **schools, retail, professional services** → overtime can wait.
If targeting **factories, construction, hospitals** → overtime is core.

The MVP is not universal. It depends on which industry we pilot with first.

---

## Governance Boards

These are not meetings. They are decision-making bodies that protect the product.

---

### Board 1: Compliance Review Board

**Members:**
- Accountant
- Auditor
- Tax Expert
- Labor Law Expert

**Mission:** Can this payroll legally be trusted?

**NOT** to test software. To verify that every number that touches money is legally defensible.

**Every two weeks they answer:**
- Is tax correct?
- Is pension correct?
- Is leave correct?
- Is severance correct?
- Is ERCA report accepted?
- Is MOLSA report correct?
- Can an auditor defend this payroll?

**Output:** Compliance Score (0–100%)

**Example report:**
| Component | Status |
|-----------|--------|
| Payroll Tax | ✅ Verified |
| Pension | ⚠️ Needs correction |
| Overtime | ✅ Verified |
| Leave | ⏳ Waiting legal clarification |
| ERCA | ✅ Approved |
| **Overall** | **82%** |

**Authority:** Engineering cannot override them. If they say no, the feature goes back.

---

### Board 2: Customer Advisory Board

**Members (10 customers):**
- 3 accountants
- 2 HR managers
- 2 business owners
- 2 payroll officers
- 1 finance manager

**Mission:** Destroy assumptions.

They don't write code. They use the product.

**Every month they answer:**
- "This feature saved me time."
- "This feature confused me."
- "I never use this."
- "I still use Excel because…"
- "I still calculate manually because…"
- "This workflow is wrong."
- "You forgot this report."
- "Why can't I…"

**Their feedback decides the roadmap. Not engineering.**

**KPI:** How many hours did we save? Not how many features shipped.

---

### Board 3: Product Steering Committee

**Members:**
- Product Director
- Technical Lead
- UX Lead
- Implementation Lead
- Customer Success Lead
- Compliance Lead

**Mission:** Make product decisions. Own the roadmap.

**Every two weeks, agenda:**
- What did customers say?
- What compliance issues remain?
- What bugs block pilots?
- What should be removed?
- What should be delayed?
- What gets built next?

**Authority:** This board owns the roadmap.

---

### Board 4: Implementation & Operations Board

**Members:**
- Payroll implementation specialist
- Customer support
- Trainer
- Sales representative
- Onboarding specialist

**Mission:** Can customers successfully adopt and operate this without frustration?

**They ask:**
- Can a new company start using this in one day?
- Where do customers get stuck?
- Which screens require training?
- Which Excel imports fail?
- Which questions are asked every week?

**Why this matters:** Engineers almost never see these problems. They are often the biggest barriers to adoption.

---

## How the Boards Work Together

```
  Customers
      │
      ▼
  Customer Advisory Board
      │
      │ "This workflow is painful."
      ▼
  Product Steering Committee
      │
      │ "Yes, build this improvement."
      ▼
  Engineering Team
      │
      │ Feature implemented
      ▼
  Compliance Review Board
      │
      │ "Legally correct?" Yes / No
      ▼
  Pilot Customers
      │
      │ Feedback goes back
      ▼
  (cycle repeats)
```

**The continuous improvement loop:**
1. Customers identify problems
2. Leadership decides priorities
3. Engineering builds solutions
4. Compliance verifies legality and correctness
5. Pilot customers validate that the solution actually works
6. The cycle repeats

---

## The Four Questions

Every meeting, every sprint, every feature must answer one of four questions:

1. **Did it solve a real customer problem?** → Customer Advisory Board
2. **Is it legally and professionally correct?** → Compliance Review Board
3. **Is it the highest-priority thing to build now?** → Product Steering Committee
4. **Can customers successfully adopt and operate it without frustration?** → Implementation & Operations Board

If all four groups answer "yes," the product is ready to earn trust and grow.

---

## Current State (2026-07-28)

| Board | Status | Next Action |
|-------|--------|-------------|
| Compliance Review Board | Not formed | Identify members. Send VERIFICATION_PACKAGE.md. |
| Customer Advisory Board | Not formed | Begin customer discovery (Workstream B). |
| Product Steering Committee | Active (implicit) | Formalize bi-weekly cadence. |
| Implementation & Operations Board | Not formed | Identify pilot implementation specialist. |

---

*Framework captured from Product Director directive, 2026-07-28.*
