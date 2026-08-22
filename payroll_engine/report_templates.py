"""
Report Template Service — Fully flexible column layouts for ERCA and other reports.

Companies can:
- Add any column (predefined or custom)
- Remove any column
- Reorder columns freely
- Rename column headers
- Set custom data sources or static values
- Use formulas for calculated fields

Templates are stored in Company.report_templates (JSON).

Usage:
    template = get_report_template(company, 'erca')
    columns = template['columns']  # list of {key, label, enabled, order, data_path, ...}
"""

# Predefined column library — users can use these or create their own
# key: internal field name
# label: default header label
# data_path: how to extract from a payslip object
# group: UI grouping hint
COLUMN_LIBRARY = [
    # ERCA portal columns
    {'key': 'employee_name', 'label': 'Employee Full Name', 'data_path': 'employee.name', 'group': 'employee'},
    {'key': 'start_date', 'label': 'Start Date', 'data_path': 'employee.start_date', 'group': 'employee'},
    {'key': 'end_date', 'label': 'End Date', 'data_path': '_end_date', 'group': 'employee'},
    {'key': 'basic_salary', 'label': 'Basic Salary', 'data_path': 'employee.basic_salary', 'group': 'salary'},
    {
        'key': 'transport_allowance',
        'label': 'Transport Allowance',
        'data_path': '_transport_allowance',
        'group': 'salary',
    },
    {
        'key': 'taxable_transport',
        'label': 'Taxable Transport Allowance',
        'data_path': '_taxable_transport',
        'group': 'salary',
    },
    {'key': 'overtime_pay', 'label': 'Over Time', 'data_path': 'overtime_pay', 'group': 'salary'},
    {'key': 'other_taxable', 'label': 'Other Taxable Benefit', 'data_path': '_other_taxable', 'group': 'salary'},
    {'key': 'total_taxable', 'label': 'Total Taxable', 'data_path': 'taxable', 'group': 'tax'},
    {'key': 'tax_withheld', 'label': 'Tax withheld', 'data_path': 'tax', 'group': 'tax'},
    # Employee info
    {'key': 'employee_id', 'label': 'Employee ID', 'data_path': 'employee.employee_id', 'group': 'employee'},
    {'key': 'tin', 'label': 'TIN', 'data_path': 'employee.tin', 'group': 'employee'},
    {'key': 'fayda_fin', 'label': 'Fayda FIN', 'data_path': 'employee.fayda_fin', 'group': 'employee'},
    {'key': 'department', 'label': 'Department', 'data_path': 'employee.department', 'group': 'employee'},
    {'key': 'position', 'label': 'Position', 'data_path': 'employee.position', 'group': 'employee'},
    {'key': 'employment_date', 'label': 'Employment Date', 'data_path': 'employee.start_date', 'group': 'employee'},
    # Salary breakdown
    {'key': 'allowances', 'label': 'Allowances', 'data_path': 'employee.allowances', 'group': 'salary'},
    {'key': 'gross_salary', 'label': 'Gross Salary', 'data_path': 'gross', 'group': 'salary'},
    # Pension
    {'key': 'pension_employee', 'label': 'Pension 7%', 'data_path': 'pension_employee', 'group': 'pension'},
    {'key': 'pension_employer', 'label': 'Pension 11% (Employer)', 'data_path': 'pension_employer', 'group': 'pension'},
    # Tax
    {'key': 'taxable_income', 'label': 'Taxable Income', 'data_path': 'taxable', 'group': 'tax'},
    {'key': 'net_pay', 'label': 'Net Pay', 'data_path': 'net', 'group': 'net'},
    # Company info
    {'key': 'employer_tin', 'label': 'Employer TIN', 'data_path': '_company_tin', 'group': 'company'},
    {'key': 'employer_name', 'label': 'Employer Name', 'data_path': '_company_name', 'group': 'company'},
    # Payment
    {'key': 'bank_account', 'label': 'Bank Account', 'data_path': 'employee.bank_account', 'group': 'payment'},
    {'key': 'payment_method', 'label': 'Payment Method', 'data_path': 'employee.bank_or_telebirr', 'group': 'payment'},
    # Sequence
    {'key': 'row_number', 'label': 'No.', 'data_path': '_row_number', 'group': 'meta'},
]

