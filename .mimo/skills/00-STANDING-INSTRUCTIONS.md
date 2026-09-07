# EthioPayroll — Standing Instructions

Read this file at the start of every session.
Follow these instructions for every task.

---

## THE RULES WE ESTABLISHED

These are non-negotiable. Every calculation must
follow these exactly.

### Tax Brackets (Proclamation 1395/2025)

| Monthly Income (ETB) | Rate |
|---|---|
| 0 — 2,000 | 0% |
| 2,001 — 4,000 | 15% |
| 4,001 — 7,000 | 20% |
| 7,001 — 10,000 | 25% |
| 10,001 — 14,000 | 30% |
| Over 14,000 | 35% |

### Pension

- Employee: 7% of basic salary
- Employer: 11% of basic salary
- Foreign nationals: EXEMPT entirely
- NO CAP — Proclamation 1268/2022 has no maximum cap. Do not add one.

### Deduction Order (never change this)

1. Gross salary
2. Subtract pension (Ethiopian citizens only)
3. Calculate PAYE on remaining
4. Subtract PAYE
5. Subtract other deductions
6. = Net pay

### Leave

- Annual: 16 days after 1 year, +1 per 2 years
- Sick: Full pay month 1, half pay months 2-3, no pay months 4-6
- Maternity: 120 days, full pay
- Paternity: 3 days, full pay

### Overtime Rates

- Weekday (6am-10pm): 1.25x
- Night (10pm-6am): 1.5x
- Holiday: 2.0x
- Rest day: 2.5x
- Limit: 20 hours/month, 100 hours/year

### Severance

- 30 days per year of service, capped at 12 months
- Eligible: redundancy, mutual agreement, unfair dismissal, employer bankruptcy,
  employer death, employee death at work, physical incapacity, sexual harassment
- Not eligible: resignation, termination for cause

### Verification Test (run after EVERY change)

If this produces different numbers, something is wrong. Stop and investigate.

---

## BEFORE CHANGING WORKING CODE

If the code produces correct numbers and someone says "this is wrong":

1. **Ask for the primary legal source** — the actual proclamation text, not a blog,
   not a compliance guide, not a payroll aggregator's documentation.
2. **If they can't cite the proclamation article/section, don't change the code.**
3. **If they cite a secondary source (HiveDesk, Deel, Multiplier, etc.), verify
   against the actual proclamation before changing anything.**
4. **If the code passes all verification tests, it's probably right.** The tests
   are based on the law. Changing the code to match a blog post breaks the law.

NEVER change a working calculation based on:
- A blog post
- A payroll aggregator's documentation
- A "compliance guide" from a third-party website
- Someone saying "I think the law says..."

ALWAYS change a calculation when:
- The actual proclamation text says something different
- An Ethiopian tax lawyer or certified accountant confirms it's wrong
- A verification test fails against the legal source

---

## SIX CHECKS (apply before declaring ANYTHING done)

### CHECK 1: Security
- Could Company A see Company B's data?
- Is tenant_id in every query?
- Are salary/TIN/bank details encrypted?
- Is any secret hardcoded or logged?

### CHECK 2: Compliance
- Does this match Ethiopian law?
- Can I cite the legal source?
- What happens with zero/negative/missing input?
- Is deduction order enforced by the function itself?

### CHECK 3: QA
- Have edge cases been tested?
- Zero, negative, missing, duplicate, boundary?
- Is this module wired into a real flow or orphaned?

### CHECK 4: Data Safety
- If server restarts, is data lost?
- Is everything in the database (not files/sessions)?
- Soft deletes only for payroll records?

### CHECK 5: Product Value
- Does this help a real Ethiopian SME owner?
- Is this the simplest version that works?
- Does it serve Smart/Empowering/Flexible/Explainable/Discreet?

### CHECK 6: Communication
- Never say "works" without showing test output
- Separate "code exists" from "feature is usable"
- If you cut corners, say so explicitly

---

## PRIORITY FILTER

