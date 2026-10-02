"""Tests for Fayda Digital Identification Number (FIN) validation and integration.

Fayda FIN is a 12-digit number issued by Ethiopia's National ID Program (NIDP).
Source: https://id.gov.et
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.models import validate_fayda_fin


class TestFaydaFinValidation:
    """Test the validate_fayda_fin function."""

    def test_valid_fin(self):
        is_valid, normalized, error = validate_fayda_fin('123456789012')
        assert is_valid is True
        assert normalized == '123456789012'
        assert error is None

    def test_valid_fin_with_spaces(self):
        is_valid, normalized, _error = validate_fayda_fin('1234 5678 9012')
        assert is_valid is True
        assert normalized == '123456789012'

    def test_valid_fin_with_dashes(self):
        is_valid, normalized, _error = validate_fayda_fin('1234-5678-9012')
        assert is_valid is True
        assert normalized == '123456789012'

    def test_empty_fin(self):
        is_valid, normalized, error = validate_fayda_fin('')
        assert is_valid is False
        assert normalized is None
        assert 'empty' in error.lower()

    def test_none_fin(self):
        is_valid, _normalized, _error = validate_fayda_fin(None)
        assert is_valid is False

    def test_too_short(self):
        is_valid, _normalized, error = validate_fayda_fin('12345678901')
        assert is_valid is False
        assert '12 digits' in error

    def test_too_long(self):
        is_valid, _normalized, error = validate_fayda_fin('1234567890123')
        assert is_valid is False
        assert '12 digits' in error

    def test_non_numeric(self):
        is_valid, _normalized, error = validate_fayda_fin('abcdefghijkl')
        assert is_valid is False
        assert 'digits' in error.lower()

    def test_mixed_alpha_numeric(self):
        is_valid, _normalized, error = validate_fayda_fin('12345abc9012')
        assert is_valid is False
        assert 'digits' in error.lower()

    def test_all_zeros(self):
        """Edge case: all zeros is technically valid 12-digit format."""
        is_valid, normalized, _error = validate_fayda_fin('000000000000')
        assert is_valid is True
        assert normalized == '000000000000'

    def test_leading_trailing_spaces(self):
        is_valid, normalized, _error = validate_fayda_fin('  123456789012  ')
        assert is_valid is True
        assert normalized == '123456789012'

    def test_exactly_11_digits(self):
        is_valid, _, error = validate_fayda_fin('12345678901')
        assert is_valid is False
        assert '12 digits' in error

    def test_exactly_13_digits(self):
        is_valid, _, error = validate_fayda_fin('1234567890123')
        assert is_valid is False
        assert '12 digits' in error


class TestFaydaFinProfileChangeRequest:
    """Test that Fayda FIN is in the editable/sensitive fields list."""

    def test_fayda_fin_in_editable_fields(self):
        from payroll_engine.models import ProfileChangeRequest

        assert 'fayda_fin' in ProfileChangeRequest.EDITABLE_FIELDS

    def test_fayda_fin_in_sensitive_fields(self):
        from payroll_engine.models import ProfileChangeRequest

        assert 'fayda_fin' in ProfileChangeRequest.SENSITIVE_FIELDS

    def test_fayda_fin_field_label(self):
        from payroll_engine.models import ProfileChangeRequest

        req = ProfileChangeRequest(field_name='fayda_fin')
        assert 'Fayda' in req.field_label


class TestFaydaFinReportTemplates:
    """Test that Fayda FIN appears in report template column library."""

    def test_fayda_fin_in_column_library(self):
        from payroll_engine.report_templates import COLUMN_LIBRARY

        fin_cols = [c for c in COLUMN_LIBRARY if c['key'] == 'fayda_fin']
        assert len(fin_cols) == 1
        assert fin_cols[0]['data_path'] == 'employee.fayda_fin'
        assert fin_cols[0]['group'] == 'employee'

    def test_fayda_fin_in_path_map(self):
        from payroll_engine.report_templates import COLUMN_LIBRARY

        fin_col = next(c for c in COLUMN_LIBRARY if c['key'] == 'fayda_fin')
        assert fin_col['data_path'] == 'employee.fayda_fin'


class TestFaydaFinValidationIntegration:
    """Test Fayda FIN validation in the payroll validation pipeline."""

    def test_missing_fin_generates_hint(self):
        from payroll_engine.validation import _check_missing_fayda_fin

        data = [{'id': 'E001', 'name': 'Test', 'fayda_fin': ''}]
        results = []
        _check_missing_fayda_fin(data, results)
        assert len(results) == 1
        assert results[0].rule_code == 'MISSING_FAYDA_FIN'
        assert results[0].severity == 'HINT'

    def test_present_fin_no_hint(self):
        from payroll_engine.validation import _check_missing_fayda_fin

        data = [{'id': 'E001', 'name': 'Test', 'fayda_fin': '123456789012'}]
        results = []
        _check_missing_fayda_fin(data, results)
        assert len(results) == 0

    def test_missing_fin_field_generates_hint(self):
        """When fayda_fin key is missing entirely from the dict."""
        from payroll_engine.validation import _check_missing_fayda_fin

        data = [{'id': 'E001', 'name': 'Test'}]
        results = []
        _check_missing_fayda_fin(data, results)
        assert len(results) == 1
