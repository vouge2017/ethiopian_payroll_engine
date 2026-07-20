# EthioPayroll — Diagnostic Questionnaire Answers

**Date:** 2026-07-20
**Prepared by:** AI agent (codebase analysis + deployment evidence)
**Based on:** Code inspection, git history, Render deployment logs, test suite

---

## Mobile (Current: 5/10)

### Q1: What devices/browsers are you testing on?

**No real device testing has occurred.** All mobile testing was done via browser DevTools responsive mode (Chrome desktop emulating 360px/768px viewports). There is no evidence of testing on actual Android phones, iPhones, or mobile browsers.

### Q2: Which specific screens overflow?

Based on `responsive.css` (line 97: `min-width: 500px` on tables):

- **Employee list table** — overflow-x scroll wrapper exists but table min-width is 500px
- **Payslip table** — same treatment
- **Audit log table** — wrapped in `table-responsive`
- **Dashboard** — cards stack vertically, no overflow issues
- **Quick Start paste zone** — drag-and-drop doesn't work on mobile (no touch event handling)

The `responsive.css` file header literally says: *"Usable on a phone" not "beautiful on a phone."*

### Q3: Hamburger menu?

**Yes.** The responsive CSS converts the sidebar into a fixed top navbar with a hamburger toggle at `max-width: 767.98px`. The sidebar nav collapses/shows via `.show` class. There's a `sidebar-toggle` button with `☰` icon.

### Q4: CSS framework?

**Bootstrap 5.3.2** via CDN, plus **Bootstrap Icons 1.11.1** via CDN. Custom `responsive.css` on top. No Tailwind, no custom framework.

### Q5: Worst mobile complaint?

No real users yet — but from code inspection, the known issues are:
1. Tables overflow on screens < 500px (horizontal scroll required)
2. Sidebar is clunky — 10+ items in the nav, even when collapsed
3. Drag-and-drop Excel paste doesn't work on touch devices
4. No PWA support — no service worker, no manifest, no offline capability

---

## Infrastructure (Current: "Not Ready")

### Q6: Where is this deployed?

**Render.com** — free tier. One web service (`ethiopian-payroll-web`) + one managed PostgreSQL (`ethiopian-payroll-db`, starter plan).

- Service ID: `srv-d91t12u7r5hc738taug0`
- URL: `https://ethiopian-payroll-engine.onrender.com`
- Auto-deploy from `main` branch on GitHub
- Docker-based build (multi-stage Dockerfile)
- Free instance spins down with inactivity (~50s cold start)

### Q7: Staging environment?

**No.** Single environment. No staging, no preview deploys. Tests in production.

### Q8: Last backup restore test?

**Never tested against the live Render database.** A `verify_backup.py` script exists and was tested against SQLite only. The `--pg` flag exists for PostgreSQL testing but requires a `TEST_DATABASE_URL` which has never been set.

### Q9: Automated backups?

**Render manages this.** The starter plan includes automated daily backups with point-in-time recovery. The backup configuration is at Render Dashboard → Postgres instance → Backups tab. It has never been verified by the team.

### Q10: Recovery time if server dies today?

**Unknown.** Theoretically: Render auto-restarts the web service within minutes. Database restore from Render backup would depend on the backup age. No runbook exists. No documented recovery procedure.

### Q11: Docker or bare-metal?

**Docker.** Multi-stage Dockerfile (builder + runtime). Python 3.11-slim base. The `render.yaml` blueprint specifies `runtime: docker`.

---

## Regulatory / Tax Brackets (Current: "Unverified")

### Q12: Which proclamation is referenced?

**Proclamation No. 1395/2025** (Income Tax Amendment). Referenced in:

- `payroll_engine/tax.py` line 4: *"Source: Ethiopian Income Tax (Amendment) Proclamation No. 1395/2025, Article 36(1)"*
- `payroll_engine/i18n.py` line 155: Amharic translation references 1395/2025
- `payroll_engine/i18n_om.py` line 152: Afaan Oromoo translation references 1395/2025
- `payroll_engine/payroll.py` line 361: *"Progressive brackets (Proclamation 1395/2025)"*

Additional proclamations referenced:
- **No. 1268/2022** — Pension (Private Organizations Employees Social Security)
- **No. 1156/2019** — Labor (overtime, severance, leave)
- **No. 715/2011** — Pension (repealed, replaced by 1268/2022)

### Q13: Current bracket thresholds?

From `tax.py` `DEFAULT_BRACKETS`:

| Upper Limit (ETB) | Rate |
|---|---|
| 2,000 | 0% |
| 4,000 | 15% |
| 7,000 | 20% |
| 10,000 | 25% |
| 14,000 | 30% |
| ∞ | 35% |

Personal relief: **ETB 150/month**

### Q14: Where did the numbers come from?

**The code contains a direct link to the proclamation PDF:**
`https://lawethiopia.com/images/proc1395-2025.pdf`

