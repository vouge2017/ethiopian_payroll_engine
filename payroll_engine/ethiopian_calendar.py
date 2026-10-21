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

Leap-year rule (verified against real-world anchors, 2026-10-21):
- Ethiopian years with year % 4 == 3 (e.g. 2011, 2015, 2019) are leap years
  and have 6 Pagume days.
- Meskerem 1 therefore falls on September 11 in Gregorian years, EXCEPT the
  day after a Pagume 6, when New Year falls on September 12.
- World-verified anchor: Meskerem 1, 2016 EC = September 12, 2023
  (Ethiopian News Agency, "Ethiopians ... celebrating the 2016 Ethiopian New
  Year that started on the 12th of September", ena.et, 2023-09-12).

Implementation uses the classic Ethiopic JDN formula (epoch JDN 1723856),
which reproduces every real-world anchor above and a 2020-2035 sweep:
Sep 11, 2025 = Meskerem 1, 2018; Sep 11, 2026 = Meskerem 1, 2019;
Sep 11, 2023 = Pagume 6, 2015; Sep 12, 2023 = Meskerem 1, 2016;
Sep 11, 2027 = Pagume 6, 2019; Sep 12, 2027 = Meskerem 1, 2020.
"""

from datetime import date

# Ethiopian month names
ETHIOPIAN_MONTHS = [
    'መስከረም',  # Meskerem (1)
    'ጥቅምት',  # Tikimt (2)
    'ህዳር',  # Hidar (3)
    'ታህሳስ',  # Tahsas (4)
    'ጥር',  # Ter (5)
    'የካቲት',  # Yekatit (6)
    'መጋቢት',  # Megabit (7)
    'ሚያዝያ',  # Miyazia (8)
    'ግንቦት',  # Ginbot (9)
    'ሰኔ',  # Sene (10)
    'ሐምሌ',  # Hamle (11)
    'ነሐሴ',  # Nehase (12)
    'ጳጉሜ',  # Pagume (13)
]

# English month names for fallback
ETHIOPIAN_MONTHS_EN = [
    'Meskerem',
    'Tikimt',
    'Hidar',
    'Tahsas',
    'Ter',
    'Yekatit',
    'Megabit',
    'Miyazia',
    'Ginbot',
    'Sene',
    'Hamle',
    'Nehase',
    'Pagume',
]

# Epoch used by the classic Ethiopic JDN formula (see module docstring).
_ETH_JDN_EPOCH = 1723856


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


def gregorian_to_ethiopian(greg_date: date) -> tuple[int, int, int]:
    """
    Convert a Gregorian date to Ethiopian calendar (year, month, day).

    Uses the classic Ethiopic Julian Day Number formula for correctness
    across all dates, including Pagume 6 after Ethiopian leap years
    (year % 4 == 3) and the September 12 New-Year boundaries that follow.

    Args:
        greg_date: Gregorian date object

    Returns:
        Tuple of (ethiopian_year, ethiopian_month, ethiopian_day)
        Month is 1-indexed (1=Meskerem, 13=Pagume)
    """
    jd = _gregorian_to_jdn(greg_date) - _ETH_JDN_EPOCH
    r = jd % 1461
    # Day within the Ethiopian year (0-indexed); leap-day years (Pagume 6)
    # keep 366 days through the (r % 365) + 365 * (r // 1460) term.
    day_in_year = (r % 365) + 365 * (r // 1460)
    eth_year = 4 * (jd // 1461) + (r // 365) - (r // 1460)

    is_leap = eth_year % 4 == 3
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

    return f'{month_name} {eth_day}, {eth_year}'


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
    return f'{eth_str} ({greg_str})'


def format_ethiopian_period(greg_date: date, include_gregorian: bool = True) -> str:
    """
    Ethiopian-first period (month/year) label.

    Args:
        greg_date: Gregorian date object (any day of the month)
        include_gregorian: append the Gregorian month/year fallback

    Returns:
        Formatted string like 'ጥቅምት 2019 · Gregorian October 2026'
    """
    eth_year, eth_month, _ = gregorian_to_ethiopian(greg_date)
    eth_str = f'{ETHIOPIAN_MONTHS[eth_month - 1]} {eth_year} ዓ.ም.'
    if include_gregorian:
        return f'{eth_str} · Gregorian {greg_date.strftime("%B %Y")}'
    return eth_str


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
