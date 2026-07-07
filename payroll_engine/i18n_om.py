"""
Afaan Oromoo Language Strings — Core UI Translation

Qubee (Latin script) — no special fonts needed.
50+ core strings for the payroll flow.

Usage: loaded by i18n.py when language='om'.

Translation notes:
- "Kaffaltii" = salary/wage (standard business term)
- "Hojjetaa" = worker/employee
- "Ramaddii" = tax
- "Hir'ina" = deduction/withholding
- "Bal'ina" = allowance
- Review flags marked with: # NEEDS REVIEW
"""

STRINGS_OM = {
    # --- Navigation ---
    'dashboard': 'Gabatee',
    'employees': 'Hojjetaanota',
    'payroll': 'Kaffaltii',
    'reports': 'Gabaasa',
    'settings': 'Qindaa\'ina',
    'logout': 'Ba\'i',

    # --- Actions ---
    'run_payroll': 'Kaffaltii kaasii',
    'add_employee': 'Hojjetaa dabali',
    'save': 'Olkaa\'i',
    'cancel': 'Haquu',
    'approve': 'Mirkaneeffadhu',
    'download': 'Buusaa',
    'upload': 'Olfe\'i',
    'search': 'Barbaadi',
    'view': 'Ilaali',

    # --- Payroll ---
    'basic_salary': 'Kaffaltii bu\'uuraa',
    'allowances': 'Bal\'ina',
    'gross_salary': 'Kaffaltii waliigalaa',
    'income_tax': 'Ramaddii galii',
    'employee_pension': 'Furtuu hojjetaa',
    'employer_pension': 'Furtuu hirmaataa',
    'net_pay': 'Kaffaltii xiqqaa',
    'payment_method': 'Too\'annoo kaffaltii',

    # --- Status ---
    'completed': 'Xumurameera',
    'processing': 'Hojii irra jira',
    'pending': 'Eegaa jira',
    'failed': 'Hin milkoofne',
    'draft': 'Qormaata',
    'review': 'Irra deebi\'a',

    # --- Employee ---
    'employee_id': 'Lakkoofsa hojjetaa',
    'full_name': 'Maqaa guutuu',
    'tin': 'Lakkoofsa ramaddii',
    'bank_account': 'Herrega baankii',

    # --- Reports ---
    'erca_report': 'Gabaasa ERCA',
    'pension_report': 'Gabaasa furtuu',
    'bank_file': 'Fayilii baankii',
    'compliance_score': 'Qabxii simannaa',

    # --- Messages ---
    'welcome': 'Baga nagaan dhuftan',
    'payroll_completed': 'Kaffaltiin xumurameera',
    'no_employees': 'Hojjetaan hin jiru',
    'no_payslips': 'Warraagaa kaffaltii hin jiru',

    # --- Validation ---
    'required_field': 'Dirree kun dirqama',
    'invalid_number': 'Lakkoofsa sirrii galchaa',
    'missing_bank': 'Odeeffannoo baankii hin jiru',

    # --- Compliance ---
    'erca_deadline': 'Guyyaa dhumaa ERCA',
    'pension_deadline': 'Guyyaa dhumaa furtuu',
    'days_remaining': 'Guyywan hafan',

    # --- Leave ---
    'annual_leave': 'Baga guyyaa waggaa',
    'sick_leave': 'Baga dhiibbaa',
    'request_leave': 'Baga gaafadhu',
    'leave_balance': 'Hanga baga',

    # --- Dashboard ---
    'total_employees': 'Hojjetaanota waliigalaa',
    'monthly_payroll': 'Kaffaltii ji\'aa',
    'next_payroll_date': 'Guyyaa kaffaltii itti aanu',
    'compliance_status': 'Haala simannaa',

    # --- Payslip ---
    'payslip': 'Warraagaa kaffaltii',
    'earnings': 'Galii',
    'deductions': 'Hir\'ina',
    'total_deductions': 'Hir\'ina waliigalaa',

    # --- General ---
    'delete': 'Haquu',
    'edit': 'Gulaaluu',
    'filter': 'Calaluu',
    'export': 'Alergi',
    'confirm': 'Mirkaneessi',

    # --- Login ---
    'sign_in': 'Seenii',
    'phone_number': 'Lakkoofsa bilbila',
    'password': 'Jecha darbii',
    'remember_me': 'Na yaadadhu',
    'forgot_password': 'Jecha darbii irraanfattanii',

    # --- Employee Detail ---
    'department': 'Kutaa',
    'position': 'Iddoo',
    'start_date': 'Guyyaa jalqabaa',
    'status': 'Haala',

    # --- Overtime ---
    'overtime': 'Sa\'aatii dabalataa',
    'overtime_hours': 'Sa\'aatii dabalataa',

    # --- Severance ---
    'severance': 'Mallaakkii',

    # --- Payroll Run ---
    'payroll_run': 'Adeemsaa kaffaltii',
    'reference': 'Wabiilee',
    'period': 'Yeroo',
}
