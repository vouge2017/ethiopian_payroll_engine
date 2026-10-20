#!/usr/bin/env python3
"""Export every payroll UI string for native-speaker review.

The workbook combines the runtime translation dictionaries with every literal
``_('key')`` / ``get_string('key')`` reference in product code, so reviewers can
see English, Amharic and Afaan Oromoo (Oromo) side by side, plus where each key
is used and whether a translation is missing or silently falling back.

Outputs (default ``docs/i18n_review/<date>/``):
  payroll_i18n_review_<date>.xlsx   main workbook
  payroll_i18n_review_<date>.csv    flat copy of the Review sheet (UTF-8 BOM)
  corrections_amharic_<date>.csv    fill-in sheet for Amharic reviewers
  corrections_oromo_<date>.csv      fill-in sheet for Oromo reviewers
  corrections_english_<date>.csv    fill-in sheet for English wording
  payroll_i18n_review_<date>.zip    all of the above

Run from the repository root:
  python scripts/export_i18n_review.py
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from payroll_engine.i18n import STRINGS
from payroll_engine.i18n_first_use import FIRST_USE_COPY
from payroll_engine.i18n_om import STRINGS_OM

PRODUCT_ROOT = ROOT / 'payroll_engine'
NATIVE_PACKAGE = ROOT / 'docs' / 'NATIVE_REVIEW_PACKAGE_20261018.md'

REF_RE = re.compile(r"""(?<![A-Za-z0-9_])_\(\s*['"]([A-Za-z0-9_]+)['"]""")
GET_RE = re.compile(r"""(?<![A-Za-z0-9_])get_string\(\s*['"]([A-Za-z0-9_]+)['"]""")
DYNAMIC_GET_RE = re.compile(r"""(?<![A-Za-z0-9_])get_string\(\s*(?!['"])""")
DYNAMIC_UNDERSCORE_RE = re.compile(r"""(?<![A-Za-z0-9_])_\(\s*(?!['"])""")

RC_DRAFT_KEYS = {
    'tax_explainer_intro',
    'bracket',
    'taxable_range',
    'tax_rate',
    'personal_relief',
    'per_month',
    'pension_before_tax',
    'of_basic_salary',
    'then_tax',
}

AREA_ORDER = [
    'Preparation',
    'Review',
    'Monthly shared',
    'Auth & onboarding',
    'Navigation & layout',
    'Payroll results',
    'Employees',
    'Reports & compliance',
    'Settings & billing',
    'Other / legacy',
]

HEADER_FILL = PatternFill('solid', fgColor='1F4E79')
HEADER_FONT = Font(bold=True, color='FFFFFF', size=11)
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical='top', wrap_text=True)
MISSING_FILL = PatternFill('solid', fgColor='FCE4E4')
FALLBACK_FILL = PatternFill('solid', fgColor='FFF2CC')
OK_FILL = PatternFill('solid', fgColor='E2EFDA')
DRAFT_FILL = PatternFill('solid', fgColor='DDEBF7')


def git_output(*args: str) -> str:
    try:
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ''


def source_files() -> list[Path]:
    files = []
    for pattern in ('*.py', '*.html', '*.js'):
        for path in PRODUCT_ROOT.rglob(pattern):
            rel = path.relative_to(ROOT).as_posix()
            if '/static/vendor/' in rel or '/node_modules/' in rel:
                continue
            if '.min.' in path.name:
                continue
            if path.name.startswith('i18n') and path.parent == PRODUCT_ROOT:
                continue
            files.append(path)
    return sorted(files)


def scan_references(keys: set[str]) -> tuple[dict[str, list[tuple[str, int, str]]], list[str], list[str]]:
    contexts: dict[str, list[tuple[str, int, str]]] = {key: [] for key in keys}
    dynamic_get: list[str] = []
    dynamic_underscore: list[str] = []

    for path in source_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding='utf-8', errors='replace').splitlines()

        for number, line in enumerate(lines, 1):
            matched = set()
            for regex in (REF_RE, GET_RE):
                for match in regex.finditer(line):
                    key = match.group(1)
                    if key in keys:
                        matched.add(key)
                        contexts[key].append((rel, number, line.strip()[:220]))
            if rel.endswith('.py') and DYNAMIC_GET_RE.search(line) and 'def get_string' not in line:
                dynamic_get.append(f'{rel}:{number}: {line.strip()[:180]}')
            if rel.endswith('.html') and DYNAMIC_UNDERSCORE_RE.search(line):
                snippet = line.strip()
                if not snippet.startswith('{%') or '_((' in snippet:
                    dynamic_underscore.append(f'{rel}:{number}: {snippet[:180]}')

    for key, items in contexts.items():
        seen = set()
        unique = []
        for rel, number, snippet in sorted(items, key=lambda item: (item[0], item[1])):
            marker = (rel, number)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append((rel, number, snippet))
        contexts[key] = unique

    return contexts, dynamic_get, dynamic_underscore


