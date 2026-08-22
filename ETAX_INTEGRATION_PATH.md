# eTax Integration Path

**Date:** 2026-08-02
**Purpose:** Document how EthioPayroll integrates with Ethiopia's eTax filing system

---

## How ERCA Filing Actually Works

Ethiopian companies file monthly tax through the **eTax portal** (etax.erca.gov.et). The process:

1. **Company receives payroll data** → calculates tax, pension, net pay
2. **Company logs into eTax portal** → selects regional/sub-city office
3. **Company enters/uploads filing** → using eTax template (varies by region)
4. **eTax generates confirmation** → confirmation number stored for audit

### Key Points

- eTax templates vary by **regional office** (Addis Ababa, Dire Dawa, Hawassa, etc.)
- Some offices accept **CSV/Excel upload**, others require **manual entry**
- Column format is determined by the **eTax portal**, not by ERCA proclamation
- The portal may change its format without proclamation changes

---

## Current EthioPayroll Support

### What We Have

| Feature | Status | Notes |
|---------|--------|-------|
| ERCA export (Excel) | ✅ | Configurable columns per company |
| Column templates | ✅ | `report_templates.py` — per-company config |
| Filing tracking | ✅ | `FilingRecord` model — stores confirmation numbers |
| Compliance scoring | ✅ | Company-configurable deadlines |
| Deadline reminders | ✅ | Push notifications before deadlines |
| eTax template info | 📝 | This document |

### What We Don't Have Yet

| Feature | Priority | Complexity |
|---------|----------|------------|
| eTax API integration | Low | High — no public API exists |
| Auto-upload to eTax | Low | High — requires eTax credentials |
| Regional template library | Medium | Low — crowdsource from users |
| Filing history sync | Low | Medium — eTax doesn't expose history API |

---

## Integration Strategy: Phased Approach

### Phase 1: Template-Based Export (Current)

**Status:** ✅ Done

- Generate ERCA export with configurable columns
- User downloads file and manually uploads to eTax
- User records confirmation number in EthioPayroll

**How it works:**
1. User goes to Reports → ERCA Export
2. System generates Excel/CSV with company-configured columns
3. User downloads and uploads to eTax portal
4. User returns to EthioPayroll and marks as filed (stores confirmation)

### Phase 2: Regional Template Library

**Status:** 📋 Planned

- Build a library of eTax templates by region
- Users select their regional office during setup
- System auto-configures columns to match their eTax portal

**Data source:**
- Crowdsourced from users who share their eTax column format
- Verified against actual eTax portal screenshots
- Updated when eTax changes format

**Implementation:**
```python
# In report_templates.py
ETAX_REGIONAL_TEMPLATES = {
    'addis_ababa_kirkos': {
        'label': 'Addis Ababa — Kirkos Sub-City',
        'columns': [
            {'key': 'name', 'label': 'Employee Full Name'},
            {'key': 'start_date', 'label': 'Start Date'},
            {'key': 'end_date', 'label': 'End Date'},
            {'key': 'basic_salary', 'label': 'Basic Salary'},
            {'key': 'transport_allowance', 'label': 'Transport Allowance'},
            {'key': 'taxable_transport', 'label': 'Taxable Transport Allowance'},
            {'key': 'overtime', 'label': 'Over Time'},
            {'key': 'other_taxable', 'label': 'Other Taxable Benefit'},
            {'key': 'total_taxable', 'label': 'Total Taxable'},
            {'key': 'tax_withheld', 'label': 'Tax withheld'},
        ]
    },
    # ... more regions
}
```

### Phase 3: Smart Filing Assistant

**Status:** 🔮 Future

After collecting enough user filing data, the system can:

1. **Learn filing patterns** — "You usually file on the 22nd"
2. **Pre-fill confirmation numbers** — detect from email/SMS
3. **Flag discrepancies** — compare our export to eTax confirmation
4. **Suggest corrections** — "Your last filing was short by ETB 500"

**Data needed:**
- Filing dates (from `FilingRecord`)
- Confirmation amounts (from user input)
- Regional template (from user selection)

### Phase 4: Direct eTax Integration

**Status:** 🔮 Future (blocked on eTax API)

If/when ERCA exposes a public API:

1. **OAuth authentication** — user grants EthioPayroll access to their eTax account
2. **Auto-upload** — system pushes filing data directly to eTax
3. **Auto-confirmation** — receives confirmation number automatically
4. **Reconciliation** — compares our records to eTax records

**Blockers:**
- No public eTax API exists as of 2026
- Would require ERCA partnership or government API program
- Security concerns (storing eTax credentials)

---

## What Users Should Do Today

### For Accountants

1. **Generate ERCA export** from EthioPayroll (Reports → ERCA Export)
2. **Check column format** matches your eTax portal template
3. **If columns differ** → adjust in Settings → Report Templates
4. **Upload to eTax** → download from EthioPayroll, upload to eTax portal
5. **Record confirmation** → return to EthioPayroll, mark as filed

### For Developers

1. **Collect regional templates** — ask users to share their eTax column format
2. **Build template library** — store in `ETAX_REGIONAL_TEMPLATES`
3. **Add regional selector** — in company setup wizard
4. **Auto-configure columns** — based on selected region

---

## Compliance Deadlines

Deadlines are now **company-configurable** (Settings → Compliance Deadlines):

| Filing | Default | Source | Configurable |
|--------|---------|--------|-------------|
| ERCA Tax Filing | 25th | Common practice | ✅ Day of month |
| Pension Remittance | 10th | Proclamation 1268/2022, Art. 10(6) | ✅ Day of month |
| PSSA Contribution | 10th | Common practice | ✅ Day of month |
| Salary Disbursement | 5 days after month end | Common practice | ✅ Days after month end |
| Custom filings | — | User-defined | ✅ Name + day |

**Why configurable?** Different regional eTax offices may have different practical deadlines. The proclamation says "first 10 working days" for pension, but some offices accept until the 15th. Companies should set what works for their actual workflow.

---

## Related Files

- `payroll_engine/compliance.py` — Compliance scoring with company-configurable deadlines
- `payroll_engine/report_templates.py` — Column template system
- `payroll_engine/models.py:FilingRecord` — Filing tracking
- `payroll_engine/scheduled.py` — Deadline reminders
- `payroll_engine/templates/settings/compliance_deadlines.html` — Settings UI
- `payroll_engine/templates/settings/report_templates.html` — Column config UI

---

*This document is part of the EthioPayroll production readiness process.*