This is referenced in the comments of `tax.py` line 7. However, it's unclear whether anyone on the team has actually opened and verified this PDF against the hardcoded values.

### Q15: Has anyone read the actual proclamation?

**Unknown — but the code suggests secondary sources were used for pension.** The pension ceiling (ETB 15,000) was originally added from "secondary compliance sources" and has since been **removed** after research confirmed Ethiopia has no statutory pension ceiling. The tax brackets appear to be from the actual proclamation (the PDF link is present), but no human verification is documented.

---

## ERCA Filing (Current: 7/10)

### Q16: Export format?

**Excel (.xlsx)** via `openpyxl`. The ERCA report generates an Excel file with employee-level tax details. Bank files are generated as `.txt` (fixed-width or CSV depending on bank). Telebirr uses a specific format.

From `reports.py` and `bank_file.py`:
- ERCA report: Excel with columns for TIN, name, gross salary, taxable income, tax withheld
- Pension report: Separate Excel for PSSA submissions
- Bank files: Text files per bank (CBE, Dashen, Awash, BOA, Telebirr, etc.)

### Q17: Has the export been shown to an accountant or tax officer?

**No.** The ERCA format has never been verified against an actual ERCA portal submission. This is explicitly listed as a blocker in `SESSION_SUMMARY_2026-07-19.md`: *"Test ERCA report format against a real ERCA portal submission — format is assumed, never verified end-to-end."*

### Q18: Do you know anyone who has filed with ERCA electronically?

**Not documented.** The system generates the file for manual download and upload to the ERCA portal. No API integration exists. No one has tested whether the generated file is accepted by the ERCA portal.

### Q19: ERCA sandbox or test portal?

**Not known.** No sandbox URL is referenced anywhere in the codebase or documentation.

---

## Pension Ceiling (Current: "Resolved")

### Q20: Is the ETB 15,000 cap still in the code?

**No — removed today (2026-07-20).** After research confirmed Ethiopia has no statutory pension ceiling, the following changes were made:

- `pension.py`: Removed `PENSION_SALARY_CEILING = Decimal('15000')` and all `min(salary, ceiling)` logic
- `models.py`: Added configurable `pension_ceiling` property to TaxRule (defaults to `None` = no ceiling)
- Tests: Updated to reflect no ceiling; added test proving ceiling works when configured

Pension is now: 7% employee / 11% employer on **full basic salary**, no cap.

If Ethiopia introduces a ceiling in the future, set `rules_json['pension']['ceiling'] = 15000` in a TaxRule — no code change needed.

### Q21: Ethiopian accountant or HR professional in network?

**Not documented.** No external verification of pension rates or tax brackets by a qualified professional is recorded in the project history.

---

## Informal Market (Not Scored Yet)

### Q22-24: Informal workers research?

**No user research has been conducted.** The system is designed for formal employment (monthly salary, employer-employee relationship, tax registration). There is no support for:
- Per-job or per-task payment
- Workers without TIN numbers
- Workers without bank accounts
- Weekly or daily wage calculation (the system does have a `daily_rate` employee type, but no informal market features)

---

## General

### Q25: Biggest fear about launching?

**Not explicitly stated.** Based on the codebase evidence, the biggest risks are:
1. **Regulatory** — ERCA filing format unverified, tax brackets from secondary sources
2. **Data** — No tested backup/restore procedure for the live database
3. **Mobile** — Primary users (Ethiopian business owners) are mobile-first, but mobile UX is 5/10

### Q26: Timeline?

**Not documented.** The project has been in active development across multiple sessions. No deadline or launch date is recorded.

### Q27: Solo or team?

**Solo developer + AI assistant.** All commits are from a single author. The AI handles code generation, testing, audits, and documentation. No team members are documented.

---

## Summary: What Blocks Moving to 9/10

| Category | Current | Blocker | Effort |
|---|---|---|---|
| **Mobile** | 5/10 | No real device testing; tables overflow | 2-3 days |
| **Infrastructure** | "Not Ready" | No staging, no tested backups, no runbook | 1-2 days |
| **Regulatory** | "Unverified" | Need human to verify proclamation PDF | 2 hours |
| **ERCA Filing** | 7/10 | Need real business owner to test against ERCA portal | External |
| **Pension** | ✅ Resolved | Ceiling removed, configurable for future | Done |

### Immediate Actions (can be done by AI)

1. **Mobile**: Test on actual device, fix table overflow, add PWA manifest
2. **Infrastructure**: Document backup/restore procedure, test against Render Postgres
3. **Create a runbook**: "What to do when X breaks"

### External Dependencies (need humans)

1. **Tax verification**: Ethiopian accountant reviews proclamation vs. code
2. **ERCA testing**: Business owner tests generated file on actual ERCA portal
3. **i18n review**: Native Amharic/Afaan Oromoo speaker reviews translations