def draft_keys_from_package() -> set[str]:
    if not NATIVE_PACKAGE.exists():
        return set()
    text = NATIVE_PACKAGE.read_text(encoding='utf-8')
    return set(re.findall(r'`([a-z][a-z0-9_]+)`', text))


def area_for(key: str, items: list[tuple[str, int, str]]) -> str:
    paths = [rel for rel, _number, _snippet in items]
    in_spreadsheet = any('payroll_spreadsheet' in path for path in paths)
    in_review = any('payroll_review_workspace' in path for path in paths)
    if in_spreadsheet and in_review:
        return 'Monthly shared'
    if in_review:
        return 'Review'
    if in_spreadsheet:
        return 'Preparation'
    if any('components/monthly_payroll' in path for path in paths):
        return 'Monthly shared'
    if any('/auth/' in path for path in paths):
        return 'Auth & onboarding'
    if any(token in path for path in paths for token in ('base.html', 'sidebar', 'bottom_nav', 'navigation', 'nav_')):
        return 'Navigation & layout'
    if any(
        token in path
        for path in paths
        for token in ('payroll_results', 'payroll_confirm', 'payslip', 'settlement', 'pdf')
    ):
        return 'Payroll results'
    if any('employee' in path for path in paths):
        return 'Employees'
    if any(token in path for path in paths for token in ('report', 'compliance', 'tax')):
        return 'Reports & compliance'
    if any(token in path for path in paths for token in ('billing', 'company_profile', 'settings')):
        return 'Settings & billing'

    prefix = key.split('_', 1)[0]
    if prefix in {'monthly'}:
        return 'Preparation'
    if prefix in {'review'}:
        return 'Review'
    if prefix in {'auth', 'entry', 'reg', 'register', 'invite', 'profile', 'login', 'password'}:
        return 'Auth & onboarding'
    if prefix in {'nav', 'menu', 'footer', 'header'}:
        return 'Navigation & layout'
    return 'Other / legacy'


def resolve_text(key: str) -> tuple[str, str, str]:
    english = FIRST_USE_COPY[key][0] if key in FIRST_USE_COPY else key.replace('_', ' ').title()
    amharic = FIRST_USE_COPY[key][1] if key in FIRST_USE_COPY else STRINGS.get(key, key)
    if key in FIRST_USE_COPY:
        oromo = FIRST_USE_COPY[key][0]
    else:
        oromo = STRINGS_OM.get(key, key)
    return english, amharic, oromo


def statuses(key: str) -> tuple[str, str]:
    if key in FIRST_USE_COPY or key in STRINGS:
        am_status = 'Translated'
    else:
        am_status = 'MISSING (key shown)'

    if key in STRINGS_OM and key in FIRST_USE_COPY:
        om_status = 'Oromo exists but English shown'
    elif key in STRINGS_OM:
        om_status = 'Translated'
    elif key in FIRST_USE_COPY:
        om_status = 'English fallback (no Oromo)'
    else:
        om_status = 'MISSING (key shown)'
    return am_status, om_status


