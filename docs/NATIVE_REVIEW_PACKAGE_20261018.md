# Native-speaker review package — draft Amharic/Oromo strings

Date: 2026-10-18
Branch: `feature/amharic-prep-review-and-ops`
Scope: monthly payroll **preparation** and **review** screens only.
(`payroll_confirm` and payday/results screens are intentionally unchanged this
slice.)

All the strings below are new and marked DRAFT inside
`payroll_engine/i18n_first_use.py` (`PAYROLL_COPY.update({...})` block, comment
`DRAFT TRANSLATIONS (2026-10-18)`). English values must stay byte-identical to
what production shows today; Amharic values are drafts awaiting review. Oromo
values are drafts too — every key also exists in `STRINGS_OM` per
`tests/test_i18n.py::test_oromo_all_keys_have_translations`.

## How to review

1. Sign in on staging, switch your profile language to Amharic (or Oromo).
2. Walk the screens listed in `docs/SYNTHETIC_PREVIEW.md`:
   preparation (`/payroll/payroll-spreadsheet`), review
   (`/payroll/runs/<id>/review`), including an employee-ledger row expanded,
   the filter buttons, and the "How this review stays current" notes.
3. Note corrections against the key names below. Corrections are applied as
   code changes; no runtime text editing exists.

## Draft keys (English value → what to check)

### Preparation screen (`payroll_spreadsheet.html`)
- `monthly_empty_title` — Start with your employees
- `monthly_empty_intro` — Add employees first. Then enter monthly changes...
- `monthly_add_first_employee` — Add first employee
- `monthly_import_file` / `monthly_import_help` — Import payroll file / help text
- `monthly_enter_changes` — Enter this month's changes, save, then review...
- `monthly_this_month_inputs` — This month's inputs
- `monthly_edit_inputs` / `monthly_unsaved_edits` — Edit inputs / Unsaved edits
- `monthly_save_all_note` — Save all inputs together...
- `monthly_save_recalculate` — Save & recalculate
- `monthly_review_saved_payroll` / `monthly_ready_to_check` — Review saved payroll / Ready to check the amounts?
- `monthly_basic_note` — Basic salary (row amounts are read-only in this screen)
- `monthly_bonus_etb` / `monthly_advance_etb` / `monthly_overtime_hours` — field labels (· ETB / · hours)
- `monthly_ot_day|night|holiday|rest` — overtime day-type names; check dialect
- `monthly_only_title` — Monthly employees only (daily help note)
- `monthly_daily_note` — daily-employee note
- `monthly_inputs_effect_title|body` — how inputs affect payroll (rates ×/÷ wording)
- `monthly_ot_limit_warning` — overtime exceeds monthly limit
- `monthly_find_employee` / `monthly_search_placeholder` — search UI
- `monthly_employee_no_match` — no-match text
- `monthly_estimated_net_label` / `monthly_gross_etb` / `monthly_income_tax_etb` / `monthly_tax_short` — totals row
- `monthly_employees_count` — totals employee count
- `monthly_retry_preparation|help` — estimate-unavailable retry
- `payroll_steps`, `step_prepare|review|approve` — stepper chips

### Review screen (`payroll_review_workspace.html`)
- `review_page_title` / `review_title` — page title "Payroll Review" / heading "Review payroll"
- `review_intro` — intro under heading
- `review_what_to_check` / `review_frozen_help` — story section
- `review_changed_one|many`, `review_compared_with`, `review_open_row_help` — comparison summary
- `review_full_record` / `review_updates` / `review_about_comparison` — change record details
- `review_notes_title|help`, `review_finding_blocking|review`, `review_why`, `review_what_to_do`, `review_add_phone`, `review_open_details` — findings cards
- `review_saved_validation`, `review_additional_notes`, `review_override_recorded`, `review_flag_help` — saved checks
- `review_employee_pay`, `review_saved_payroll_for`, `review_gregorian_note`, `review_later_edit_note` — ledger heading
- `review_find_employee`, `review_filter_all|issues|changed`, `review_filter_aria`, `review_no_filter_match`, `review_clear_filters` — filter tools
- `review_issue_badge`, `review_changed_badge`, `review_why_pay_changed`, `review_bonus_label`, `review_net_pay_etb` — row badges
- `review_income_tax_plain`, `review_net_pay_plain`, `review_leave_deductions`, `review_other_deductions` — breakdown terms
- `review_newer_changes`, `review_newer_changes_help`, `review_return_preparation`, `review_refresh_saved`, `review_refresh_confirm` — refresh flow
- `review_next_step`, `review_no_blocking_help`, `review_after_approval`, `review_submit_owner`, `review_waiting_owner`, `review_approve_button` — decision card
- `review_saved_blocks`, `review_blocking_issues`, `review_unverified_info`, `review_check_status`, `review_unavailable`, `review_cannot_verify`, `review_manually` — blocked-approval variants
- `review_approved_title`, `review_approval_recorded`, `review_view_approved`, `review_approved`, `review_approved_locked`, `review_ready_owner`, `review_waiting_owner`, `review_resolve_blocking`, `review_checks_attention|help` — status badges
- `review_evidence_title`, `review_checks_passed`, `review_passed_only`, `review_trust_evidence`, `review_source` — evidence card
- `review_all_runs`, `review_view_details`, `review_run_date`, `review_next_action_aria` — navigation

### Shared texts with totals/period (`components/monthly_payroll.html`)
- `monthly_period_gregorian|ethiopian`, `monthly_period_aria` — dual-calendar period strip
- `monthly_aria_totals`, `monthly_employees_count`, `monthly_gross_etb`, `monthly_income_tax_etb`, `monthly_vs_previous` — totals band

### JavaScript strings (injected via `window.PAYROLL_I18N`)
- `monthly_state_dirty` / `monthly_state_saved` — live save state
- `monthly_estimate_label` / `monthly_last_saved_label` — per-row estimate labels
- `monthly_busy_saving` / `monthly_busy_opening` — busy overlays
- `monthly_save_first_help` / `monthly_review_uses_saved` — guidance line
- `monthly_js_count_pattern` / `monthly_js_review_count_pattern` — "{0} of {1} employees shown [· totals include everyone]"

## Explicitly NOT in this package

- Confirmation screen, payslips, bank files, results/diff screens (English-only
  this slice).
- RC-38000-01 accountant notices — reviewed separately under
  `docs/PENSION_BEFORE_TAX_RC38000_01.md`.
- Router level i18n and email copy (future work orders).

## Tests that gate this slice

- `tests/test_i18n.py` — all keys resolve in am/om, missing key → raw key,
  Oromo coverage complete (all pass locally 2026-10-18).
- Templates parse via `app.jinja_env.get_template` (all 4 touched files OK).
- `node --check payroll_engine/static/js/monthly-payroll.js` — OK.
