"""
Seed the initial 2025 tax rule into the database.

Run this once after creating the TaxRule table:
    python seed_tax_rules.py

Or with Flask CLI:
    flask seed-tax-rules
"""

import json
from datetime import date

# Proclamation No. 1395/2025 — effective July 7, 2025
# Verified by: EY, PwC, DABLO Law, Liku Worku Law Office
RULES_2025 = {
    "version": "2025-v1",
    "effective_date": "2025-07-07",
    "brackets": [
        {"min": 0, "max": 2000, "rate": 0.00},
        {"min": 2001, "max": 4000, "rate": 0.15},
        {"min": 4001, "max": 7000, "rate": 0.20},
        {"min": 7001, "max": 10000, "rate": 0.25},
        {"min": 10001, "max": 14000, "rate": 0.30},
        {"min": 14001, "max": None, "rate": 0.35}
    ],
    "personal_relief": 150,
    "pension": {
        "employee_rate": 0.07,
        "employer_rate": 0.11,
        "deduction_order": "before_tax",
        "expat_exemption": True
    }
}


def seed():
    from payroll_engine import create_app, db
    from payroll_engine.models import TaxRule

    app = create_app()
    with app.app_context():
        # Check if rule already exists
        existing = TaxRule.query.filter_by(version_name='2025-v1').first()
        if existing:
            print("Tax rule '2025-v1' already exists. Skipping.")
            return

        rule = TaxRule(
            version_name='2025-v1',
            effective_date=date(2025, 7, 7),
            rules_json=RULES_2025,
            status='active',
            notes='Initial 2025 tax brackets per Proclamation No. 1395/2025. '
                  'Verified by EY, PwC, DABLO Law, Liku Worku Law Office.'
        )
        db.session.add(rule)
        db.session.commit()
        print(f"Seeded tax rule: {rule.version_name} (effective {rule.effective_date})")
        print(f"  Brackets: {len(rule.brackets)}")
        print(f"  Personal relief: ETB {rule.personal_relief}")
        print(f"  Pension: employee {rule.pension_employee_rate*100}%, employer {rule.pension_employer_rate*100}%")
        print(f"  Expat exempt: {rule.expat_pension_exempt}")


if __name__ == '__main__':
    seed()
