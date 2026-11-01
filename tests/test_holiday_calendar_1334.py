"""Holiday calendar per Public Holidays Proc. 1334/2024.

Pins the corrected national holiday data:
  - Patriots' Victory Day is May 5 (Art. 4); the old seed wrongly put it on
    May 28 together with the abolished "Downfall of the Dergue".
  - May 28 is no longer a public holiday at all.
  - Dec 9 (Nations/Nationalities Day) and Feb 20 (Martyrs' Day) are Art. 5
    memorial days: institutions open, NOT days off.
  - Enkutatash/Meskel shift to Sep 12/Sep 28 in 2027 (the year before the
    2028 Gregorian leap year) — timeanddate.com, officeholidays.com and
    clockit.io all agree.
  - Orthodox Good Friday/Easter via the Julian computus: 2025-04-20,
    2026-04-12, 2027-05-02 (Good Friday Apr 30, 2027 crosses the month).
  - Lunar holidays (Mawlid, Eid al-Fitr, Eid al-Adha) are statutory (Art. 6)
    but are NOT seeded: public aggregator sources conflict on the Gregorian
    dates, so they are recorded per official announcement through
    add_national_holiday(). Until then they count as working days — a
    documented limitation (PLAN.md), not a claim that they are workdays.

Existing databases get the corrected rows from data migration
``h1334c2024a1`` (executed by the PostgreSQL CI chain); the seed itself never
resurrects the abolished May 28 rows.
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from payroll_engine import create_app, db
from payroll_engine.holidays import (
    BASE_YEARS,
    add_national_holiday,
    get_working_days,
    is_gregorian_leap,
    is_holiday,
    national_holidays,
    orthodox_easter,
    seed_holidays,
)


def _by_name(year):
    return {h['name']: h['date'] for h in national_holidays(year)}


def _dates(year):
    return {h['date'] for h in national_holidays(year)}


class TestGregorianMapping:
    def test_leap_years(self):
        assert is_gregorian_leap(2024)
        assert is_gregorian_leap(2028)
        assert not is_gregorian_leap(2025)
        assert not is_gregorian_leap(2027)

    def test_orthodox_easter_pinned(self):
        assert orthodox_easter(2025) == date(2025, 4, 20)
        assert orthodox_easter(2026) == date(2026, 4, 12)
        assert orthodox_easter(2027) == date(2027, 5, 2)

    def test_nine_closed_holidays_per_year(self):
        for year in BASE_YEARS:
            assert len(national_holidays(year)) == 9, year

    def test_patriots_on_may5_and_may28_gone(self):
        for year in BASE_YEARS:
            by = _by_name(year)
            assert by["Patriots' Victory Day"] == date(year, 5, 5)
            assert 'Downfall of the Dergue' not in by
            assert date(year, 5, 28) not in _dates(year)

    def test_memorial_days_are_not_holidays(self):
        # Art. 5: institutions stay open on Feb 20 and Dec 9.
        for year in BASE_YEARS:
            assert date(year, 2, 20) not in _dates(year)
            assert date(year, 12, 9) not in _dates(year)

    def test_september_shift_2027(self):
        assert _by_name(2027)['Enkutatash (New Year)'] == date(2027, 9, 12)
        assert _by_name(2027)['Finding of the True Cross'] == date(2027, 9, 28)
        assert _by_name(2025)['Enkutatash (New Year)'] == date(2025, 9, 11)
        assert _by_name(2026)['Enkutatash (New Year)'] == date(2026, 9, 11)
        assert _by_name(2025)['Finding of the True Cross'] == date(2025, 9, 27)
        assert _by_name(2026)['Finding of the True Cross'] == date(2026, 9, 27)

    def test_good_friday_is_two_days_before_easter(self):
        for year in BASE_YEARS:
            by = _by_name(year)
            assert by['Ethiopian Good Friday'] == by['Ethiopian Easter'] - timedelta(days=2)

    def test_may_2026_weekdays_used_for_working_day_count(self):
        # Sanity for the DB test below: May 1 2026 is a Friday, May 5 a Tuesday.
        assert date(2026, 5, 1).weekday() == 4
        assert date(2026, 5, 5).weekday() == 1


class TestSeededDatabase:
    @pytest.fixture
    def app(self):
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()

    def test_seed_makes_may5_a_holiday_and_may28_not(self, app):
        assert seed_holidays([2025, 2026, 2027]) == 27
        assert is_holiday(date(2026, 5, 5)) is True
        assert is_holiday(date(2025, 5, 5)) is True
        assert is_holiday(date(2026, 5, 28)) is False
        assert is_holiday(date(2025, 12, 9)) is False
        assert is_holiday(date(2025, 2, 20)) is False

    def test_seed_is_idempotent(self, app):
        seed_holidays([2025, 2026, 2027])
        assert seed_holidays([2025, 2026, 2027]) == 0

    def test_seed_never_resurrects_the_abolished_day(self, app):
        # A database seeded by the old code still carries a May 28 "Downfall
        # of the Dergue" row (its removal is the job of migration
        # h1334c2024a1, run by the PostgreSQL CI chain). The corrected seed
        # must add exactly the corrected nine and must not add its own
        # abolished-day row.
        from payroll_engine.models import Holiday

        def derg_rows():
            return Holiday.query.filter_by(company_id=None, is_national=True, name='Downfall of the Dergue').count()

        db.session.add(
            Holiday(
                company_id=None,
                name='Downfall of the Dergue',
                name_am='ደርግ የወደቀበት ቀን',
                holiday_date=date(2026, 5, 28),
                is_national=True,
                is_recurring=False,
                description='Ethiopian national holiday',
            )
        )
        db.session.commit()
        assert derg_rows() == 1  # the legacy row, as an old DB would have it
        added = seed_holidays([2026])
        assert added == 9  # the corrected nine only
        assert derg_rows() == 1  # unchanged: the seed did not add one

    def test_add_national_holiday_records_lunar_dates(self, app):
        created = add_national_holiday(
            'Eid al-Fitr',
            date(2026, 3, 20),
            name_am='ዒድ አል-ፈጥር',
            description='Officially announced (example date)',
        )
        assert created is not None
        assert is_holiday(date(2026, 3, 20)) is True
        assert add_national_holiday('Eid al-Fitr', date(2026, 3, 20)) is None

    def test_working_days_may_2026(self, app):
        seed_holidays([2026])
        # 31 days - 5 Sundays - May 1 (Workers) - May 5 (Patriots).
        # Eid al-Adha 2026 (~May 27) is intentionally absent: lunar, not yet
        # announced/recorded — the documented limitation above.
        assert get_working_days(2026, 5) == 24


def _seeded_rows():
    from payroll_engine.models import Holiday

    return Holiday.query.filter_by(company_id=None, is_national=True).all()


def _derg_row_count():
    from payroll_engine.models import Holiday

    return Holiday.query.filter_by(company_id=None, is_national=True, name='Downfall of the Dergue').count()
