"""Regression coverage for dashboard and navigation language selection."""

import pytest

from payroll_engine.i18n import get_string


@pytest.mark.parametrize(
    'key',
    [
        'step_prepare',
        'step_review',
        'step_approve',
        'prepare_payroll',
        'compliance_timing_label',
        'compliance_evidence_help',
        'recent_payroll_runs',
        'tax_withheld',
        'deductions_breakdown',
        'attendance',
        'compare',
        'accounting',
        'pssa_remittance',
        'filing_history',
    ],
)
def test_dashboard_terms_have_amharic_and_oromo_copy(key):
    english = get_string(key, 'en')
    assert get_string(key, 'am') != english
    assert get_string(key, 'om') != english


def test_untranslated_first_use_copy_still_falls_back_to_english_for_oromo():
    assert get_string('first_workspace_title', 'om') == get_string('first_workspace_title', 'en')