# Default ERCA columns — matches the real portal format
# Source: Real ERCA filing (147 employees, Sene/June 2026)
ERCA_DEFAULT_COLUMNS = [
    {'key': 'employee_name', 'label': 'Employee Full Name', 'data_path': 'employee.name', 'enabled': True, 'order': 0},
    {'key': 'start_date', 'label': 'Start Date', 'data_path': 'employee.start_date', 'enabled': True, 'order': 1},
    {'key': 'end_date', 'label': 'End Date', 'data_path': '_end_date', 'enabled': True, 'order': 2},
    {'key': 'basic_salary', 'label': 'Basic Salary', 'data_path': 'employee.basic_salary', 'enabled': True, 'order': 3},
    {
        'key': 'transport_allowance',
        'label': 'Transport Allowance',
        'data_path': '_transport_allowance',
        'enabled': True,
        'order': 4,
    },
    {
        'key': 'taxable_transport',
        'label': 'Taxable Transport Allowance',
        'data_path': '_taxable_transport',
        'enabled': True,
        'order': 5,
    },
    {'key': 'overtime_pay', 'label': 'Over Time', 'data_path': 'overtime_pay', 'enabled': True, 'order': 6},
    {
        'key': 'other_taxable',
        'label': 'Other Taxable Benefit',
        'data_path': '_other_taxable',
        'enabled': True,
        'order': 7,
    },
    {'key': 'total_taxable', 'label': 'Total Taxable', 'data_path': 'taxable', 'enabled': True, 'order': 8},
    {'key': 'tax_withheld', 'label': 'Tax withheld', 'data_path': 'tax', 'enabled': True, 'order': 9},
]


def get_default_template(report_type: str = 'erca') -> dict:
    """Get the default template for a report type."""
    if report_type == 'erca':
        return {'columns': list(ERCA_DEFAULT_COLUMNS)}
    return {'columns': []}


def get_report_template(company, report_type: str = 'erca') -> dict:
    """Get the report template for a company.

    Falls back to default if company has no custom template.
    Preserves any custom columns the user added.
    """
    if company.report_templates and report_type in company.report_templates:
        stored = company.report_templates[report_type]
        return _merge_with_defaults(stored, report_type)
    return get_default_template(report_type)


def _merge_with_defaults(stored: dict, report_type: str) -> dict:
    """Merge stored template with defaults.

    - Preserves ALL stored columns (including custom ones)
    - Adds new default columns that aren't in stored
    - Does NOT remove user-added custom columns
    """
    default = get_default_template(report_type)
    stored_cols = stored.get('columns', [])
    stored_keys = {c['key'] for c in stored_cols}
    {c['key'] for c in default['columns']}

    # Start with stored columns — preserves everything the user configured
    merged = list(stored_cols)

    # Add new default columns that user hasn't seen yet
    for col in default['columns']:
        if col['key'] not in stored_keys:
            merged.append(col)

    return {'columns': merged}


def save_report_template(company, report_type: str, columns: list) -> None:
    """Save a report template for a company.

    Accepts ANY columns — predefined or custom. No restrictions.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.
        columns: List of column configs. Each must have at minimum:
            - key: unique identifier
            - label: display header
            - enabled: bool
            - order: int
            Optional:
            - data_path: how to extract value (dot-notation or _special)
            - static_value: fixed value for all rows
            - formula: calculated field (future)
    """
    if company.report_templates is None:
        company.report_templates = {}
    company.report_templates[report_type] = {'columns': columns}


def add_column(
    company,
    report_type: str,
    key: str,
    label: str,
    data_path: str | None = None,
    static_value=None,
    enabled: bool = True,
) -> None:
    """Add a single column to a report template.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.
        key: Unique column identifier
        label: Display header text
        data_path: How to extract value (e.g., 'employee.name', '_custom')
        static_value: Fixed value for all rows (if no data_path)
        enabled: Whether column is visible
    """
    template = get_report_template(company, report_type)
    columns = template.get('columns', [])

    # Check if column already exists
    existing = next((c for c in columns if c['key'] == key), None)
    if existing:
        # Update existing
        existing['label'] = label
        if data_path:
            existing['data_path'] = data_path
        if static_value is not None:
            existing['static_value'] = static_value
        existing['enabled'] = enabled
    else:
        # Add new
        max_order = max((c.get('order', 0) for c in columns), default=0)
        new_col = {
            'key': key,
            'label': label,
            'enabled': enabled,
            'order': max_order + 1,
        }
        if data_path:
            new_col['data_path'] = data_path
        if static_value is not None:
            new_col['static_value'] = static_value
        columns.append(new_col)

    save_report_template(company, report_type, columns)


