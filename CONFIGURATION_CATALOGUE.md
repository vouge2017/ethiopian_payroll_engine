# Configuration Catalogue
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** Every configurable setting — default, limit, who edits, validation, audit
**Audience:** Engineers, support, implementation partners

---

## How to Use This Document

Every configurable value in the system is listed here once. When adding a new setting, add it to this catalogue first.

| Field | Description |
|-------|-------------|
| **Category** | Which module/domain |
| **Key** | Internal identifier |
| **Default** | Value if not configured |
| **Allowed** | Valid range/options |
| **Editable By** | Who can change it |
| **Approval** | Whether change needs approval |
| **Effective** | When change takes effect |
| **Audit** | Whether change is logged |
| **DB Location** | Where stored |
| **PRD/BR** | Reference |

---

## Payroll Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Payroll | default_pay_day | 25 | 1-31 | Owner | No | Next payroll | Yes | SystemSetting | PRD-02 |
| Payroll | payroll_period_type | ethiopian_month | ethiopian_month, gregorian_month | Owner | No | Next payroll | Yes | SystemSetting | PRD-02 |
| Payroll | allow_negative_net | false | true/false | Owner | No | Immediate | Yes | SystemSetting | PRD-02 |
| Payroll | max_deduction_pct | 50 | 1-100 | Owner | No | Next payroll | Yes | SystemSetting | PRD-02 |
| Payroll | auto_lock_on_approval | true | true/false | Owner | No | Immediate | Yes | SystemSetting | PRD-03 |

---

## Tax Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Tax | personal_relief | 150 | 0-10000 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-TAX-07 |
| Tax | tax_brackets | [0-2000@0%, 2001-4000@15%, 4001-7000@20%, 7001-10000@25%, 10001-14000@30%, 14001+@35%] | Valid brackets | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-TAX-01-06 |
| Tax | effective_from | (per rule) | Date | Owner | No | Per rule | Yes | TaxRule.effective_from | ADR-010 |
| Tax | effective_to | null | Date or null | Owner | No | Per rule | Yes | TaxRule.effective_to | ADR-010 |

---

## Pension Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Pension | employee_rate | 0.07 | 0-0.50 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-PEN-01 |
| Pension | employer_rate | 0.11 | 0-0.50 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-PEN-02 |
| Pension | pension_base | basic_salary | basic_salary, gross_salary | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-PEN-03 |
| Pension | salary_ceiling | null | Amount or null | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-PEN-04 |

---

## Overtime Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Overtime | day_rate | 1.25 | 1.0-3.0 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-OT-01 |
| Overtime | night_rate | 1.50 | 1.0-3.0 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-OT-02 |
| Overtime | holiday_rate | 2.00 | 1.0-5.0 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-OT-03 |
| Overtime | rest_holiday_rate | 2.50 | 1.0-5.0 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-OT-04 |
| Overtime | monthly_limit_hours | 20 | 0-100 | Owner | No | Immediate | Yes | TaxRule.rules_json | PRD-02, BR-OT-05 |
| Overtime | yearly_limit_hours | 100 | 0-500 | Owner | No | Immediate | Yes | TaxRule.rules_json | PRD-02, BR-OT-06 |
| Overtime | hourly_rate_divisor | 208 | 160-240 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-OT-07 |

---

## Leave Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Leave | annual_leave_year1 | 14 | 0-30 | Owner | No | Next year | Yes | TaxRule.rules_json | PRD-02, BR-LVE-01 |
| Leave | annual_leave_increment | 1 | 0-5 | Owner | No | Next year | Yes | TaxRule.rules_json | PRD-02, BR-LVE-02 |
| Leave | annual_leave_max | 30 | 14-60 | Owner | No | Next year | Yes | TaxRule.rules_json | PRD-02, BR-LVE-03 |
| Leave | sick_leave_max | 180 | 0-365 | Owner | No | Immediate | Yes | TaxRule.rules_json | PRD-02, BR-LVE-04 |
| Leave | sick_pay_tier1_pct | 100 | 0-100 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-LVE-05 |
| Leave | sick_pay_tier2_pct | 50 | 0-100 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-LVE-06 |
| Leave | sick_pay_tier2_days | 31 | 1-180 | Owner | No | Next payroll | Yes | TaxRule.rules_json | PRD-02, BR-LVE-06 |
| Leave | maternity_leave_days | 120 | 0-180 | Owner | No | Immediate | Yes | TaxRule.rules_json | PRD-02, BR-LVE-08 |
| Leave | paternity_leave_days | 3 | 0-30 | Owner | No | Immediate | Yes | TaxRule.rules_json | PRD-02, BR-LVE-09 |
| Leave | special_leave_days | 3 | 0-10 | Owner | No | Immediate | Yes | TaxRule.rules_json | PRD-02, BR-LVE-10 |
| Leave | leave_year_start_month | 1 | 1-12 | Owner | No | Next year | Yes | SystemSetting | PRD-02 |

