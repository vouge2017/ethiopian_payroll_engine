# Payroll translation review exports

Generated from `feature/amharic-prep-review-and-ops` (stacked on
`codex/synthetic-preview`, including RC-38000-01).

## Latest: 2026-10-20

- [Workbook (XLSX)](2026-10-20/payroll_i18n_review_2026-10-20.xlsx) — all keys,
  contexts, gaps, draft flags and suggestion columns.
- [Everything (ZIP)](2026-10-20/payroll_i18n_review_2026-10-20.zip) — workbook,
  flat CSV, README and all correction templates.
- [Flat CSV](2026-10-20/payroll_i18n_review_2026-10-20.csv) — same data as the
  Review sheet, UTF-8 with BOM for Excel.
- [Amharic corrections](2026-10-20/corrections_amharic_2026-10-20.csv)
- [Oromo corrections](2026-10-20/corrections_oromo_2026-10-20.csv)
- [English wording](2026-10-20/corrections_english_2026-10-20.csv)

Counts at generation: **481 keys**; Amharic **477 translated / 4 missing**;
Oromo **130 translated / 347 English fallback / 4 missing**; **1,049**
hardcoded template candidates not yet wired to `_()`.

Missing dictionary keys found: `generated`, `of`, `per`, `total_overtime`
(used on the employee payslip; both Amharic and Oromo show the raw key).
`tax_explainer_intro` has no stored English, so English renders as the
title-cased key "Tax Explainer Intro".

## How to review

1. Download the workbook or the per-language correction CSV.
2. Check against the live screens: preparation `/payroll/spreadsheet`, review
   `/payroll/runs/<id>/review`, employee payslip `/my/payslips/<id>`, sign-in
   `/auth/login`.
3. Put corrections in `suggested_text` and add context/dialect notes in
   `comment`. Keep the `key` column unchanged.
4. Return the completed CSV or workbook. Corrections are applied as code
   changes and the export is regenerated.

Do not change the current English text for existing keys without checking the
tests first: several English bytes are pinned by regression tests.

## What the statuses mean

- **Translated** — text exists for that language.
- **English fallback (no Oromo)** — no Oromo entry; Oromo UI currently shows
  English.
- **MISSING (key shown)** — no entry; UI currently shows the raw key.
- **Draft** — added in the 2026-10-18 prep/review slice or RC-38000-01; not yet
  reviewed.

## Regenerate

```bash
python scripts/export_i18n_review.py
```

The exporter reads `payroll_engine/i18n_first_use.py`, `i18n.py`, `i18n_om.py`
and every literal `_('key')` / `get_string('key')` reference in product code.
It does not resolve keys assembled at runtime; those are listed in the
workbook's Dynamic references sheet. Hardcoded template text is a heuristic
candidate list, not part of the translation dictionary.
