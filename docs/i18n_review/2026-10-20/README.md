# Payroll UI translation review (2026-10-20)

Generated from `feature/amharic-prep-review-and-ops` at `d2e7037`.

## Files

- `payroll_i18n_review_2026-10-20.xlsx` — main workbook (Review, Oromo gaps, Amharic gaps, Draft keys, Hardcoded candidates, Dynamic references).
- `payroll_i18n_review_2026-10-20.csv` — flat copy of the Review sheet, UTF-8 with BOM for Excel.
- `corrections_amharic_2026-10-20.csv` — fill `suggested_text` for Amharic.
- `corrections_oromo_2026-10-20.csv` — fill `suggested_text` for Oromo.
- `corrections_english_2026-10-20.csv` — propose clearer English wording.

## Counts

- Keys: 481; Amharic translated 477, missing 4.
- Oromo translated 130, English fallback 347, missing/raw key 4.
- Keys with a direct code/template reference: 418; dictionary-only: 63.
- Hardcoded template text candidates (not wired to `_()`): 1049.

## How to use

1. Open the workbook and use the Area/Priority filters, or work screen by screen from `Where used`.
2. Put corrections in the suggested columns (or the per-language CSV). Keep the `key` column unchanged.
3. Do not edit the current English text in code; tests pin existing English bytes.
4. Return the completed CSV/workbook. Corrections are applied as code changes.

## Screens to check

- Preparation: `/payroll/spreadsheet`
- Review: `/payroll/runs/<id>/review`
- Employee payslip: `/my/payslips/<id>`
- Sign-in and onboarding: `/auth/login`, `/auth/register`

## Legend

- `Translated` — text exists for that language.
- `English fallback (no Oromo)` — no Oromo entry; Oromo UI shows English.
- `MISSING (key shown)` — no entry; UI shows the raw key.
- `Draft` — new prep/review or RC-38000-01 copy, not yet reviewed.

## Caveats

- English for legacy keys is title-cased from the key, not stored separately.
- Oromo checks `FIRST_USE_COPY` first; entries for those keys would be ignored (the sets do not overlap today).
- Dynamic runtime keys cannot be resolved statically; see the Dynamic references sheet.
- Hardcoded template text is a review candidate list, not part of the dictionary yet.
- Contexts are file:line at the generation commit and may move after edits.