---

## Payment Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Payment | default_payment_method | bank | bank, cash, cheque | Owner | No | Next payroll | Yes | Company.settings | PRD-04 |
| Payment | max_retry_count | 3 | 1-10 | Owner | No | Immediate | Yes | SystemSetting | PRD-04, BR-PMT-05 |
| Payment | reversal_reason_min_length | 10 | 5-100 | Owner | No | Immediate | Yes | SystemSetting | PRD-04 |
| Payment | cash_receipt_required | true | true/false | Owner | No | Immediate | Yes | SystemSetting | PRD-04, BR-PMT-11 |
| Payment | bank_file_narrative_template | {period} salary - {id} {name} | Template string | Owner | No | Next file | Yes | Company.settings | PRD-04, BR-PMT-08 |
| Payment | bank_file_decimals | 2 | 0-4 | Owner | No | Next file | Yes | Company.settings | PRD-04 |

---

## Filing Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Filing | erca_deadline_day | 25 | 1-31 | Owner | No | Next filing | Yes | SystemSetting | PRD-05, BR-DLN-01 |
| Filing | pension_deadline_day | 10 | 1-31 | Owner | No | Next filing | Yes | SystemSetting | PRD-05, BR-DLN-02 |
| Filing | erca_report_template | (default9 columns) | Customizable | Owner | No | Next report | Yes | Company.report_templates | PRD-05, BR-FL-02 |
| Filing | pssa_enabled | false | true/false | Owner | No | Immediate | Yes | Company.settings | PRD-05 |

---

## Notification Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Notification | whatsapp_enabled | false | true/false | Owner | No | Immediate | Yes | Company.settings | ADR-017 |
| Notification | email_enabled | false | true/false | Owner | No | Immediate | Yes | Company.settings | ADR-017 |
| Notification | deadline_warning_days | 7,2,0 | Comma-separated | Owner | No | Immediate | Yes | SystemSetting | PRD-05 |
| Notification | acknowledgment_reminder_days | 7 | 1-30 | Owner | No | Immediate | Yes | SystemSetting | PRD-06 |
| Notification | approval_overdue_days | 2 | 1-7 | Owner | No | Immediate | Yes | SystemSetting | PRD-03 |

---

## Security Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Security | session_timeout_minutes | 30 | 5-480 | Owner | No | Next login | Yes | SystemSetting | ADR-020 |
| Security | session_absolute_hours | 8 | 1-24 | Owner | No | Next login | Yes | SystemSetting | ADR-020 |
| Security | max_login_attempts | 5 | 1-20 | Owner | No | Immediate | Yes | SystemSetting | ADR-020 |
| Security | lockout_duration_minutes | 30 | 5-1440 | Owner | No | Immediate | Yes | SystemSetting | ADR-020 |
| Security | mfa_required_for_approval | false | true/false | Owner | No | Immediate | Yes | SystemSetting | ADR-020 |
| Security | password_min_length | 8 | 6-32 | Owner | No | Next password | Yes | SystemSetting | ADR-020 |
| Security | password_require_special | true | true/false | Owner | No | Next password | Yes | SystemSetting | ADR-020 |

---

## Retention Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Retention | pdf_retention_days | 3650 | 365-36500 | Owner | No | Next purge | Yes | SystemSetting | PRD-08, BR-AUD-05 |
| Retention | audit_log_retention_days | 3650 | 365-36500 | Owner | No | Never purged | Yes | SystemSetting | PRD-08, BR-AUD-06 |
| Retention | upload_retention_days | 365 | 30-3650 | Owner | No | Next purge | Yes | SystemSetting | PRD-08 |
| Retention | purge_enabled | true | true/false | Owner | No | Immediate | Yes | SystemSetting | PRD-08 |

---

## Display Settings

| Category | Key | Default | Allowed | Editable By | Approval | Effective | Audit | DB Location | PRD/BR |
|----------|-----|---------|---------|-------------|----------|-----------|-------|-------------|--------|
| Display | default_language | en | en, am, om | Owner | No | Immediate | No | Company.settings | i18n |
| Display | currency_symbol | ETB | String | Owner | No | Immediate | No | Company.settings | ADR-004 |
| Display | currency_decimals | 0 | 0-4 | Owner | No | Immediate | No | Company.settings | ADR-004 |
| Display | date_format | ethiopian | ethiopian, gregorian | Owner | No | Immediate | No | Company.settings | ADR-014 |
| Display | company_logo_url | null | URL | Owner | No | Immediate | No | Company.settings | PRD-06 |

---

*Configuration Catalogue v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
