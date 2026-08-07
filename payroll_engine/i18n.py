"""
Multilingual Language Strings — Core UI Translation

Supports: English (en), Amharic (am), Afaan Oromoo (om)

Usage in templates:
    {{ _('dashboard') }}  → 'ዳሽቦርድ' (Amharic) or 'Dashboard' (English) or 'Daashboordii' (Afaan Oromoo)
"""

from payroll_engine.i18n_om import STRINGS_OM

# Amharic strings — 164 keys
STRINGS = {
    # Navigation & Actions
    'dashboard': 'ዳሽቦርድ',
    'employees': 'ሰራተኞች',
    'run_payroll': 'ደመወዝ አዘጋጅ',
    'payroll': 'የተሰሩ ደመወዞች',
    'payroll_runs': 'የተሰሩ ደመወዞች',
    'reports': 'ሪፖርቶች',
    'team': 'የቡድን አባላት',
    'my_dashboard': 'የእኔ ዳሽቦርድ',
    'my_payslips': 'የእኔ የደመወዝ ወረቀቶች',
    'my_profile': 'የእኔ መገለጫ',
    'logout': 'ውጣ',
    'help': 'እርዳታ',
    'log_in': 'ግባ',
    'register': 'ተመዝገብ',
    'add_employee': 'ሰራተኛ መዝግብ',
    'save_employee': 'ሰራተኛ አስቀምጥ',
    'cancel': 'ሰርዝ',
    'search': 'ፈልግ',
    'upload_csv': 'CSV ጭን',
    'select_csv': 'የCSV ፋይል ምረጥ',
    'view_all': 'ሁሉንም እይ',
    'download': 'አውርድ',
    'add': 'መዝግብ',
    'confirm_approve': 'አረጋግጥና አጽድቅ',
    'reactivate': 'መልሰህ አንቃ',
    'link': 'አያይዝ',
    'terminate_employee': 'ሰራተኛ አሰናብት',
    'oromoo': 'ኦሮሞኛ',
    'actions': 'ተግባራት',
    'show_calculation': 'ስሌት አሳይ',
    'entries': 'ምዝገባዎች',
    'overtime': 'ትርፍ ሰዓት',
    # Employee Fields
    'employee_id': 'የሰራተኛ መታወቂያ',
    'full_name': 'ሙሉ ስም',
    'name': 'ስም',
    'phone': 'ስልክ',
    'department': 'ክፍል',
    'position': 'የስራ መደብ',
    'start_date': 'የስራ መጀመሪያ ቀን',
    'basic_salary': 'መሠረታዊ ደመወዝ',
    'allowances': 'አበል',
    'gross_salary': 'ጠቅላላ ደመወዝ',
    'bank_account': 'የባንክ ሂሳብ',
    'payment_method': 'የክፍያ መንገድ',
    'tin': 'TIN',
    'role': 'ድርሻ',
    'joined': 'የተቀጠረበት ቀን',
    'status': 'ሁኔታ',
    'deactivated': 'የታገደ',
    'linked_user': 'የተያያዘ ተጠቃሚ',
    # Payroll
    'payroll_summary': 'የደመወዝ ማጠቃለያ',
    'payroll_history': 'የደመወዝ ታሪክ',
    'period': 'ወቅት',
    'date': 'ቀን',
    'earnings': 'ገቢዎች',
    'deductions': 'ተቀናሾች',
    'gross': 'ጠቅላላ ገቢ',
    'income_tax': 'የስራ ግብር',
    'employee_pension': 'የሰራተኛ ጡረታ',
    'employer_pension': 'የድርጅት ጡረታ',
    'total_deductions': 'ጠቅላላ ተቀናሽ',
    'net_pay': 'የተጣራ ክፍያ',
    'net': 'የተጣራ',
    'payment': 'ክፍያ',
    'pdf': 'PDF',
    'payslips': 'የደመወዝ ወረቀቶች',
    'payslip_history': 'የደመወዝ ወረቀቶች ታሪክ',
    'no_payslips': 'እስካሁን ምንም የደመወዝ ወረቀት የለም',
    'no_runs': 'እስካሁን የተሰራ ደመወዝ የለም',
    'recent_payroll_runs': 'በቅርቡ የተሰሩ ደመወዞች',
    'recent_payslips': 'የቅርብ የደመወዝ ወረቀቶች',
    'recent_runs': 'የቅርብ ስራዎች',
    'confirm_payroll_processing': 'የደመወዝ ዝግጅቱን ያረጋግጡ',
    'enter_password_confirm': 'ለማረጋገጥ የይለፍ ቃልዎን ያስገቡ',
    'your_login_password': 'የመግቢያ ይለፍ ቃልዎ',
    'total_employees': 'ጠቅላላ ሰራተኞች',
    'total_gross': 'ጠቅላላ ጥቅል ደመወዝ',
    'total_tax': 'ጠቅላላ ግብር',
    'total_net': 'ጠቅላላ የተጣራ ክፍያ',
    # Overtime
    'overtime_this_month': 'የዚህ ወር ትርፍ ሰዓት',
    'total_hours': 'ጠቅላላ ሰዓት',
    'over_limit': 'ከገደብ በላይ',
    'hours': 'ሰዓታት',
    'type': 'ዓይነት',
    'rate': 'ተመን',
    # Compliance & Reports
    'compliance': 'ህግ ማክበር',
    'compliance_score': 'የህግ ማክበር ደረጃ',
    'compliance_details': 'የህግ ማክበር ዝርዝሮች',
    'erca_filing': 'ERCA Filing',
    'tax_filing_deadline': 'የግብር ማስታወቂያ የመጨረሻ ቀን',
    'pension_deadline': 'የጡረታ ክፍያ የመጨረሻ ቀን',
    'pension_contribution_deadline': 'የጡረታ መዋጮ የመጨረሻ ቀን',
    'pssa_remittance': 'PSSSA Remittance',
    'reports_compliance': 'ሪፖርቶችና ህግ ማክበር',
    'total_checks': 'ጠቅላላ ፍተሻዎች',
    'issue': 'ችግር',
    'override': 'ተሻገር',
    'reason': 'ምክንያት',
    'note': 'ማስታወሻ',
    'why_ok': 'ይህ ለምን ተፈቀደ?',
    # Dashboard
    'latest_net_pay': 'የቅርብ የተጣራ ክፍያ',
    'last_payroll_run': 'መጨረሻ የተሰራ ደመወዝ',
    'quick_actions': 'ፈጣን ተግባራት',
    # Termination
    'severance_preview': 'የስንብት ክፍያ ስሌት ቅድመ-እይታ',
    'termination_reason': 'የስንብት ምክንያት',
    'last_working_day': 'የመጨረሻ የስራ ቀን',
    'years_of_service': 'የአገልግሎት ዘመን',
    # Team & Linking
    'current_members': 'የአሁኑ አባላት',
    'add_team_member': 'የቡድን አባል መዝግብ',
    'phone_or_email': 'ስልክ ወይም ኢሜይል',
    'user_account': 'የተጠቃሚ መለያ',
    'link_employee_user': 'ሰራተኛውን ከተጠቃሚ መለያ ጋር አያይዝ',
    # Login & Registration
    'password': 'የይለፍ ቃል',
    'forgot_password': 'የይለፍ ቃል ረስተዋል?',
    'remember_me': 'አስታውሰኝ',
    'email': 'ኢሜይል',
    'yes': 'አዎ',
    'no': 'አይደለም',
    # CSV & Format
    'csv_format': 'የCSV ቅርፅ',
    'bank_telebirr': 'ባንክ / ቴሌብር',
    # Flash Messages
    'how_tax_calculated': 'ግብር እንዴት ይሰላል?',
    'tax_explainer_intro': 'የኢትዮጵያ ገቢ ግብር ተከታታይ ደረጃዎችን ይጠቀማል (ህግ ቁጥር 1395/2025)። ጡረታ ከግብር በፊት ይቀነሳል፣ የሚተካ ገቢዎን ይቀንሳል።',
    'bracket': 'ደረጃ',
    'taxable_range': 'የሚተካ ገቢ ክልል',
    'tax_rate': 'መጠን',
    'personal_relief': 'የግል ማስታገሻ',
    'per_month': 'በወር',
    'pension_before_tax': 'ጡረታ ከግብር በፊት ይቀነሳል',
    'of_basic_salary': 'የመነሻ ደመወዝ',
    'then_tax': 'ከዚያ ግብር ይሰላል',
}


def get_string(key: str, language: str = 'en') -> str:
    """
    Get a translated string.

    Args:
        key: String key
        language: 'en' for English, 'am' for Amharic, 'om' for Afaan Oromoo

    Returns:
        Translated string, or key itself if not found
    """
    if language == 'am':
        return STRINGS.get(key, key)
    if language == 'om':
        return STRINGS_OM.get(key, key)
    return key.replace('_', ' ').title()


def get_all_strings(language: str = 'en') -> dict:
    """Get all strings for a language."""
    if language == 'am':
        return STRINGS.copy()
    if language == 'om':
        return STRINGS_OM.copy()
    return {k: k.replace('_', ' ').title() for k in STRINGS}