1. Anything that could LOSE or LEAK data
2. Anything that silently produces a WRONG NUMBER
3. The single highest-VALUE missing feature
4. Polish and nice-to-haves

Never skip 1 or 2 to work on 3 or 4.

---

## FIVE CORE PRINCIPLES

Every feature must serve at least one:

1. **SMART** — Prevents mistakes, learns patterns
2. **EMPOWERING** — Makes users more capable
3. **FLEXIBLE** — Adapts to each business
4. **EXPLAINABLE** — Every number has a reason
5. **DISCREET** — Sensitive data protected

---

## COMMIT AND PUSH RULE

After completing ANY fix or feature:
1. git add the specific files changed
2. git commit with descriptive message
3. git push IMMEDIATELY
4. Verify: git log --oneline -1
5. If push fails, STOP and tell me.
   Do not continue until push works.

NEVER report a fix as "done" until it's
pushed to GitHub. Code that isn't pushed
does not exist.

---

## SESSION START RULE

At the start of every session:
1. python3 verify_status.py
2. pytest -q
3. git log --oneline -10
4. Read PROGRESS_TRACKER.md

NEVER generate status from memory or from
stale documentation.

---

## SESSION END RULE

Before ending any session:
1. git status (check uncommitted files)
2. pytest -q (check tests pass)
3. python3 verify_status.py (check everything)
4. Update PROGRESS_TRACKER.md
5. git add -A && git push

If anything is uncommitted, commit and push
BEFORE ending.

---

## FEATURE COMPLETION RULE

A feature is NOT done until:
 1. The calculation module exists and passes tests
 2. A route exists in main.py that calls it
 3. A template exists that shows the result
 4. A user can access it through the web UI
 5. An E2E test proves the full flow works

A module without a route is a library, not
a feature. A route without a template is an
API, not a product. A template without user
access is a mockup, not a feature.

NEVER report a feature as "done" until all
five conditions are met.

---

## SCOPE CONTROL — What NOT to Build (and why)

When someone suggests a new feature, check this list first.
If it's listed here, the answer is already decided.

### Celery/RQ Background Tasks
WHY NOT: Adds Redis dependency, worker process, task failure handling.
For a 50-employee company, CSV processing takes 2 seconds.
Not worth the complexity. Revisit at 1000+ employees.

### Credit/Sales Ledger (Khatabook-style)
WHY NOT: Completely different product. Payroll is hard enough.
Do not expand scope until payroll is solid and has paying customers.

### Offline-First Architecture
WHY NOT: Requires fundamentally different architecture (local-first data,
sync engines, conflict resolution). Not a feature you add — it's a
design decision at the start. We chose web-first.

### Complex RBAC with Custom Roles
WHY NOT: Three roles (owner/accountant/employee) cover every Ethiopian
SME for MVP. Custom roles add UI complexity and testing burden.
Add when a real customer asks for it.

### Multi-Level Approval Chains
WHY NOT: Ethiopian SMEs don't have 3 levels of management.
The owner approves. That's it.

### Email-Based Notifications
WHY NOT: Most Ethiopian workers don't have email.
Building Telegram OTP instead.

### SMS OTP (as primary)
WHY NOT: SMS is expensive in Ethiopia. Telegram is free and widely used.
SMS becomes a fallback when we have revenue.

### Auto-Detect Night/Holiday Overtime
WHY NOT: Requires time tracking and Ethiopian holiday calendar.
Manual selection by accountant is simpler and correct.

### CI/CD Pipeline
WHY NOT: Manual deployment is fine for a team of one.
Add when there are multiple human developers.

### Sign-Off Sheets Per Task/PR
WHY NOT: One developer + one AI agent. Session end rules
(pytest + verify + push) provide equivalent verification.

### General Rule
If a feature doesn't serve at least one of the five principles
(SMART, EMPOWERING, FLEXIBLE, EXPLAINABLE, DISCREET),
don't build it. When in doubt, ask the owner.
