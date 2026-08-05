"""
Tests for rule_source.py — Legal source tracing for every calculation.

Run: python -m pytest tests/test_rule_source.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payroll_engine.rule_source import (
    RULE_SOURCES, get_rule_source, get_rules_by_category,
    get_all_sources, get_explanation, mark_verified,
    get_unverified_rules, get_verification_summary,
    RuleSource,
)


# ─────────────────────────────────────────────
# Tests: Rule sources exist
# ─────────────────────────────────────────────

class TestRuleSourcesExist:

    def test_all_categories_covered(self):
        categories = {r.category for r in RULE_SOURCES.values()}
        assert 'tax' in categories
        assert 'pension' in categories
        assert 'overtime' in categories
        assert 'leave' in categories
        assert 'severance' in categories

    def test_tax_brackets_source(self):
        source = get_rule_source('tax_brackets')
        assert source is not None
        assert '1395/2025' in source.source
        assert 'Article 11' in source.source
        assert source.category == 'tax'
        assert len(source.explanation) > 0

    def test_pension_source(self):
        source = get_rule_source('pension_employee_rate')
        assert source is not None
        assert '1268/2022' in source.source
        assert '7%' in source.explanation

    def test_overtime_sources(self):
        assert get_rule_source('overtime_day_rate') is not None
        assert get_rule_source('overtime_night_rate') is not None
        assert get_rule_source('overtime_holiday_rate') is not None
        assert get_rule_source('overtime_rest_holiday_rate') is not None

    def test_leave_sources(self):
        assert get_rule_source('leave_annual') is not None
        assert get_rule_source('leave_sick') is not None
        assert get_rule_source('leave_maternity') is not None

    def test_severance_sources(self):
        assert get_rule_source('severance_year1') is not None
        assert get_rule_source('severance_additional_years') is not None
        assert get_rule_source('severance_maximum') is not None

    def test_cash_limit_source(self):
        source = get_rule_source('tax_cash_limit')
        assert source is not None
        assert '50,000' in source.explanation
        assert '81' in source.source


# ─────────────────────────────────────────────
# Tests: Source format
# ─────────────────────────────────────────────

class TestSourceFormat:

    def test_all_sources_have_explanation(self):
        for rule_id, source in RULE_SOURCES.items():
            assert len(source.explanation) > 0, f'{rule_id}: missing explanation'

    def test_all_sources_have_name(self):
        for rule_id, source in RULE_SOURCES.items():
            assert len(source.name) > 0, f'{rule_id}: missing name'
            assert len(source.name_am) > 0, f'{rule_id}: missing Amharic name'

    def test_all_sources_have_proclamation_reference(self):
        for rule_id, source in RULE_SOURCES.items():
            assert 'Proclamation' in source.source or 'proclamation' in source.source, \
                f'{rule_id}: source should reference a proclamation'

    def test_amharic_names_different_from_english(self):
        for rule_id, source in RULE_SOURCES.items():
            assert source.name_am != source.name, \
                f'{rule_id}: Amharic name should differ from English'


# ─────────────────────────────────────────────
# Tests: Category filtering
# ─────────────────────────────────────────────

class TestCategoryFiltering:

    def test_tax_rules(self):
        tax_rules = get_rules_by_category('tax')
        assert len(tax_rules) >= 3
        assert all(r.category == 'tax' for r in tax_rules)

    def test_pension_rules(self):
        pension_rules = get_rules_by_category('pension')
        assert len(pension_rules) >= 3

    def test_overtime_rules(self):
        overtime_rules = get_rules_by_category('overtime')
        assert len(overtime_rules) >= 5

    def test_leave_rules(self):
        leave_rules = get_rules_by_category('leave')
        assert len(leave_rules) >= 4

    def test_severance_rules(self):
        severance_rules = get_rules_by_category('severance')
        assert len(severance_rules) >= 3


# ─────────────────────────────────────────────
# Tests: Verification
# ─────────────────────────────────────────────

class TestVerification:

    def test_initially_unverified(self):
        source = get_rule_source('tax_brackets')
        assert source.verified is False

    def test_mark_verified(self):
        source = mark_verified('tax_brackets', 'accountant@example.com')
        assert source.verified is True
        assert source.verified_by == 'accountant@example.com'
        assert source.verified_at is not None

        # Reset for other tests
        source.verified = False
        source.verified_by = None
        source.verified_at = None

    def test_unverified_rules_list(self):
        unverified = get_unverified_rules()
        assert len(unverified) > 0
        assert all(not r.verified for r in unverified)

    def test_verification_summary(self):
        summary = get_verification_summary()
        assert summary['total'] > 0
        assert summary['verified'] == 0  # None verified initially
        assert summary['unverified'] == summary['total']
        assert summary['percentage'] == 0.0


# ─────────────────────────────────────────────
# Tests: Explanation content
# ─────────────────────────────────────────────

class TestExplanationContent:

    def test_tax_bracket_explanation_has_rates(self):
        explanation = get_explanation('tax_brackets')
        assert '0%' in explanation
        assert '15%' in explanation
        assert '20%' in explanation
        assert '25%' in explanation
        assert '30%' in explanation
        assert '35%' in explanation

    def test_pension_explanation_has_rates(self):
        explanation = get_explanation('pension_employee_rate')
        assert '7%' in explanation

    def test_overtime_explanation_has_multipliers(self):
        explanation = get_explanation('overtime_day_rate')
        assert '1.5' in explanation

    def test_severance_explanation_has_formula(self):
        explanation = get_explanation('severance_year1')
        assert '30 days' in explanation

    def test_unknown_rule_returns_empty(self):
        explanation = get_explanation('nonexistent_rule')
        assert explanation == ''


# ─────────────────────────────────────────────
# Tests: Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_get_nonexistent_rule(self):
        source = get_rule_source('nonexistent')
        assert source is None

    def test_mark_nonexistent_verified(self):
        result = mark_verified('nonexistent', 'user')
        assert result is None

    def test_get_rules_empty_category(self):
        rules = get_rules_by_category('nonexistent')
        assert len(rules) == 0

    def test_total_rule_count(self):
        """Should have at least 20 rules covering all major areas."""
        assert len(RULE_SOURCES) >= 20
