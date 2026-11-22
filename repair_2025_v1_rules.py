"""Repair the existing 2025-v1 tax rule for issue #79.

This script is intentionally manual and is never invoked by application startup.
Run it only against a throwaway or human-reviewed database:
    python repair_2025_v1_rules.py
"""

from copy import deepcopy


def repair_2025_v1_rules(app=None):
    """Repair only the existing 2025-v1 row; return True when changed."""
    from flask import has_app_context

    if app is not None:
        with app.app_context():
            return _repair()
    if has_app_context():
        return _repair()

    from payroll_engine import create_app

    app = create_app()
    with app.app_context():
        return _repair()


def _repair():
    from payroll_engine import db
    from payroll_engine.leave import invalidate_leave_cache
    from payroll_engine.models import TaxRule
    from payroll_engine.overtime import invalidate_overtime_cache

    row = TaxRule.query.filter_by(version_name='2025-v1').first()
    if row is None:
        print("Tax rule '2025-v1' does not exist. No changes made.")
        return False

    rules = deepcopy(row.rules_json)
    overtime = rules.setdefault('overtime', {})
    overtime_rates = overtime.setdefault('rates', {})
    leave = rules.setdefault('leave', {})

    changed = False
    for key, fixed in (('day', 1.50), ('night', 1.75)):
        old = overtime_rates.get(key)
        if old != fixed:
            print(f"overtime.rates.{key}: before={old}, after={fixed}")
            overtime_rates[key] = fixed
            changed = True

    old_annual = leave.get('annual_base')
    if old_annual != 16:
        print(f"leave.annual_base: before={old_annual}, after=16")
        leave['annual_base'] = 16
        changed = True

    if not changed:
        print("Tax rule '2025-v1' already has fixed overtime and annual-leave values.")
        return False

    row.rules_json = rules
    db.session.commit()
    invalidate_overtime_cache()
    invalidate_leave_cache()
    print("Updated tax rule '2025-v1'; version_name and effective_date unchanged.")
    return True


if __name__ == '__main__':
    repair_2025_v1_rules()
