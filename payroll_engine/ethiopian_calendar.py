"""
Ethiopian Calendar Converter

Converts Gregorian dates to Ethiopian calendar dates.

Ethiopian Calendar:
- 13 months: 12 months of 30 days + Pagume (5 or 6 days)
- Year starts on Meskerem 1 = September 11 (or September 12 in Gregorian leap years)
- Ethiopian year is 7-8 years behind Gregorian
- Months: Meskerem, Tikimt, Hidar, Tahsas, Ter, Yekatit, Megabit,
  Miyazia, Ginbot, Sene, Hamle, Nehase, Pagume

Reference: Ethiopian calendar epoch = August 29, 7 CE (Julian)
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


def _is_gregorian_leap_year(year: int) -> bool:
    """Check if a Gregorian year is a leap year."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def gregorian_to_ethiopian(greg_date: date) -> Tuple[int, int, int]:
    """
    Convert a Gregorian date to Ethiopian calendar (year, month, day).

    Args:
        greg_date: Gregorian date object

    Returns:
        Tuple of (ethiopian_year, ethiopian_month, ethiopian_day)
        Month is 1-indexed (1=Meskerem, 13=Pagume)
    """
    # Ethiopian new year in Gregorian:
    # Sep 11 in non-leap Gregorian years, Sep 12 in leap Gregorian years
    # The Ethiopian year that starts in September YYYY is YYYY - 7 (or -8)

    year = greg_date.year
    month = greg_date.month
    day = greg_date.day

    # Determine Ethiopian new year date for this Gregorian year
    # Ethiopian new year is September 11 (or 12 if Gregorian year is leap)
    if _is_gregorian_leap_year(year):
        new_year_greg = date(year, 9, 12)
    else:
        new_year_greg = date(year, 9, 11)

    # If date is before Ethiopian new year, it belongs to previous Ethiopian year
    if greg_date < new_year_greg:
        eth_year = year - 8
        # Calculate days from previous Ethiopian new year to this date
        prev_new_year = date(year - 1, 9, 12) if _is_gregorian_leap_year(year - 1) else date(year - 1, 9, 11)
        days_from_new_year = (greg_date - prev_new_year).days
    else:
        eth_year = year - 7
        days_from_new_year = (greg_date - new_year_greg).days

    # Convert days to Ethiopian month and day
    # First 12 months have 30 days each, Pagume has 5 or 6
    if days_from_new_year < 0:
        # Edge case: should not happen with correct calculation above
        days_from_new_year = 0

    # Calculate month (1-indexed)
    eth_month = (days_from_new_year // 30) + 1
    if eth_month > 13:
        eth_month = 13

    # Calculate day within the month
    eth_day = (days_from_new_year % 30) + 1

    # Handle Pagume (month 13): 5 days normally, 6 in Ethiopian leap year
    # Ethiopian leap year: year % 4 == 3
    if eth_month == 13:
        pagume_days = 6 if (eth_year % 4 == 3) else 5
        if eth_day > pagume_days:
            # This shouldn't happen, but handle gracefully
            eth_day = pagume_days

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
