"""
Report Template Service — Configurable column layouts for ERCA and other reports.

Companies can customize which columns appear in their reports, in what order,
and with what headers. Templates are stored in Company.report_templates (JSON).

Usage:
    template = get_report_template(company_id, 'erca')
    columns = template['columns']  # list of {key, label, enabled, order}
"""

from typing import List, Dict, Optional

# All available columns for ERCA reports
# key: internal field name
# label: default header label
# data_path: how to extract from a payslip object
ERCA_COLUMNS = [
    {'key': 'row_number', 'label': 'No.', 'data_path': '_row_number'},
    {'key': 'employee_id', 'label': 'Employee ID', 'data_path': 'employee.employee_id'},
    {'key': 'employee_name', 'label': 'Employee Name', 'data_path': 'employee.name'},
    {'key': 'tin', 'label': 'TIN', 'data_path': 'employee.tin'},
    {'key': 'employment_date', 'label': 'Employment Date', 'data_path': 'employee.start_date'},
    {'key': 'department', 'label': 'Department', 'data_path': 'employee.department'},
    {'key': 'position', 'label': 'Position', 'data_path': 'employee.position'},
    {'key': 'basic_salary', 'label': 'Basic Salary', 'data_path': 'employee.basic_salary'},
    {'key': 'allowances', 'label': 'Allowances', 'data_path': 'employee.allowances'},
    {'key': 'gross_salary', 'label': 'Gross Salary', 'data_path': 'gross'},
    {'key': 'overtime_pay', 'label': 'Overtime Pay', 'data_path': 'overtime_pay'},
    {'key': 'pension_employee', 'label': 'Pension 7%', 'data_path': 'pension_employee'},
    {'key': 'pension_employer', 'label': 'Pension 11% (Employer)', 'data_path': 'pension_employer'},
    {'key': 'taxable_income', 'label': 'Taxable Income', 'data_path': 'taxable'},
    {'key': 'tax_withheld', 'label': 'Tax Withheld', 'data_path': 'tax'},
    {'key': 'net_pay', 'label': 'Net Pay', 'data_path': 'net'},
    {'key': 'employer_tin', 'label': 'Employer TIN', 'data_path': '_company_tin'},
    {'key': 'employer_name', 'label': 'Employer Name', 'data_path': '_company_name'},
    {'key': 'bank_account', 'label': 'Bank Account', 'data_path': 'employee.bank_account'},
    {'key': 'payment_method', 'label': 'Payment Method', 'data_path': 'employee.bank_or_telebirr'},
]

# Default enabled columns for ERCA (what most companies need)
ERCA_DEFAULT_ENABLED = [
    'row_number', 'employee_id', 'employee_name', 'tin',
    'gross_salary', 'pension_employee', 'taxable_income',
    'tax_withheld', 'net_pay',
]


def get_default_template(report_type: str = 'erca') -> dict:
    """Get the default template for a report type.

    Returns:
        Dict with 'columns' key containing list of column configs.
    """
    if report_type == 'erca':
        columns = []
        for i, col in enumerate(ERCA_COLUMNS):
            columns.append({
                'key': col['key'],
                'label': col['label'],
                'enabled': col['key'] in ERCA_DEFAULT_ENABLED,
                'order': i,
            })
        return {'columns': columns}

    return {'columns': []}


def get_report_template(company, report_type: str = 'erca') -> dict:
    """Get the report template for a company.

    Falls back to default if company has no custom template.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.

    Returns:
        Dict with 'columns' key.
    """
    if company.report_templates and report_type in company.report_templates:
        stored = company.report_templates[report_type]
        # Merge with defaults to ensure new columns appear
        return _merge_with_defaults(stored, report_type)

    return get_default_template(report_type)


def _merge_with_defaults(stored: dict, report_type: str) -> dict:
    """Merge stored template with defaults — adds new columns, preserves customizations."""
    default = get_default_template(report_type)
    stored_keys = {c['key'] for c in stored.get('columns', [])}
    default_keys = {c['key'] for c in default['columns']}

    # Start with stored columns (preserves order, label, enabled)
    merged = list(stored.get('columns', []))

    # Add any new default columns that aren't in stored
    for col in default['columns']:
        if col['key'] not in stored_keys:
            merged.append(col)

    # Remove columns that no longer exist in defaults
    merged = [c for c in merged if c['key'] in default_keys]

    return {'columns': merged}


def save_report_template(company, report_type: str, columns: list) -> None:
    """Save a report template for a company.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.
        columns: List of {key, label, enabled, order}
    """
    if company.report_templates is None:
        company.report_templates = {}

    company.report_templates[report_type] = {'columns': columns}


def get_enabled_columns(company, report_type: str = 'erca') -> List[Dict]:
    """Get enabled columns for a report, sorted by order.

    Returns:
        List of {key, label, data_path} for enabled columns only.
    """
    template = get_report_template(company, report_type)
    enabled = [c for c in template['columns'] if c.get('enabled', True)]
    enabled.sort(key=lambda c: c.get('order', 999))

    # Enrich with data_path
    path_map = {c['key']: c['data_path'] for c in ERCA_COLUMNS}
    result = []
    for col in enabled:
        result.append({
            'key': col['key'],
            'label': col['label'],
            'data_path': path_map.get(col['key'], col['key']),
        })

    return result


def get_column_value(payslip, data_path: str, company=None):
    """Extract a value from a payslip using a data_path string.

    Args:
        payslip: Payslip model instance
        data_path: Dot-notation path like 'employee.name' or 'gross'
        company: Company instance (for _company_tin, _company_name)

    Returns:
        The extracted value, or '' if not found.
    """
    if data_path == '_row_number':
        return ''  # Filled by the report generator
    if data_path == '_company_tin':
        return company.tin if company else ''
    if data_path == '_company_name':
        return company.name if company else ''

    # Handle encrypted fields
    if data_path == 'employee.bank_account':
        try:
            return str(payslip.employee.bank_account) if payslip.employee.bank_account else ''
        except Exception:
            return '****'
    if data_path == 'employee.tin':
        try:
            return str(payslip.employee.tin) if payslip.employee.tin else ''
        except Exception:
            return '****'

    # Dot-notation traversal
    parts = data_path.split('.')
    obj = payslip
    for part in parts:
        if obj is None:
            return ''
        obj = getattr(obj, part, None)

    return obj if obj is not None else ''


def get_all_available_columns(report_type: str = 'erca') -> list:
    """Get all available columns for a report type (for the settings UI).

    Returns:
        List of {key, label} for all possible columns.
    """
    if report_type == 'erca':
        return [{'key': c['key'], 'label': c['label']} for c in ERCA_COLUMNS]
    return []