def remove_column(company, report_type: str, key: str) -> None:
    """Remove a column from a report template.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.
        key: Column key to remove
    """
    template = get_report_template(company, report_type)
    columns = [c for c in template.get('columns', []) if c['key'] != key]
    save_report_template(company, report_type, columns)


def update_column(company, report_type: str, key: str, **kwargs) -> None:
    """Update a column's properties.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.
        key: Column key to update
        **kwargs: Any column property to update (label, data_path, enabled, order, static_value)
    """
    template = get_report_template(company, report_type)
    columns = template.get('columns', [])
    col = next((c for c in columns if c['key'] == key), None)
    if col:
        col.update(kwargs)
        save_report_template(company, report_type, columns)


def reorder_columns(company, report_type: str, key_order: list) -> None:
    """Reorder columns by providing keys in desired order.

    Args:
        company: Company model instance
        report_type: 'erca', 'pension', 'bank', etc.
        key_order: List of column keys in desired order
    """
    template = get_report_template(company, report_type)
    columns = template.get('columns', [])
    col_map = {c['key']: c for c in columns}

    reordered = []
    for i, key in enumerate(key_order):
        if key in col_map:
            col_map[key]['order'] = i
            reordered.append(col_map[key])

    # Append any columns not in the order list
    for col in columns:
        if col['key'] not in key_order:
            col['order'] = len(reordered)
            reordered.append(col)

    save_report_template(company, report_type, reordered)


def get_enabled_columns(company, report_type: str = 'erca') -> list[dict]:
    """Get enabled columns for a report, sorted by order.

    Returns:
        List of {key, label, data_path, static_value} for enabled columns only.
    """
    template = get_report_template(company, report_type)
    enabled = [c for c in template.get('columns', []) if c.get('enabled', True)]
    enabled.sort(key=lambda c: c.get('order', 999))

    # Build path map from library + custom columns
    path_map = {c['key']: c.get('data_path', c['key']) for c in COLUMN_LIBRARY}

    result = []
    for col in enabled:
        data_path = col.get('data_path', path_map.get(col['key'], col['key']))
        entry = {
            'key': col['key'],
            'label': col['label'],
            'data_path': data_path,
        }
        if 'static_value' in col:
            entry['static_value'] = col['static_value']
        result.append(entry)

    return result


def get_column_value(payslip, data_path: str, company=None, static_value=None):
    """Extract a value from a payslip using a data_path string.

    Args:
        payslip: Payslip model instance
        data_path: Dot-notation path like 'employee.name' or '_special'
        company: Company instance (for _company_tin, _company_name)
        static_value: If set, returns this value directly

    Returns:
        The extracted value, or '' if not found.
    """
    # Static value takes priority
    if static_value is not None:
        return static_value

    if data_path == '_row_number':
        return ''  # Filled by the report generator
    if data_path == '_company_tin':
        return company.tin if company else ''
    if data_path == '_company_name':
        return company.name if company else ''
    if data_path == '_end_date':
        return ''
    if data_path == '_transport_allowance':
        try:
            basic = float(payslip.employee.basic_salary or 0)
            gross = float(payslip.gross_salary or 0)
            return max(0, gross - basic)
        except Exception:
            return 0
    if data_path == '_taxable_transport':
        try:
            basic = float(payslip.employee.basic_salary or 0)
            gross = float(payslip.gross_salary or 0)
            return max(0, gross - basic)
        except Exception:
            return 0
    if data_path == '_other_taxable':
        return 0

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
    if data_path == 'employee.fayda_fin':
        try:
            return str(payslip.employee.fayda_fin) if payslip.employee.fayda_fin else ''
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
    """Get all predefined columns for the settings UI.

    Returns:
        List of {key, label, group} for all possible columns.
    """
    if report_type == 'erca':
        return [{'key': c['key'], 'label': c['label'], 'group': c.get('group', 'other')} for c in COLUMN_LIBRARY]
    return []
