"""Correct national holidays per Public Holidays Proc. 1334/2024.

Data migration, no schema change.

Proc. 1334/2024 (gazette No. 55, 14 Aug 2024) changed the holiday calendar:
Patriots' Victory Day is May 5 (Art. 4), May 28 (Downfall of the Derg) is no
longer a public holiday, and Dec 9 (Nations/Nationalities Day) plus Feb 20
(Martyrs' Day) are memorial days only — institutions open, NOT days off
(Art. 5). The old seed data wrongly put "Patriots' Victory Day" AND "Downfall
of the Dergue" on May 28 of 2025 and 2026, so May 28 was treated as a holiday
and May 5 as a working day.

Upgrade:
  1. Deletes the wrongly seeded national rows: every "Downfall of the Dergue"
     row, and "Patriots' Victory Day" rows not on May 5.
  2. Seeds the corrected closed-holiday list for 2025-2027 (insert-if-absent,
     idempotent): the nine Proc. 1334/2024 Art. 4/Art. 6 holidays, including
     the 2027 September shift (Enkutatash Sep 12, Meskel Sep 28 — year before
     the 2028 Gregorian leap year) and Orthodox Easter via the Julian
     computus (2025-04-20, 2026-04-12, 2027-05-02).
  3. Lunar holidays (Mawlid, Eid al-Fitr, Eid al-Adha) are statutory
     (Art. 6) but their Gregorian dates are only fixed by official
     announcement and public sources conflict — they are deliberately NOT
     invented here. Record them per announcement with
     payroll_engine.holidays.add_national_holiday(). Until recorded they are
     counted as working days (documented limitation, PLAN.md).

Downgrade is a deliberate no-op: restoring abolished May 28 holidays would
corrupt current-year payroll data.
"""

from datetime import date, timedelta

import sqlalchemy as sa
from alembic import op

revision = 'h1334c2024a1'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None

# (name, name_am, (year, month, day), description) — mirrors
# payroll_engine.holidays.national_holidays(); inlined because migrations
# must not import the app package.
_CORRECTED = []
for _year, _easter in ((2025, (4, 20)), (2026, (4, 12)), (2027, (5, 2))):
    _easter_date = date(_year, _easter[0], _easter[1])
    _good_friday = _easter_date - timedelta(days=2)
    _sep_day = 12 if _year == 2027 else 11  # 1 Meskerem shift before leap 2028
    _CORRECTED += [
        ('Ethiopian Christmas', 'ገና', (_year, 1, 7), 'Gena, 29 Tahsas — Public Holidays Proc. 1334/2024 Art. 6'),
        ('Epiphany', 'ጥምቀት', (_year, 1, 19), 'Timket, 11 Ter — Public Holidays Proc. 1334/2024 Art. 6'),
        ('Adwa Victory Day', 'የአድዋ ድል በዓል', (_year, 3, 2), '23 Megabit — Public Holidays Proc. 1334/2024 Art. 4'),
        (
            'Ethiopian Good Friday',
            'ስቅለት',
            (_good_friday.year, _good_friday.month, _good_friday.day),
            'Siklet (movable) — Public Holidays Proc. 1334/2024 Art. 6',
        ),
        (
            'Ethiopian Easter',
            'ፋሲካ',
            (_easter_date.year, _easter_date.month, _easter_date.day),
            'Fasika (movable) — Public Holidays Proc. 1334/2024 Art. 6',
        ),
        ("International Workers' Day", 'የሰራተኞች ቀን', (_year, 5, 1), 'Public Holidays Proc. 1334/2024 Art. 4'),
        (
            "Patriots' Victory Day",
            'የአርበኞች ድል በዓል',
            (_year, 5, 5),
            'Public Holidays Proc. 1334/2024 Art. 4 (was wrongly May 28 before 2024)',
        ),
        (
            'Enkutatash (New Year)',
            'እንቁጣጣሽ',
            (_year, 9, _sep_day),
            '1 Meskerem — Public Holidays Proc. 1334/2024 Art. 4',
        ),
        (
            'Finding of the True Cross',
            'መስቀል',
            (_year, 9, _sep_day + 16),
            'Meskel, 17 Meskerem — Public Holidays Proc. 1334/2024 Art. 6',
        ),
    ]
del _year, _easter, _easter_date, _good_friday, _sep_day

_WRONG_PATRIOTS_DATES = ('2025-05-28', '2026-05-28')


def _exists(conn, name, iso_date):
    row = conn.execute(
        sa.text(
            'SELECT 1 FROM holiday '
            'WHERE company_id IS NULL AND is_national = TRUE AND name = :name '
            'AND holiday_date = :d'
        ),
        {'name': name, 'd': iso_date},
    ).first()
    return row is not None


def upgrade():
    conn = op.get_bind()

    # 1. Remove the wrongly seeded rows (national only; company rows untouched).
    conn.execute(
        sa.text(
            "DELETE FROM holiday WHERE company_id IS NULL AND is_national = TRUE AND name = 'Downfall of the Dergue'"
        )
    )
    conn.execute(
        sa.text(
            'DELETE FROM holiday WHERE company_id IS NULL AND is_national = TRUE '
            "AND name = 'Patriots'' Victory Day' "
            'AND holiday_date IN :wrong_dates'
        ).bindparams(sa.bindparam('wrong_dates', expanding=True)),
        {'wrong_dates': list(_WRONG_PATRIOTS_DATES)},
    )

    # 2. Seed the corrected 2025-2027 list (insert-if-absent, idempotent).
    for name, name_am, (y, m, d), desc in _CORRECTED:
        iso_date = f'{y:04d}-{m:02d}-{d:02d}'
        if _exists(conn, name, iso_date):
            continue
        conn.execute(
            sa.text(
                'INSERT INTO holiday (company_id, name, name_am, holiday_date, '
                'is_national, is_recurring, description) '
                'VALUES (NULL, :name, :name_am, :d, TRUE, FALSE, :desc)'
            ),
            {'name': name, 'name_am': name_am, 'd': iso_date, 'desc': desc},
        )


def downgrade():
    # No-op by design: re-adding the abolished May 28 holiday would corrupt
    # current-year holiday pay and overtime data. See docstring.
    pass
