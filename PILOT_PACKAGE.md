# PILOT PACKAGE
**Date:** 2026-08-31
**Commit:** `70143e7`
**Production:** https://ethiopian-payroll-engine.onrender.com

> This package is preparation for a real-accountant pilot. It is NOT validation. Validation happens when a real accountant processes a real payroll.

---

## 1. Pilot onboarding procedure

### Pre-pilot checklist (ops)

- [ ] Confirm `DB_ENCRYPTION_KEY` in Render dashboard is escrowed in a separate secret manager (1Password / AWS Secrets Manager / offline password vault)
- [ ] Set `SENTRY_DSN` in Render dashboard
- [ ] Confirm Render Cron Job `ethiopian-payroll-cron` exists and is scheduled `0 6 * * *` (06:00 UTC daily)
- [ ] Confirm the deployed commit matches `70143e7` (Settings → Service → "Deploys")
- [ ] Confirm `/internal/cron/health` returns 200 from the running deployment
- [ ] Confirm a PITR snapshot exists in Render → Postgres → Backups

### Pilot kickoff (accountant)

1. Receive invite email from pilot coordinator with a one-time registration link
2. Set a strong password (12+ chars, mixed case, digit, symbol)
3. Enable MFA (TOTP) via `/auth/mfa/setup`
4. Create a new company via `/setup-company` (or accept an invite to an existing one)
5. Verify the company's compliance deadlines are set via `/settings/compliance`
6. Run a dry-run payroll (see "Payroll processing checklist" below)

---

## 2. Company setup procedure

For the pilot company, the accountant should provide:

- Legal name (English + Amharic)
- TIN (Tax Identification Number)
- Address
- Phone
- Bank account details (for outgoing payments)
- Logo (optional, PNG)
- Default currency: ETB (only ETB is supported in pilot)
- Country: Ethiopia (only ET is supported)

Configuration locations:
- `/settings/company` — company profile
- `/settings/team` — invite accountants/owners
- `/settings/compliance` — set ERCA/pension deadlines
- `/settings/reports` — per-company ERCA column configuration
- `/settings/link-employee` — link employees to their self-service accounts (optional)

---

## 3. Employee import template

### CSV format

| Column | Required | Type | Example |
|---|---|---|---|
| `employee_id` | yes | string | `E-001` |
| `first_name` | yes | string | `Abebe` |
| `father_name` | yes | string | `Kebede` |
| `grandfather_name` | yes | string | `Tadesse` |
| `basic_salary` | yes | number | `5000.00` |
| `employee_type` | yes | `monthly` / `daily` | `monthly` |
| `daily_rate` | if daily | number | `300.00` |
| `department` | no | string | `Engineering` |
| `position` | no | string | `Engineer` |
| `phone` | no | string (09XXXXXXXX) | `0911234567` |
| `tin` | no | string | `TIN-EMP-001` |
| `bank_account` | no | string | `CBE-1234567890` |
| `bank_or_telebirr` | no | string | `cbe` / `telebirr` |
| `fayda_fin` | no | string | `FIN-XXX` |
| `start_date` | yes | YYYY-MM-DD | `2026-01-15` |

### Import route

- Upload via `/employees` → "Import from CSV"
- Or paste manually via `/employees/add` form
- Or via API: `POST /api/v1/employees` with `Authorization: Bearer ep_<token>`

### Validation

The system rejects rows with:
- Missing required field
- Negative salary
- Malformed phone (must be 9 digits starting with 9 or 7, or `+251...`)
- Duplicate `employee_id` for the same company

Errors are returned in the import preview before any DB write.

---

## 4. Payroll processing checklist (per month)

### Step 1 — Collect inputs
- [ ] All employees imported (verify via `/employees` count vs HR list)
- [ ] All overtime entered (route: `/employees/<id>/overtime` or `/attendance/import`)
- [ ] All leave requests approved or rejected (route: `/leave` or `/calendar`)
- [ ] All profile changes (bank, TIN) approved (route: `/profile-changes`)
- [ ] All allowances valid for this period (route: `/employees/<id>/allowances`)

### Step 2 — Upload / register payroll
- [ ] Navigate to `/payroll` (or `/payroll/spreadsheet` for in-app editor)
- [ ] Upload CSV/Excel OR enter manually via spreadsheet
- [ ] System parses, calculates, shows preview with line-item breakdown
- [ ] Review calculation narrative (per-employee step-by-step)
- [ ] Submit → run is created in `draft` status

### Step 3 — Review
- [ ] Navigate to `/payroll/cockpit` (or `/payroll/dashboard`)
- [ ] Check Change Summary (what changed vs last month)
- [ ] Check Narrative (why payroll changed)
- [ ] Check Variance (unusual movements)
- [ ] Check Exceptions inbox (BLOCK/FLAG/WARN)
- [ ] Resolve all BLOCK issues
- [ ] For FLAG issues, click "Override with reason" or "Acknowledge"
- [ ] Confidence / readiness score should be ≥ threshold

### Step 4 — Approval (if accountant)
- [ ] Click "Submit for Owner Approval" (status: review → pending_approval)
- [ ] Owner receives notification
- [ ] Owner reviews, then approves
- [ ] Re-authenticate with password (and TOTP if enabled)
- [ ] Status: completed
- [ ] Payslips are generated in the background (check `/payroll/batch-pdf/<batch>/status`)

### Step 5 — Disbursement
- [ ] Navigate to `/payroll/runs/<id>/disbursement`
- [ ] Generate bank file (CBE / Telebirr / etc.)
- [ ] Download, verify total amount
- [ ] Send to bank (out of band)
- [ ] Mark as disbursed in the system