def scan_hardcoded_templates(limit: int = 2000) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted((PRODUCT_ROOT / 'templates').rglob('*.html')):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding='utf-8', errors='replace')
        text = re.sub(
            r'<script\b.*?</script>',
            lambda match: '\n' * match.group(0).count('\n'),
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(
            r'<style\b.*?</style>',
            lambda match: '\n' * match.group(0).count('\n'),
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r'\{#.*?#\}', lambda match: '\n' * match.group(0).count('\n'), text, flags=re.DOTALL)

        for number, line in enumerate(text.splitlines(), 1):
            if '_(' in line or '{{' in line or '{%' in line:
                continue
            for match in re.finditer(r'>\s*([^<>{}]{2,180}?)\s*<', line):
                candidate = html.unescape(match.group(1)).strip()
                if not candidate or candidate.startswith(('http', '&', '@')):
                    continue
                words = re.findall(r"[A-Za-z][A-Za-z'’-]+", candidate)
                if len(words) < 2:
                    continue
                if any(token in candidate for token in ('http', 'www.', '.js', '.css', 'px', 'var(')):
                    continue
                marker = (rel, candidate)
                if marker in seen:
                    continue
                seen.add(marker)
                rows.append((rel, number, candidate))
                if len(rows) >= limit:
                    return rows
    return rows


def style_header(ws, headers: list[str]) -> None:
    for index, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=index, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical='center', wrap_text=True)
        cell.border = BORDER
    ws.freeze_panes = 'D2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(headers))}1'
    ws.row_dimensions[1].height = 30


def write_rows(ws, rows: list[list[object]], widths: list[int], amharic_column: int | None = None) -> None:
    for row_number, values in enumerate(rows, 2):
        for column, value in enumerate(values, 1):
            cell = ws.cell(row=row_number, column=column, value=value)
            cell.alignment = WRAP
            cell.border = BORDER
            if amharic_column and column == amharic_column:
                cell.font = Font(name='Nyala', size=11)
        ws.row_dimensions[row_number].height = 44
    for index, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(index)].width = width


