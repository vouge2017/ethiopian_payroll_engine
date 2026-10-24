"""
Ethiopian Calendar Converter Tests

Verifies Gregorian -> Ethiopian date conversion using JDN arithmetic.
Key facts:
- Ethiopian New Year (Meskerem 1) = September 11 in Gregorian years,
  EXCEPT the day after an Ethiopian leap year (year % 4 == 3, Pagume 6),
  when New Year falls on September 12 (real-world anchor: Meskerem 1,
  2016 EC = 2023-09-12, Ethiopian News Agency).
- Known date: July 7, 2026 = Sene 30, 2018
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta

from payroll_engine.ethiopian_calendar import (
    ETHIOPIAN_MONTHS,
    ETHIOPIAN_MONTHS_EN,
    format_dual_date,
    format_ethiopian_date,
    get_ethiopian_month_name,
    gregorian_to_ethiopian,
)


# ---------------------------------------------------------------
# TEST 1: Known date conversion
# ---------------------------------------------------------------
def test_known_date_july_7_2026():
    """July 7, 2026 should be Sene 30, 2018 in Ethiopian calendar."""
    greg = date(2026, 7, 7)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018, f'Expected year 2018, got {eth_year}'
    assert eth_month == 10, f'Expected month 10 (Sene), got {eth_month}'
    assert eth_day == 30, f'Expected day 30, got {eth_day}'


# ---------------------------------------------------------------
# TEST 2: Ethiopian New Year
# ---------------------------------------------------------------
def test_ethiopian_new_year_non_leap():
    """September 11, 2025 = Meskerem 1, 2018."""
    greg = date(2025, 9, 11)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018
    assert eth_month == 1
    assert eth_day == 1


# ---------------------------------------------------------------
# TEST 3: Ethiopian New Year (2024)
# ---------------------------------------------------------------
def test_ethiopian_new_year_2024():
    """September 11, 2024 = Meskerem 1, 2017."""
    greg = date(2024, 9, 11)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2017
    assert eth_month == 1
    assert eth_day == 1


# ---------------------------------------------------------------
# TEST 4: Day before Ethiopian New Year
# ---------------------------------------------------------------
def test_day_before_new_year():
    """September 10, 2025 = Pagume 5, 2017 (last day of year)."""
    greg = date(2025, 9, 10)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2017
    assert eth_month == 13  # Pagume
    assert eth_day == 5


# ---------------------------------------------------------------
# TEST 5: January date (belongs to previous Ethiopian year)
# ---------------------------------------------------------------
def test_january_date():
    """January 1, 2026 = Tahsas 23, 2018."""
    greg = date(2026, 1, 1)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018
    assert eth_month == 4  # Tahsas
    assert eth_day == 23


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
    assert 'Jul' in result  # English month
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
# TEST 11: Year boundary dates
# ---------------------------------------------------------------
def test_year_boundary_pagume():
    """Sep 6, 2026 = Pagume 1, 2018 (first day of Pagume)."""
    greg = date(2026, 9, 6)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018
    assert eth_month == 13  # Pagume
    assert eth_day == 1


def test_year_boundary_last_day():
    """Sep 10, 2026 = Pagume 5, 2018 (last day of year 2018)."""
    greg = date(2026, 9, 10)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2018
    assert eth_month == 13
    assert eth_day == 5


def test_leap_year_2015():
    """Ethiopian year 2015 is a leap year (2015 % 4 == 3).

    Pagume has 6 days: Sep 10, 2023 = Pagume 5, Sep 11, 2023 = Pagume 6
    (last day of year 2015), and New Year 2016 falls on Sep 12, 2023
    (real-world anchor: Ethiopian News Agency, 2016-09-12).
    """
    # Sep 10 = Pagume 5
    greg = date(2023, 9, 10)
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg)
    assert eth_year == 2015
    assert eth_month == 13
    assert eth_day == 5
    # Sep 11 = Pagume 6 (the leap day)
    ey, em, ed = gregorian_to_ethiopian(date(2023, 9, 11))
    assert ey == 2015
    assert em == 13
    assert ed == 6
    # Sep 12 = Meskerem 1, 2016 (new year starts; celebrated worldwide this day)
    greg2 = date(2023, 9, 12)
    ey2, em2, ed2 = gregorian_to_ethiopian(greg2)
    assert ey2 == 2016
    assert em2 == 1
    assert ed2 == 1


def test_leap_year_2019_boundary():
    """Year 2019 EC is leap: Pagume 6 on Sep 11, 2027; NY 2020 on Sep 12, 2027."""
    ey, em, ed = gregorian_to_ethiopian(date(2027, 9, 11))
    assert ey == 2019 and em == 13 and ed == 6
    ey2, em2, ed2 = gregorian_to_ethiopian(date(2027, 9, 12))
    assert ey2 == 2020 and em2 == 1 and ed2 == 1


def test_non_leap_new_year_2019():
    """September 11, 2026 = Meskerem 1, 2019 (Enkutatash table anchor)."""
    ey, em, ed = gregorian_to_ethiopian(date(2026, 9, 11))
    assert ey == 2019 and em == 1 and ed == 1


def test_every_year_has_exactly_365_or_366_days_and_pagume_shape():
    """Property: for 2012-2035 every EC year has 365 days (Pagume 5) when
    year % 4 != 3, and 366 days (Pagume 6 reaching day 365) when year % 4 == 3;
    all months 1-12 have 30 days; Pagume days are 1..5 or 1..6.

    The pre-fix converter produced day labels 1 day shifted for ~25% of days
    sampled (1460/5844 in 2020-2035 mismatched the classic formula).
    """
    start = date(2019, 9, 12)  # Meskerem 1, 2012 (year after leap 2011)
    d = start
    end = date(2035, 9, 11)  # Pagume 6, 2027 (last day of year 2027)
    counts: dict[int, int] = {}
    seen: set[tuple[int, int, int]] = set()
    while d <= end:
        ey, em, ed = gregorian_to_ethiopian(d)
        assert (ey, em, ed) not in seen, f'duplicate mapping {d} -> {(ey, em, ed)}'
        seen.add((ey, em, ed))
        counts[ey] = counts.get(ey, 0) + 1
        assert 1 <= em <= 13
        if em <= 12:
            assert 1 <= ed <= 30
        else:
            assert 1 <= ed <= (6 if ey % 4 == 3 else 5), (ey, ed)
        d += timedelta(days=1)
    for ey in range(2012, 2028):
        expected = 366 if ey % 4 == 3 else 365
        assert counts.get(ey) == expected, f'year {ey}: {counts.get(ey)} != {expected}'


def test_known_dates_stay_stable():
    """Mid-year sanity anchors unchanged after the converter rewrite."""
    assert gregorian_to_ethiopian(date(2026, 7, 7)) == (2018, 10, 30)
    assert gregorian_to_ethiopian(date(2026, 1, 1)) == (2018, 4, 23)
    assert gregorian_to_ethiopian(date(2026, 10, 21)) == (2019, 2, 11)