### Step 6 — Bank confirmation
- [ ] When bank confirms payment, mark as "Confirmed" in the system
- [ ] Status: paid

### Step 7 — Filing
- [ ] Navigate to `/payroll/runs/<id>/filing`
- [ ] Generate ERCA report (XLSX) — verify total tax matches payslips
- [ ] Generate Pension report — verify total contributions match
- [ ] Download, submit to ERCA / PSSA (out of band for pilot)
- [ ] Mark as filed in `/filing-history`

### Step 8 — Month-end close
- [ ] Navigate to `/payroll/runs/<id>/close`
- [ ] 7-step guided close: confirm payroll → confirm tax → confirm pension → confirm bank → confirm filing → lock period
- [ ] Period is now locked; no further changes accepted except adjustments

---

## 5. Accountant instructions (one-pager)

> **What this system does for you**
> Calculates Ethiopian income tax, pension, overtime, leave, deductions. Generates payslips, bank files, ERCA and pension reports. Tracks every change.
>
> **What it does NOT do for you**
> It does not submit filings to ERCA. It does not pay the bank. It does not chase employees for missing TIN. Those are still your responsibility.
>
> **What you should do FIRST**
> 1. Add all your employees (import CSV)
> 2. Verify their basic salaries and allowances
> 3. Enter any overtime / leave / deductions for the month
> 4. Run a dry-run payroll BEFORE the real one — compare to your Excel
> 5. Then run the real payroll for the month
>
> **Where to get help**
> - `/help` — built-in help center
> - `support@ethiopayroll.com` — pilot support email
> - Pilot coordinator: [name + phone]

---

## 6. Excel comparison template

The accountant runs the same payroll in their existing Excel and in EthioPayroll. For each employee, record:

| Employee | Field | EthioPayroll | Excel | Diff | Class | Notes |
|---|---|---|---|---|---|---|
| E-001 | Gross | 5,000.00 | 5,000.00 | 0 | match | |
| E-001 | Pension (7%) | 350.00 | 350.00 | 0 | match | |
| E-001 | Taxable | 4,650.00 | 4,650.00 | 0 | match | |
| E-001 | Income tax | 365.00 | 360.00 | 5.00 | rounding | EthioPayroll uses ROUND_HALF_UP; Excel might use floor |
| E-002 | ... | ... | ... | ... | ... | |

**Diff classification options:**
- `match` — identical
- `rounding` — diff ≤ 1 ETB and explainable by rounding rule
- `ethiopayroll_bug` — diff > 1 ETB, system is wrong
- `accountant_error` — diff > 1 ETB, Excel is wrong
- `legal_interpretation` — different reading of the same law
- `data_entry` — different inputs in either system
- `unresolved` — needs investigation

---

## 7. Discrepancy log

The accountant maintains `docs/pilot_discrepancies.md`:

```
# Pilot Discrepancy Log
## Company: <name>
## Period: 2026-MM
## Accountant: <name>

### D-001
Employee: E-001
Field: Income tax
EthioPayroll: 365.00 ETB
Excel: 360.00 ETB
Diff: 5.00 ETB
Classification: rounding
Resolution: EthioPayroll applies ROUND_HALF_UP; bracket 4001-7000 has 20% marginal.
Status: RESOLVED
```

Any `unresolved` or `ethiopayroll_bug` discrepancy **blocks pilot sign-off** until fixed.

---

## 8. Support escalation

- **Tier 1 (accountant → pilot coordinator)**: Slack channel `#pilot-<company>`
- **Tier 2 (pilot coordinator → engineer)**: GitHub issue with label `pilot-blocker`
- **Tier 3 (engineer → on-call)**: PagerDuty rotation `ethiopayroll-pilot-oncall`
- **Data emergencies (suspected data corruption, security incident)**: Page immediately, do not wait for next business day

---

## 9. Rollback / recovery procedure

If the pilot produces critical data corruption or a security incident:

1. **Stop new payroll processing** for the pilot company (mark company `billing_status='blocked'`)
2. **Preserve the database** — Render PITR is available, do NOT delete anything
3. **Capture logs** from Render → Logs (download 24h window)
4. **Restore the database** from the last known-good PITR snapshot (Render → Postgres → Backups → Restore)
5. **Re-verify** with the encrypted fields test (`tests/test_p0b_encryption_recovery.py`)
6. **Investigate root cause** before re-enabling

If encryption key is lost:
1. Check the escrow location (1Password / vault)
2. Restore the key to Render environment
3. Restart the web service
4. Verify decryption works by logging in and reading an employee TIN

---

## 10. Evidence collection procedure

After the pilot month closes, collect:

- [ ] `docs/pilot_discrepancies.md` (full log)
- [ ] Screenshot of the cockpit for each month-end
- [ ] Bank confirmation receipt (out-of-band)
- [ ] ERCA submission receipt (when filed)
- [ ] Final comparison spreadsheet (Excel vs EthioPayroll)
- [ ] Accountant interview notes (recorded with consent)
- [ ] Pilot success/failure decision signed by pilot coordinator

Store all evidence in `docs/pilots/<company>-<period>/`.

---

## 11. Post-pilot decision

After the pilot month:

- **GO to 3-company scale** if:
  - Zero `unresolved` discrepancies
  - Zero `ethiopayroll_bug` discrepancies
  - Accountant completed the workflow without Excel
  - Accountant states they would use the system again
- **HOLD** if:
  - Any `ethiopayroll_bug` discrepancies
  - Accountant still needed Excel for > 1 critical step
- **NO-GO** if:
  - Any `unresolved` discrepancies that block filing
  - Accountant refuses to use the system again
  - Cross-tenant data exposure observed

