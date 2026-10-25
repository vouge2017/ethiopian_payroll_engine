"""Guard the Amharic payroll labels (PLAN.md Next item 7).

The 2026-10-25 audit found nonsense Amharic on payslip items (employer pension
printed as 'ፀጉሮች', which means 'hairs'). These tests pin the corrected
statutory labels and stop the known-bad strings from coming back.
"""

from pathlib import Path

from payroll_engine.catalog import COMPANY_TEMPLATE_ITEMS, SYSTEM_ITEMS
from payroll_engine.i18n import STRINGS
from payroll_engine.rule_source import RULE_SOURCES

ROOT = Path(__file__).resolve().parent.parent / 'payroll_engine'

KNOWN_BAD = (
    'ቀሜታ',
    'ፀጉሮች',
    'የእጅሮ ስሚስ',
    'ኢትዮጵያ የህብረተሰብ መረጃ',
    'ስያፍ',
    'የሰዓት ወጪ',
    'ብረት መፍፍፍያ',
    'ቤት መቀመጫ',
    'ፈተና ስርዓት',
    'የሚተካ ገቢ',
    'የግል ማስታገሻ',
    'የተቀረ',
    'የፋንድ ተጠቃሚ',
    'ጠቅላይ',
    'የስራ ማቆያ',
    'እንኳታሽ',
)


def _by_key(items):
    return {item['key']: item for item in items}


def test_statutory_system_item_labels():
    items = _by_key(SYSTEM_ITEMS)
    assert items['basic_salary']['name_am'] == 'መሠረታዊ ደመወዝ'
    assert items['employee_pension']['name_am'] == 'የሠራተኛ የጡረታ መዋጮ 7%'
    assert items['employer_pension']['name_am'] == 'የአሠሪ የጡረታ መዋጮ 11%'
    assert items['income_tax']['name_am'] == 'የገቢ ግብር'


def test_every_catalog_item_has_amharic_label():
    for item in SYSTEM_ITEMS + COMPANY_TEMPLATE_ITEMS:
        label = (item.get('name_am') or '').strip()
        assert label, f'{item["key"]}: empty Amharic label'
        assert label != item['name_en'], f'{item["key"]}: Amharic label is the English one'


def test_allowance_items_use_abel():
    for item in COMPANY_TEMPLATE_ITEMS:
        if item['name_en'].endswith('Allowance'):
            assert item['name_am'].endswith('አበል'), f'{item["key"]}: {item["name_am"]!r} should say አበል'
        if item['name_en'] == 'Per Diem':
            assert item['name_am'] == 'የውሎ አበል'


def test_no_known_bad_or_corrupted_amharic_in_source():
    files = list(ROOT.rglob('*.py')) + list((ROOT / 'templates').rglob('*.html'))
    for path in files:
        text = path.read_text(encoding='utf-8')
        assert '\ufffd' not in text, f'{path}: contains a U+FFFD replacement character'
        for bad in KNOWN_BAD:
            assert bad not in text, f'{path}: contains known-bad Amharic {bad!r}'


def test_pension_before_tax_copy_is_neutral():
    for key in ('pension_before_tax', 'tax_explainer_intro'):
        text = STRINGS[key]
        assert 'የተለመደው' not in text, f'{key} still asserts the old rule as common practice'
        assert 'RC-38000-01' in text


def test_rule_source_amharic_names_clean():
    assert RULE_SOURCES['pension_employer_rate'].name_am == 'የአሠሪ የጡረታ መዋጮ ተመን'
    assert RULE_SOURCES['tax_brackets'].name_am == 'የገቢ ግብር ደረጃዎች'
