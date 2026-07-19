"""
Afaan Oromoo Language Strings — Core UI Translation

Qubee (Latin script) — no special fonts needed.
164 core strings for the payroll flow.

Usage: loaded by i18n.py when language='om'.
"""

STRINGS_OM = {
    # Navigation & Actions
    'dashboard': 'Daashboordii',
    'employees': 'Hojjettoota',
    'run_payroll': 'Kaffaltii Raawwaddhu',
    'payroll': 'Kaffaltiiwwan Raawwataman',
    'payroll_runs': 'Kaffaltiiwwan Raawwataman',
    'reports': 'Gabaasota',
    'team': 'Miseensota Garee',
    'my_dashboard': 'Daashboordii Koo',
    'my_payslips': 'Waraqaa Kaffaltii Koo',
    'my_profile': 'Profaayilii Koo',
    'logout': 'Bahii',
    'log_in': 'Seeni',
    'register': 'Galmaa\'i',
    'add_employee': 'Hojjetaa Dabali',
    'save_employee': 'Hojjetaa Olkaayi',
    'cancel': 'Haqunu',
    'search': 'Barbaadi',
    'upload_csv': 'CSV Olfe\'i',
    'select_csv': 'Faayila CSV Filadhu',
    'view_all': 'Hunduma Agarsiisi',
    'download': 'Buufadhu',
    'add': 'Dabali',
    'confirm_approve': 'Mirkaneessi & Raggaasisi',
    'reactivate': 'Deebisii Kakassi',
    'link': 'Walqabsiisi',
    'terminate_employee': 'Hojjetaa Gaggeessi',
    'oromoo': 'Afaan Oromoo',
    'actions': 'Gochaawwan',
    'show_calculation': 'Shallacha agarsiisi',
    'entries': 'Galfamoota',
    'overtime': 'Hojii Turee',

    # Employee Fields
    'employee_id': 'ID Hojjetaa',
    'full_name': 'Maqaa Guutuu',
    'name': 'Maqaa',
    'phone': 'Bilbila',
    'department': 'Damee',
    'position': 'Gadi-aantummaa Hojii',
    'start_date': 'Guyyaa Hojii Jalqabe',
    'basic_salary': 'Mindaa Bu\'uraa',
    'allowances': 'Aballii',
    'gross_salary': 'Mindaa Waligalaa',
    'bank_account': 'Herrega Baankii',
    'payment_method': 'Mala Kaffaltii',
    'tin': 'TIN',
    'role': 'Gahee',
    'joined': 'Kan Seene',
    'status': 'Haala',
    'deactivated': 'Kan Dhaabbate',
    'linked_user': 'Fayyadamaa Walqabate',

    # Payroll
    'payroll_summary': 'Gabaasa Kaffaltii Gabaabaa',
    'payroll_history': 'Seenaa Kaffaltii',
    'period': 'Yeroo',
    'date': 'Guyyaa',
    'earnings': 'Galiiwwan',
    'deductions': 'Hir\'ifamoota',
    'gross': 'Waligala',
    'income_tax': 'Gibira Galii',
    'employee_pension': 'Furtuu Hojjetaa',
    'employer_pension': 'Furtuu Hojjechiisaa',
    'total_deductions': 'Total Hir\'ifamoota',
    'net_pay': 'Kaffaltii Qulqulluu',
    'net': 'Qulqulluu',
    'payment': 'Kaffaltii',
    'pdf': 'PDF',
    'payslips': 'Waraqaa Kaffaltii',
    'payslip_history': 'Seenaa Waraqaa Kaffaltii',
    'no_payslips': 'Waraqaan kaffaltii ammatti hin jiru',
    'no_runs': 'Kaffaltiin raawwatame ammatti hin jiru',
    'recent_payroll_runs': 'Kaffaltiiwwan Dhiyoo Raawwataman',
    'recent_payslips': 'Waraqaa Kaffaltii Dhiyoo',
    'recent_runs': 'Raawwiiwwan dhiyoo',
    'confirm_payroll_processing': 'Adeemsa Kaffaltii Mirkaneessi',
    'enter_password_confirm': 'Mirkaneessuuf jecha icciitii keessan galchaa',
    'your_login_password': 'Jecha Icciitii Seensaa',
    'total_employees': 'Total Hojjettoota',
    'total_gross': 'Total Waligala',
    'total_tax': 'Total Gibira',
    'total_net': 'Total Qulqulluu',

    # Overtime
    'overtime_this_month': 'Hojii Turee kan Addaa',
    'total_hours': 'Total Sa\'aatii',
    'over_limit': 'Daangaa Ol',
    'hours': 'Sa\'aatiiwwan',
    'type': 'Akaakuu',
    'rate': 'Saffisa',

    # Compliance & Reports
    'compliance': 'Seera Kabajuu',
    'compliance_score': 'Qabxii Seera Kabajuu',
    'compliance_details': 'Tarreeffama Seera Kabajuu',
    'erca_filing': 'ERCA Filing',
    'tax_filing_deadline': 'Daangaa Guyyaa Gibira Beeksisuu',
    'pension_deadline': 'Daangaa Guyyaa Furtuu Hojjetaa',
    'pension_contribution_deadline': 'Daangaa Guyyaa Buusii Furtuu',
    'pssa_remittance': 'PSSSA Remittance',
    'reports_compliance': 'Gabaasa & Seera Kabajuu',
    'total_checks': 'Total Sakatta\'iinsa',
    'issue': 'Rakkoo',
    'override': 'Irra Dabalama',
    'reason': 'Sababa',
    'note': 'Hubachiisa',
    'why_ok': 'Kun maaliif sirrii ta\'e?',

    # Dashboard
    'latest_net_pay': 'Kaffaltii Qulqulluu Dhumaa',
    'last_payroll_run': 'Kaffaltii Raawwatame kan Dhumaa',
    'quick_actions': 'Gochaawwan Ariifachiisaa',

    # Termination
    'severance_preview': 'Durgoo Gaggeessaa Dursee Argamuu',
    'termination_reason': 'Sababa Hojii Gaggeeffamuu',
    'last_working_day': 'Guyyaa Hojii Dhumaa',
    'years_of_service': 'Waggoottan Tajaajilaa',

    # Team & Linking
    'current_members': 'Miseensota Ammaa',
    'add_team_member': 'Miseensa Garee Dabali',
    'phone_or_email': 'Bilbila ykn Email',
    'user_account': 'Herrega Fayyadamaa',
    'link_employee_user': 'Hojjetaa herrega fayyadamaa waliin walqabsiisi',

    # Login & Registration
    'password': 'Jecha Icciitii',
    'forgot_password': 'Jecha Icciitii dagattanii?',
    'remember_me': 'Na Yaadadhu',
    'email': 'Email',
    'yes': 'Eeyyee',
    'no': 'Lakki',

    # CSV & Format
    'csv_format': 'Boca CSV',
    'bank_telebirr': 'Baankii / Telebirr',

    # Flash Messages
    'how_tax_calculated': 'Caasni akkamitti shallagama?',
    'tax_explainer_intro': "Caansi lixuu Itoophiyaa brackettiin caalu fayyadamaa (Proclamation No. 1395/2025). Haqni guutuu dura caasaa irraa ni haqama, lixuu kee ni hir'isa.",
    'bracket': 'Bracket',
    'taxable_range': 'Hangaa Lixuu',
    'rate': 'Hammam',
    'personal_relief': 'Dhoomsoo Dhuunfaa',
    'per_month': "ji'a tokkootti",
    'pension_before_tax': 'Haqni guutuu dura caasaa irraa ni haqama',
    'of_basic_salary': "lixuu bu'uura",
    'then_tax': 'sana booda caasni ni shallagama',
}
