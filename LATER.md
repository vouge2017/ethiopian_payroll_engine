# LATER — EthioPayroll Roadmap Beyond Pilot

**Date:** 2026-09-14
**Status:** Frozen — do not touch until one real pilot company is running in shadow mode against Tigist's actual payroll for at least one full month.

**Purpose:** This file exists so that when someone says "should we build X?" the answer is "check LATER.md — if it's here, it's not for now." This prevents scope creep from competing with the three things that actually matter.

**Entry criterion to reopen any item below:** One pilot company has run a full payroll cycle in shadow mode (our system calculates, Tigist's Excel does the real thing, we compare), AND the accountant has signed off on our calculations, AND we've sent at least one real bank file and one real ERCA filing.

---

## Tier 3 — Unlock the Ecosystem (after pilot sign-off)

### 3.1 OpenAPI/Swagger Documentation
**What:** Document the existing 17 REST API endpoints with OpenAPI spec. Add missing endpoints (payroll creation via API, leave management API).
**Why it matters:** Fintechs and integration partners cannot build on top of us without docs. Banks won't even have a conversation without seeing the API surface.
**What it unlocks:** Third-party integrations, accountant tool-building, bank partnership conversations.
**Replaces:** Manual integration work for every new partner.

### 3.2 Employee-Consent Data Sharing API
**What:** An API endpoint that, with the employee's explicit consent, returns verified employment + salary history to a third party (lender, fintech, verification service).
**Why it matters:** Digital lenders in Ethiopia need payroll-backed credit scoring. Telebirr and other fintechs want verified employment data. This is the door to the financial ecosystem.
**What it unlocks:** Payroll-backed lending, instant employment verification, fintech partnerships.
**Replaces:** Manual "send me your payslips" for every loan application.

### 3.3 Bank API Integration Layer
**What:** A webhook-based callback system where the bank acknowledges receipt of a payout file and reports status (accepted, rejected, processed, failed) back to EthioPayroll.
**Why it matters:** Today: employer uploads file → waits → manually checks status. Tomorrow: system sends file → bank callback → automatic status update → employee gets WhatsApp when money lands.
**What it unlocks:** Real-time payment tracking, automatic retry of failed payments, "money moved" notifications.
**Replaces:** Manual bank portal checking.

### 3.4 Payment Retry for Failed Transactions
**What:** "Retry failed" button on payroll run that regenerates a file containing only the employees whose payments failed, with the original error reasons visible.
**Why it matters:** When 10 of 50 payments fail, nobody wants to manually filter and re-create the file.
**What it unlocks:** Faster payment recovery, less manual work during month-end.
**Replaces:** Manual filtering + re-generation.

### 3.5 Cash Flow Pre-Flight Check
**What:** Before approving payroll, show total payroll cost vs. bank balance (manually entered or API-connected). Warn if short. Suggest staggering.
**Why it matters:** Approving payroll you can't afford is worse than not having a payroll system.
**What it unlocks:** Financial safety net for business owners.
**Replaces:** "Oh no, I approved payroll and now I can't pay everyone."

---

## Tier 4 — Build the Moat (after successful pilot)

### 4.1 AI Input Agent — Excel Scan + Auto-Validate
**What:** When a user uploads an Excel spreadsheet during onboarding, the system reads it, maps columns to fields, extracts employee data, validates TINs and bank accounts, flags issues — all before the human sees it.
**Why it matters:** The #1 friction in onboarding is data entry. Remove it.
**What it unlocks:** 15-minute onboarding becomes 5-minute onboarding.
**Replaces:** Manual copy-paste from Excel.

### 4.2 Smart Filing Assistant
**What:** Auto-generate ERCA and pension reports, remind the user before deadlines, provide one-click "mark as filed" with confirmation number entry.
**Why it matters:** Filing is the #1 accountant pain point. Make it effortless.
**What it unlocks:** Accountants trust the system for compliance, not just calculations.
**Replaces:** Manual report generation + manual filing tracking.

### 4.3 Compliance Monitoring Agent
**What:** Monitor ERCA announcements and Ethiopian proclamation updates. When a rule changes (tax bracket, pension rate, deadline), flag it to the system admin and suggest an update.
**Why it matters:** If ERCA changes a bracket and our system doesn't know, every payroll that month is wrong.
**What it unlocks:** Automatic rule updates, reduced compliance risk.
**Replaces:** "Did you hear ERCA changed something?" panic.

### 4.4 Attendance → Payroll Pipeline
**What:** Upload attendance CSV from biometric device → system auto-matches employees → calculates overtime → includes in payroll draft.
**Why it matters:** Attendance-to-payroll matching is currently manual and error-prone.
**What it unlocks:** End-to-end payroll without manual attendance handling.
**Replaces:** Manual attendance-to-employee matching.

### 4.5 Manager Approval Workflow
**What:** Overtime entries, leave requests, profile changes all route to the relevant manager for approval before they affect payroll.
**Why it matters:** HR shouldn't be the gatekeeper for every overtime request. Managers should approve their own team's overtime.
**What it unlocks:** Distributed approval authority, less HR bottleneck.
**Replaces:** "HR, can you approve Bob's overtime?" every month.

### 4.6 Full Employee Lifecycle View
**What:** One timeline per employee showing: hire date, salary changes, department transfers, leave taken, overtime, warnings, promotions, termination.
**Why it matters:** Reconstructing an employee's history today requires checking 4+ different records.
**What it unlocks:** Instant employee history for audits, disputes, loan applications.
**Replaces:** Piecing together data from payroll runs, leave records, audit logs.

---

## Tier 5 — Beyond the Platform (year 2+)

*These are not on the table until EthioPayroll is the de facto payroll system for Ethiopian SMEs. Do not even read this section until the pilot is running and the accountant has signed off.*

### 5.1 Accountant Workspace — Multi-Company Dashboard
**What:** Accountant role sees all linked companies, batch-files ERCA for all of them, sees which clients are late on deadlines, gets a compliance overview.
**Why it matters:** 1 accountant serves 50 SMEs. Win the accountant, win 50 businesses.
**What it unlocks:** Distribution channel. Accountants bring clients.

### 5.2 Third-Party OAuth2 Integrations
**What:** Let accounting software (Sage, Xero equivalents), HR tools, and banking apps connect to EthioPayroll via OAuth2.
**Why it matters:** Ethiopian businesses use multiple tools. They want them to talk to each other.
**What it unlocks:** Integration ecosystem, stickiness, platform value.

### 5.3 White-Label for Banks
**What:** Banks offer "powered by EthioPayroll" to their SME clients. The bank gets the payroll data, the SME gets payroll software, EthioPayroll gets distribution.
**Why it matters:** Banks have the SME relationships. We have the payroll engine. Together = distribution at scale.
**What it unlocks:** Hundreds of companies onboarded through bank partnerships.

### 5.4 Cash Flow Forecasting + Anomaly Detection
**What:** Based on payroll history, forecast next month's cash need. Detect anomalies: "Employee X's salary changed 300% this month — verify before approving."
**Why it matters:** Prevents errors before they happen. Helps business owners plan.
**What it unlocks:** Proactive financial management, fewer payroll errors.

### 5.5 Multi-Country Expansion (Kenya, Rwanda, Uganda, Tanzania)
**What:** Same trust architecture (hash chain, explainable calculations, configurable rules, audit trail) applied to a new country's tax, pension, and labor laws.
**Why it matters:** The architecture is country-agnostic. The rules are country-specific. Swap the rules, keep the engine.
**What it unlocks:** Regional presence, larger market, investor appeal.

### 5.6 Payroll-Backed Lending Market
**What:** With employee consent, EthioPayroll becomes the employment + income verification layer for the entire Ethiopian fintech lending market. Any lender queries the API, gets verified data, makes a decision.
**Why it matters:** Ethiopia has a huge informal workforce with no credit history. Payroll data is the bridge to formal credit.
**What it unlocks:** Financial inclusion at scale, new revenue stream (per-verification fee), strategic value.

---

## What Is NOT In This File (and never will be)

- **Multi-country expansion before Ethiopia works.** One country, done right, is worth ten half-built.
- **White-label before direct customers.** No clients yet. Build for Tigist first.
- **Push notifications before WhatsApp.** Ethiopian users are on WhatsApp. Push is noise.
- **Full offline mode.** Hawassa has 4G. Auto-save covers 90% of the risk.
- **Redis/advanced infra before scale.** SQLite→Postgres is done. Scale infra when you have scale.
- **Anything that doesn't remove Excel from someone's workflow.** If they still need Excel after using our feature, we failed.

---

## How to Use This File

1. **Before starting any new feature:** Check if it's in this file. If yes → it's not for now. If no → ask "does this block the pilot or the accountant verification?" If no → don't build it.
2. **When the pilot succeeds:** Pick ONE item from Tier 3. Build it. Ship it. Then pick the next.
3. **When an investor or partner asks for something advanced:** Point them to this file. "We have a plan. It's sequenced. We're on step 1."
4. **When you feel the urge to build something cool:** Read Tier 5. Then close the file. You're not there yet.

---

*This file is frozen. It changes only when the pilot is live and the accountant has signed off. Anyone can suggest additions, but nothing gets removed or prioritized without the pilot success criterion being met.*