def status_fill(value: str) -> PatternFill | None:
    if value.startswith('MISSING'):
        return MISSING_FILL
    if value.startswith(('English fallback', 'Oromo exists')):
        return FALLBACK_FILL
    if value == 'Translated':
        return OK_FILL
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'docs' / 'i18n_review')
    parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--no-zip', action='store_true')
    args = parser.parse_args()

    references: dict[str, list[tuple[str, int, str]]] = {}
    for path in source_files():
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = path.read_text(encoding='utf-8', errors='replace')
        for regex in (REF_RE, GET_RE):
            for match in regex.finditer(text):
                references.setdefault(match.group(1), []).append(
                    (path.relative_to(ROOT).as_posix(), text[: match.start()].count('\n') + 1, '')
                )

    initial_keys = set(FIRST_USE_COPY) | set(STRINGS) | set(STRINGS_OM) | set(references)
    contexts, dynamic_get, dynamic_underscore = scan_references(initial_keys)
    all_keys = set(FIRST_USE_COPY) | set(STRINGS) | set(STRINGS_OM) | set(contexts)

    draft_slice = draft_keys_from_package()
    rows = []
    for key in all_keys:
        english, amharic, oromo = resolve_text(key)
        am_status, om_status = statuses(key)
        items = contexts.get(key, [])

        if key in draft_slice:
            priority = 'Draft: prep/review (2026-10-18)'
        elif key in RC_DRAFT_KEYS:
            priority = 'Draft: RC-38000-01'
        else:
            priority = 'Existing'

        notes = []
        if am_status.startswith('MISSING'):
            notes.append('No Amharic entry; UI shows the raw key.')
        if om_status.startswith('English fallback'):
            notes.append('No Oromo entry; Oromo UI shows English.')
        elif om_status.startswith('MISSING'):
            notes.append('No Oromo entry; Oromo UI shows the raw key.')
        elif om_status.startswith('Oromo exists'):
            notes.append('Oromo text exists but runtime shows English (FIRST_USE precedence).')
        if key not in FIRST_USE_COPY:
            notes.append('English is title-cased from the key (no stored English).')
        if not items:
            notes.append('No direct reference found (dynamic or legacy key).')

        where = '; '.join(f'{rel}:{number}' for rel, number, _snippet in items[:10])
        if len(items) > 10:
            where += f'; +{len(items) - 10} more'
        example = items[0][2] if items else ''

        rows.append(
            {
                'area': area_for(key, items),
                'priority': priority,
                'key': key,
                'english': english,
                'amharic': amharic,
                'oromo': oromo,
                'am_status': am_status,
                'om_status': om_status,
                'where': where,
                'example': example,
                'notes': ' '.join(notes),
            }
        )

    area_index = {area: index for index, area in enumerate(AREA_ORDER)}
    priority_index = {
        'Draft: prep/review (2026-10-18)': 0,
        'Draft: RC-38000-01': 1,
        'Existing': 2,
    }
    rows.sort(key=lambda row: (area_index.get(row['area'], 99), priority_index.get(row['priority'], 9), row['key']))

    out_dir = (args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir) / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_dir / f'payroll_i18n_review_{args.date}.xlsx'
    csv_path = out_dir / f'payroll_i18n_review_{args.date}.csv'
    zip_path = out_dir / f'payroll_i18n_review_{args.date}.zip'

    commit = git_output('rev-parse', '--short', 'HEAD') or 'unknown'
    branch = git_output('rev-parse', '--abbrev-ref', 'HEAD') or 'unknown'

    am_translated = sum(1 for row in rows if row['am_status'] == 'Translated')
    am_missing = len(rows) - am_translated
    om_translated = sum(1 for row in rows if row['om_status'] == 'Translated')
    om_fallback = sum(1 for row in rows if row['om_status'].startswith('English fallback'))
    om_missing = sum(
        1 for row in rows if row['om_status'].startswith('MISSING') or row['om_status'].startswith('Oromo exists')
    )
    referenced = sum(1 for row in rows if row['where'])
    unreferenced = len(rows) - referenced

    workbook = Workbook()
    ws = workbook.active
    ws.title = 'README'
    ws.column_dimensions['A'].width = 118
    readme_lines = [
        ('Payroll UI translation review', True),
        (f'Generated {args.date} from {branch} @ {commit}.', False),
        ('', False),
        ('What this workbook contains', True),
        (
            'Every key in the runtime translation dictionaries (English, Amharic, Afaan Oromoo), plus every literal translate-key reference in product templates, Python and JavaScript. Each row shows the current text, where it is used, and whether the language is translated or falling back.',
            False,
        ),
        (f'Keys: {len(rows)} | Amharic translated: {am_translated} | Amharic missing: {am_missing}', False),
        (
            f'Oromo translated: {om_translated} | Oromo English fallback: {om_fallback} | Oromo missing/raw key: {om_missing}',
            False,
        ),
        (f'Keys with a direct reference: {referenced} | dictionary-only (no direct reference): {unreferenced}', False),
        ('', False),
        ('How to review', True),
        (
            '1. Open the Review sheet. Use the Area and Priority filters, or work screen by screen using Where used.',
            False,
        ),
        (
            'Screens: preparation /payroll/spreadsheet | review /payroll/runs/<id>/review | employee payslip /my/payslips/<id> | sign-in /auth/login.',
            False,
        ),
        (
            '2. Do not edit the current English column in code: tests require the current English bytes for existing keys. Put wording changes in Suggested English.',
            False,
        ),
        (
            '3. Put corrections in Suggested Amharic / Suggested Oromo (and Reviewer comment for nuance, dialect or context).',
            False,
        ),
        (
            '4. If separate reviewers cover each language, use corrections_amharic_<date>.csv and corrections_oromo_<date>.csv instead of the workbook. Keep the key column unchanged.',
            False,
        ),
        (
            '5. Return the completed workbook or CSV. Corrections are applied as code changes; there is no runtime text editor.',
            False,
        ),
        ('', False),
        ('Status legend', True),
        ('Translated = text exists in the runtime dictionary for that language.', False),
        ('English fallback (no Oromo) = no Oromo entry; Oromo UI currently shows English.', False),
        ('MISSING (key shown) = no entry; UI currently shows the raw key such as monthly_save_recalculate.', False),
        ('Draft = added in the 2026-10-18 prep/review slice or RC-38000-01; all new copy is unreviewed.', False),
        ('', False),
        ('Important caveats', True),
        ('- English for legacy keys is derived by title-casing the key, not stored separately.', False),
        (
            '- The get_string Oromo path checks FIRST_USE_COPY first, so Oromo entries for FIRST_USE keys would be ignored. Today the sets do not overlap.',
            False,
        ),
        ('- Dynamic keys built at runtime cannot be resolved statically; see the Dynamic references sheet.', False),
        (
            '- Hardcoded template text that is not wrapped in _() is listed separately as candidates. It is not part of the translation dictionary yet.',
            False,
        ),
        ('- File:line contexts were generated from the current branch and may move after edits.', False),
        (
            '- Ethiopic text uses the Nyala font in Excel where available; CSV files are UTF-8 with BOM for Excel.',
            False,
        ),
    ]
    for index, (line, bold) in enumerate(readme_lines, 1):
        cell = ws.cell(row=index, column=1, value=line)
        cell.alignment = Alignment(vertical='top', wrap_text=True)
        if bold:
            cell.font = Font(bold=True, size=12 if index == 1 else 11)

    headers = [
        '#',
        'Area',
        'Priority',
        'Key',
        'English (current)',
        'Amharic (current)',
        'Oromo (current)',
        'Amharic status',
        'Oromo status',
        'Where used',
        'Example line',
        'Notes',
        'Suggested English',
        'Suggested Amharic',
        'Suggested Oromo',
        'Reviewer comment',
    ]
    widths = [5, 20, 24, 34, 46, 46, 46, 22, 28, 46, 60, 48, 36, 36, 36, 36]

    review = workbook.create_sheet('Review')
    style_header(review, headers)
    review_rows = []
    for index, row in enumerate(rows, 1):
        review_rows.append(
            [
                index,
                row['area'],
                row['priority'],
                row['key'],
                row['english'],
                row['amharic'],
                row['oromo'],
                row['am_status'],
                row['om_status'],
                row['where'],
                row['example'],
                row['notes'],
                '',
                '',
                '',
                '',
            ]
        )
    write_rows(review, review_rows, widths, amharic_column=6)
    for row_number, row in enumerate(rows, 2):
        for column in (8, 9):
            fill = status_fill(review.cell(row=row_number, column=column).value or '')
            if fill:
                review.cell(row=row_number, column=column).fill = fill
        if row['priority'] != 'Existing':
            for column in (3, 4):
                review.cell(row=row_number, column=column).fill = DRAFT_FILL

    def filtered_sheet(title: str, predicate) -> None:
        sheet = workbook.create_sheet(title)
        subset = [row for row in rows if predicate(row)]
        style_header(
            sheet,
            [
                '#',
                'Area',
                'Key',
                'English (current)',
                'Amharic (current)',
                'Oromo (current)',
                'Status / note',
                'Where used',
            ],
        )
        values = []
        for index, row in enumerate(subset, 1):
            note = row['om_status'] if title == 'Oromo gaps' else row['am_status']
            values.append(
                [index, row['area'], row['key'], row['english'], row['amharic'], row['oromo'], note, row['where']]
            )
        write_rows(sheet, values, [5, 20, 34, 48, 48, 48, 28, 52], amharic_column=5)

    filtered_sheet('Oromo gaps', lambda row: row['om_status'] != 'Translated')
    filtered_sheet('Amharic gaps', lambda row: row['am_status'] != 'Translated')
    filtered_sheet('Draft keys', lambda row: row['priority'] != 'Existing')

    hardcoded = scan_hardcoded_templates()
    hard = workbook.create_sheet('Hardcoded candidates')
    style_header(
        hard,
        [
            '#',
            'File',
            'Line',
            'Text (not wired to _())',
            'Suggested English',
            'Suggested Amharic',
            'Suggested Oromo',
            'Comment',
        ],
    )
    hard_rows = [[index, rel, number, text, '', '', '', ''] for index, (rel, number, text) in enumerate(hardcoded, 1)]
    write_rows(hard, hard_rows, [5, 44, 7, 60, 36, 36, 36, 36], amharic_column=6)

    dynamic = workbook.create_sheet('Dynamic references')
    style_header(dynamic, ['#', 'Kind', 'Reference'])
    dynamic_rows = [[index, 'get_string', line] for index, line in enumerate(dynamic_get, 1)]
    dynamic_rows += [[len(dynamic_rows) + index, '_()', line] for index, line in enumerate(dynamic_underscore, 1)]
    write_rows(dynamic, dynamic_rows, [5, 14, 150])

    workbook.save(xlsx_path)

    main_headers = ['No.', *headers[1:12]]
    with csv_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(main_headers)
        for index, row in enumerate(rows, 1):
            writer.writerow(
                [
                    index,
                    row['area'],
                    row['priority'],
                    row['key'],
                    row['english'],
                    row['amharic'],
                    row['oromo'],
                    row['am_status'],
                    row['om_status'],
                    row['where'],
                    row['example'],
                    row['notes'],
                ]
            )

    correction_files = []
    for language, current in (('amharic', 'amharic'), ('oromo', 'oromo'), ('english', 'english')):
        path = out_dir / f'corrections_{language}_{args.date}.csv'
        status_column = 'om_status' if language == 'oromo' else 'am_status'
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['key', 'area', 'priority', 'status', 'current_text', 'suggested_text', 'comment'])
            for row in rows:
                writer.writerow([row['key'], row['area'], row['priority'], row[status_column], row[current], '', ''])
        correction_files.append(path)

    readme_lines_md = [
        f'# Payroll UI translation review ({args.date})',
        '',
        f'Generated from `{branch}` at `{commit}`.',
        '',
        '## Files',
        '',
        f'- `{xlsx_path.name}` — main workbook (Review, Oromo gaps, Amharic gaps, Draft keys, Hardcoded candidates, Dynamic references).',
        f'- `{csv_path.name}` — flat copy of the Review sheet, UTF-8 with BOM for Excel.',
        f'- `corrections_amharic_{args.date}.csv` — fill `suggested_text` for Amharic.',
        f'- `corrections_oromo_{args.date}.csv` — fill `suggested_text` for Oromo.',
        f'- `corrections_english_{args.date}.csv` — propose clearer English wording.',
        '',
        '## Counts',
        '',
        f'- Keys: {len(rows)}; Amharic translated {am_translated}, missing {am_missing}.',
        f'- Oromo translated {om_translated}, English fallback {om_fallback}, missing/raw key {om_missing}.',
        f'- Keys with a direct code/template reference: {referenced}; dictionary-only: {unreferenced}.',
        f'- Hardcoded template text candidates (not wired to `_()`): {len(hardcoded)}.',
        '',
        '## How to use',
        '',
        '1. Open the workbook and use the Area/Priority filters, or work screen by screen from `Where used`.',
        '2. Put corrections in the suggested columns (or the per-language CSV). Keep the `key` column unchanged.',
        '3. Do not edit the current English text in code; tests pin existing English bytes.',
        '4. Return the completed CSV/workbook. Corrections are applied as code changes.',
        '',
        '## Screens to check',
        '',
        '- Preparation: `/payroll/spreadsheet`',
        '- Review: `/payroll/runs/<id>/review`',
        '- Employee payslip: `/my/payslips/<id>`',
        '- Sign-in and onboarding: `/auth/login`, `/auth/register`',
        '',
        '## Legend',
        '',
        '- `Translated` — text exists for that language.',
        '- `English fallback (no Oromo)` — no Oromo entry; Oromo UI shows English.',
        '- `MISSING (key shown)` — no entry; UI shows the raw key.',
        '- `Draft` — new prep/review or RC-38000-01 copy, not yet reviewed.',
        '',
        '## Caveats',
        '',
        '- English for legacy keys is title-cased from the key, not stored separately.',
        '- Oromo checks `FIRST_USE_COPY` first; entries for those keys would be ignored (the sets do not overlap today).',
        '- Dynamic runtime keys cannot be resolved statically; see the Dynamic references sheet.',
        '- Hardcoded template text is a review candidate list, not part of the dictionary yet.',
        '- Contexts are file:line at the generation commit and may move after edits.',
    ]
    readme_path = out_dir / 'README.md'
    readme_path.write_text('\n'.join(readme_lines_md) + '\n', encoding='utf-8')
    if len(hardcoded) >= 2000:
        with readme_path.open('a', encoding='utf-8') as handle:
            handle.write('\nThe hardcoded candidate list was capped at 2,000 rows.\n')

    if not args.no_zip:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in (xlsx_path, csv_path, readme_path, *correction_files):
                archive.write(path, arcname=path.name)

    print(f'keys: {len(rows)}')
    print(f'amharic translated/missing: {am_translated}/{am_missing}')
    print(f'oromo translated/fallback/missing: {om_translated}/{om_fallback}/{om_missing}')
    print(f'referenced/unreferenced: {referenced}/{unreferenced}')
    print(f'hardcoded candidates: {len(hardcoded)}')
    print(f'workbook: {xlsx_path}')
    print(f'csv: {csv_path}')
    for path in correction_files:
        print(f'corrections: {path}')
    if not args.no_zip:
        print(f'zip: {zip_path}')
    if dynamic_get or dynamic_underscore:
        print(f'dynamic references: {len(dynamic_get)} get_string, {len(dynamic_underscore)} _()')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
