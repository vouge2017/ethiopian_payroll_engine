"""Ethiopian-calendar-first rendering receipts on public templates."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date

from payroll_engine import create_app
from payroll_engine.ethiopian_calendar import format_ethiopian_period


def _client():
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    return app.test_client()


def test_ethiopian_period_label_text():
    label = format_ethiopian_period(date(2026, 10, 21))
    assert label == 'ጥቅምት 2019 ዓ.ም. · Gregorian October 2026', label
    assert format_ethiopian_period(date(2026, 10, 1)).startswith('መስከረም 2019')


def test_welcome_shows_ethiopian_first():
    client = _client()
    page = client.get('/welcome').get_data(as_text=True)
    assert 'Tikimt 2019' in page
    assert 'Ethiopian calendar · October 2026 Gregorian' in page
    assert page.index('Tikimt 2019') < page.index('October 2026')


def test_welcome_has_no_legacy_gregorian_first_string():
    client = _client()
    page = client.get('/welcome').get_data(as_text=True)
    assert 'Gregorian calendar · Synthetic company' not in page
