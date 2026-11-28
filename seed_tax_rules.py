"""
Seed the initial 2025 tax rule into the database.

Run this once after creating the TaxRule table:
    python seed_tax_rules.py

Or with Flask CLI:
    flask seed-tax-rules
"""

from datetime import date

# Proclamation No. 1395/2025 — effective July 7, 2025 (effective date to be
# confirmed by the accountant; public sources list different item dates)
# Brackets: Proclamation No. 1395/2025, Article 11 (Employment Income Tax
# Rates). Evidence trail for the article number:
# docs/PENSION_BEFORE_TAX_RC38000_01.md
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
    "personal_relief": 0,
    "pension": {
        "employee_rate": 0.07,
        "employer_rate": 0.11,
        "deduction_order": "after_tax",
        "expat_exemption": True
    },
    "overtime": {
        "rates": {
            # Key meanings are pinned to Proclamation 1156/2019, Art. 68:
            # day = 6am-10pm, Art. 68(1)(a)
            # night = 10pm-6am, Art. 68(1)(b)
            # holiday = weekly rest day, Art. 68(1)(c)
            # rest_day_holiday = public holiday, Art. 68(1)(d)
            "day": 1.50,
            "night": 1.75,
            "holiday": 2.00,
            "rest_day_holiday": 2.50
        },
        "max_hours_month": 20,
        "max_hours_year": 100,
        "monthly_hours": 208,
        "source": "Labor Proclamation No. 1156/2019, Article 68(1)(a)-(d)"
    },
    "leave": {
        "annual_base": 16,
        "annual_increment": 1,
        "annual_max": 30,
        "sick_max_days": 180,
        "sick_tier_1_days": 30,
        "sick_tier_2_days": 60,
        "maternity_days": 120,
        "paternity_days": 3,
        "special_days": 3,
        "source": (
            "Labor Proclamation No. 1156/2019: annual leave Art. 77(1); "
            "sick leave Art. 85-86; maternity leave Art. 88; "
            "paternity leave Art. 81(2)"
        )
    },
    "severance": {
        "max_months": 12,
        "source": "Labor Proclamation No. 1156/2019, Articles 40-42"
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
            notes='PAYE on gross per adviser decision 2026-10-25 '
                  '(Proclamation 979/2016 Arts 10-12, as amended by 1395/2025); '
                  'final licensed-accountant sign-off pending before real payroll.'
        )
        db.session.add(rule)
        db.session.commit()
        print(f"Seeded tax rule: {rule.version_name} (effective {rule.effective_date})")
        print(f"  Brackets: {len(rule.brackets)}")
        print(f"  Personal relief: ETB {rule.personal_relief}")
        print(f"  Pension: employee {rule.pension_employee_rate*100}%, employer {rule.pension_employer_rate*100}%")
        print(f"  Expat exempt: {rule.expat_pension_exempt}")
        ot = rule.overtime_rates
        if ot:
            print(f"  Overtime: day={ot.get('day', '?')}x, night={ot.get('night', '?')}x, holiday={ot.get('holiday', '?')}x")
        lv = rule.leave_rules
        if lv:
            print(f"  Leave: annual={lv.get('annual_base', '?')}d, sick={lv.get('sick_max_days', '?')}d, maternity={lv.get('maternity_days', '?')}d")
        print(f"  Severance cap: {rule.severance_max_months} months")


if __name__ == '__main__':
    seed()
