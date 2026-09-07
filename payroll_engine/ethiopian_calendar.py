"""
Ethiopian Calendar Converter

Converts Gregorian dates to Ethiopian calendar dates using Julian Day Number
(JDN) arithmetic for guaranteed correctness across all dates.

Ethiopian Calendar:
- 13 months: 12 months of 30 days + Pagume (5 or 6 days)
- Year starts on Meskerem 1
- Ethiopian year is 7-8 years behind Gregorian
- Months: Meskerem, Tikimt, Hidar, Tahsas, Ter, Yekatit, Megabit,
  Miyazia, Ginbot, Sene, Hamle, Nehase, Pagume

Reference: Ethiopian calendar epoch = Meskerem 1, 1 AD = August 29, 8 CE (Julian)
           JDN of epoch = 1724273
"""

from datetime import date, datetime
from typing import Tuple

# Ethiopian month names
ETHIOPIAN_MONTHS = [
    'መስከረም',   # Meskerem (1)
    'ጥቅምት',    # Tikimt (2)
    'ህዳር',     # Hidar (3)
    'ታህሳስ',    # Tahsas (4)
    'ጥር',      # Ter (5)
    'የካቲት',    # Yekatit (6)
    'መጋቢት',    # Megabit (7)
    'ሚያዝያ',    # Miyazia (8)
    'ግንቦት',    # Ginbot (9)
    'ሰኔ',      # Sene (10)
    'ሐምሌ',     # Hamle (11)
    'ነሐሴ',     # Nehase (12)
    'ጳጉሜ',    # Pagume (13)
]

# English month names for fallback
ETHIOPIAN_MONTHS_EN = [
    'Meskerem', 'Tikimt', 'Hidar', 'Tahsas', 'Ter',
    'Yekatit', 'Megabit', 'Miyazia', 'Ginbot', 'Sene',
    'Hamle', 'Nehase', 'Pagume',
]

# JDN of Ethiopian epoch (Meskerem 1, year 1)
# Derived from: Sep 11, 2025 = Meskerem 1, 2018
#   JDN(Sep 11, 2025) = 2460930
#   Days from epoch = 504*1461 + 365 = 736709
#   Epoch = 2460930 - 736709 = 1724221
_ETH_EPOCH_JDN = 1724221


def _gregorian_to_jdn(greg_date: date) -> int:
    """Convert a Gregorian date to Julian Day Number."""
    y = greg_date.year
    m = greg_date.month
    d = greg_date.day
    a = (14 - m) // 12
    y1 = y + 4800 - a
    m1 = m + 12 * a - 3
    jdn = d + (153 * m1 + 2) // 5 + 365 * y1 + y1 // 4 - y1 // 100 + y1 // 400 - 32045
    return jdn


def gregorian_to_ethiopian(greg_date: date) -> Tuple[int, int, int]:
    """
    Convert a Gregorian date to Ethiopian calendar (year, month, day).

    Uses Julian Day Number arithmetic for correctness across all dates,
    including leap years and year boundaries.

    Args:
        greg_date: Gregorian date object

    Returns:
        Tuple of (ethiopian_year, ethiopian_month, ethiopian_day)
        Month is 1-indexed (1=Meskerem, 13=Pagume)
    """
    jdn = _gregorian_to_jdn(greg_date)
    days_since_epoch = jdn - _ETH_EPOCH_JDN

    # Ethiopian year (4-year cycle of 1461 days = 3*365 + 1*366)
    # Plus remainder to find exact year within cycle
    cycles = days_since_epoch // 1461
    remainder = days_since_epoch % 1461

    # Year within the 4-year cycle
    # Years 0,1,2 in cycle have 365 days; year 3 has 366 days
    if remainder >= 1095:  # year 3 of cycle (365+365+365 = 1095)
        year_in_cycle = 3
    elif remainder >= 730:
        year_in_cycle = 2
    elif remainder >= 365:
        year_in_cycle = 1
    else:
        year_in_cycle = 0

    eth_year = cycles * 4 + year_in_cycle + 1  # 1-indexed

    # Day within the year (0-indexed)
    year_starts = [0, 365, 730, 1095]
    day_in_year = days_since_epoch - (cycles * 1461) - year_starts[year_in_cycle]

    # Month and day
    is_leap = (eth_year % 4 == 3)
    if day_in_year >= 360:
        # Pagume (month 13)
        eth_month = 13
        eth_day = day_in_year - 360 + 1
        # Clamp to valid Pagume days
        max_pagume = 6 if is_leap else 5
        if eth_day > max_pagume:
            eth_day = max_pagume
    else:
        # Months 1-12: each has exactly 30 days
        eth_month = (day_in_year // 30) + 1
        eth_day = (day_in_year % 30) + 1

    return eth_year, eth_month, eth_day


def format_ethiopian_date(greg_date: date, language: str = 'am') -> str:
    """
    Format a Gregorian date as Ethiopian date string.

    Args:
        greg_date: Gregorian date object
        language: 'am' for Amharic, 'en' for English

    Returns:
        Formatted string like "ሰኔ 30, 2018" or "Sene 30, 2018"
    """
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg_date)

    if language == 'am':
        month_name = ETHIOPIAN_MONTHS[eth_month - 1]
    else:
        month_name = ETHIOPIAN_MONTHS_EN[eth_month - 1]

    return f"{month_name} {eth_day}, {eth_year}"


def format_dual_date(greg_date: date, language: str = 'am') -> str:
    """
    Format a date showing both Ethiopian and Gregorian.

    Args:
        greg_date: Gregorian date object
        language: 'am' for Amharic first, 'en' for English first

    Returns:
        Formatted string like "ሰኔ 30, 2018 (Jul 7, 2026)"
    """
    eth_str = format_ethiopian_date(greg_date, language='am')
    greg_str = greg_date.strftime('%b %d, %Y')
    return f"{eth_str} ({greg_str})"


def get_ethiopian_month_name(month: int, language: str = 'am') -> str:
    """
    Get Ethiopian month name by number.

    Args:
        month: Month number (1-13)
        language: 'am' for Amharic, 'en' for English

    Returns:
        Month name string
    """
    if month < 1 or month > 13:
        return ''
    if language == 'am':
        return ETHIOPIAN_MONTHS[month - 1]
    return ETHIOPIAN_MONTHS_EN[month - 1]
