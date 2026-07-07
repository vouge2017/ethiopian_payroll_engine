"""
Ethiopian Calendar Converter Tests

Verifies Gregorian → Ethiopian date conversion.
Key dates to verify:
- Ethiopian New Year (Meskerem 1) = September 11 (or 12 in Gregorian leap year)
- Known date: July 7, 2026 = Sene 30, 2018
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
from payroll_engine.ethiopian_calendar import (
    gregorian_to_ethiopian,
    format_ethiopian_date,
    format_dual_date,
    get_ethiopian_month_name,
    ETHIOPIAN_MONTHS,
    ETHIOPIAN_MONTHS_EN,
)


# ---------------------------------------------------------------
# TEST 1: Known date conversion
# ---------------------------------------------------------------
def test_known_date_july_7_2026():
    """July 7, 2026 should be Sene 30, 2018 in Ethiopian calendar."""
    greg = date(2026, 7, 7)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018, f"Expected year 2018, got {eth_year}"
    assert eth_month == 10, f"Expected month 10 (Sene), got {eth_month}"
    assert eth_day == 30, f"Expected day 30, got {eth_day}"


# ---------------------------------------------------------------
# TEST 2: Ethiopian New Year (non-leap Gregorian year)
# ---------------------------------------------------------------
def test_ethiopian_new_year_non_leap():
    """September 11, 2025 = Meskerem 1, 2018."""
    greg = date(2025, 9, 11)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018
    assert eth_month == 1
    assert eth_day == 1


# ---------------------------------------------------------------
# TEST 3: Ethiopian New Year (leap Gregorian year)
# ---------------------------------------------------------------
def test_ethiopian_new_year_leap():
    """September 12, 2024 = Meskerem 1, 2017."""
    greg = date(2024, 9, 12)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2017
    assert eth_month == 1
    assert eth_day == 1


# ---------------------------------------------------------------
# TEST 4: Day before Ethiopian New Year
# ---------------------------------------------------------------
def test_day_before_new_year():
    """September 10, 2025 = Pagume 5 or 6, 2017."""
    greg = date(2025, 9, 10)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2017
    assert eth_month == 13  # Pagume


# ---------------------------------------------------------------
# TEST 5: January date (belongs to previous Ethiopian year)
# ---------------------------------------------------------------
def test_january_date():
    """January 1, 2026 = Tahsas 22, 2018."""
    greg = date(2026, 1, 1)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018
    assert eth_month == 4  # Tahsas


# ---------------------------------------------------------------
# TEST 6: Format Amharic
# ---------------------------------------------------------------
def test_format_amharic():
    greg = date(2026, 7, 7)
    result = format_ethiopian_date(greg, language='am')
    assert 'ሰኔ' in result
    assert '2018' in result


# ---------------------------------------------------------------
# TEST 7: Format English
# ---------------------------------------------------------------
def test_format_english():
    greg = date(2026, 7, 7)
    result = format_ethiopian_date(greg, language='en')
    assert 'Sene' in result
    assert '2018' in result


# ---------------------------------------------------------------
# TEST 8: Dual date format
# ---------------------------------------------------------------
def test_dual_date():
    greg = date(2026, 7, 7)
    result = format_dual_date(greg)
    assert 'ሰኔ' in result  # Amharic month
    assert 'Jul' in result   # English month
    assert '2026' in result  # Gregorian year
    assert '2018' in result  # Ethiopian year


# ---------------------------------------------------------------
# TEST 9: Month name lookup
# ---------------------------------------------------------------
def test_month_name_amharic():
    assert get_ethiopian_month_name(1, 'am') == 'መስከረም'
    assert get_ethiopian_month_name(10, 'am') == 'ሰኔ'
    assert get_ethiopian_month_name(13, 'am') == 'ጳጉሜ'


def test_month_name_english():
    assert get_ethiopian_month_name(1, 'en') == 'Meskerem'
    assert get_ethiopian_month_name(10, 'en') == 'Sene'
    assert get_ethiopian_month_name(13, 'en') == 'Pagume'


def test_month_name_invalid():
    assert get_ethiopian_month_name(0, 'am') == ''
    assert get_ethiopian_month_name(14, 'am') == ''


# ---------------------------------------------------------------
# TEST 10: All 13 months exist
# ---------------------------------------------------------------
def test_all_months_exist():
    assert len(ETHIOPIAN_MONTHS) == 13
    assert len(ETHIOPIAN_MONTHS_EN) == 13
    for i in range(13):
        assert ETHIOPIAN_MONTHS[i] != ''
        assert ETHIOPIAN_MONTHS_EN[i] != ''


# ---------------------------------------------------------------
# TEST 11: Leap year detection
# ---------------------------------------------------------------
def test_leap_year():
    from payroll_engine.ethiopian_calendar import _is_gregorian_leap_year
    assert _is_gregorian_leap_year(2024) == True
    assert _is_gregorian_leap_year(2025) == False
    assert _is_gregorian_leap_year(2000) == True
    assert _is_gregorian_leap_year(1900) == False
