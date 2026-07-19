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
    'settings': 'ማስተካከያዎች',
    'team': 'የቡድን አባላት',
    'my_dashboard': 'የእኔ ዳሽቦርድ',
    'my_payslips': 'የእኔ የደመወዝ ወረቀቶች',
    'my_profile': 'የእኔ መገለጫ',
    'logout': 'ውጣ',
    'log_in': 'ግባ',
    'register': 'ተመዝገብ',
    'sign_in_message': 'ደመወዝ ለማስተዳደር ይግቡ',
    'create_account': 'መለያ ይክፈቱ',
    'start_payroll_message': 'የድርጅትዎን ደመወዝ ማስተዳደር ይጀምሩ',
    'add_employee': 'ሰራተኛ መዝግብ',
    'save_employee': 'ሰራተኛ አስቀምጥ',
    'cancel': 'ሰርዝ',
    'search': 'ፈልግ',
    'search_placeholder': 'በስም ወይም መታወቂያ ፈልግ...',
    'upload_csv': 'CSV ጭን',
    'select_csv': 'የCSV ፋይል ምረጥ',
    'view_all': 'ሁሉንም እይ',
    'download': 'አውርድ',
    'add': 'መዝግብ',
    'delete': 'አጥፋ',
    'edit': 'አድስ',
    'confirm_approve': 'አረጋግጥና አጽድቅ',
    'reactivate': 'መልሰህ አንቃ',
    'link': 'አያይዝ',
    'terminate_employee': 'ሰራተኛ አሰናብት',
    'add_first_employee': 'የመጀመሪያ ሰራተኛዎን ይመዝግቡ',
    'run_first_payroll': 'የመጀመሪያ ደመወዝዎን ያዘጋጁ',
    'english': 'እንግሊዘኛ',
    'oromoo': 'ኦሮሞኛ',
    'actions': 'ተግባራት',
    'show_calculation': 'ስሌት አሳይ',
    'entries': 'ምዝገባዎች',
    'overtime': 'ትርፍ ሰዓት',
    'amharic_coming_soon': 'የአማርኛ ትርጉም በቅርቡ ይደርሳል',
    'oromoo_coming_soon': 'የአፋን ኦሮሞ ትርጉም በቅርቡ ይደርሳል',

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
    'active': 'ንቁ',
    'deactivated': 'የታገደ',
    'basic_information': 'መሠረታዊ መረጃ',
    'compensation': 'ጥቅማጥቅሞች',
    'payment_tax': 'ክፍያ እና ታክስ',
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
    'rule': 'ደንብ',
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
    'example_emp': 'ምሳሌ፦ EMP001',
    'finance': 'ፋይናንስ',
    'accountant': 'አካውንታንት',

    # Flash Messages
    'err_employee_id_name_required': 'የሰራተኛ መታወቂያ እና ስም ያስፈልጋል።',
    'err_phone_name_required': 'የስልክ ቁጥር እና ስም ያስፈልጋል።',
    'err_invalid_date_format': 'የተሳሳተ የቀን ቅርፅ። እባክዎ YYYY-MM-DD ይጠቀሙ።',
    'err_invalid_date': 'የተሳሳተ የቀን ቅርፅ።',
    'err_invalid_termination_reason': 'የተሳሳተ የስንብት ምክንያት።',
    'err_invalid_request': 'የተሳሳተ ጥያቄ።',
    'err_csv_only': 'የCSV ፋይሎች ብቻ ይፈቀዳሉ።',
    'err_no_file': 'ምንም ፋይል አልተመረጠም።',
    'err_no_payslips_run': 'ለዚህ የደመወዝ ዝግጅት ምንም ወረቀት አልተገኘም።',
    'err_pdf_not_found': 'PDF አልተገኘም።',
    'err_unresolved_blocks': 'መቀጠል አይቻልም፦ ያልተፈቱ የዕገዳ (BLOCK) ችግሮች አሉ።',
    'err_cannot_reject_review': 'በግምገማ ላይ ያለን ደመወዝ ውድቅ ማድረግ አይቻልም።',
    'err_cannot_remove_owner': 'የድርጅቱን ባለቤት መሰረዝ አይቻልም።',
    'err_exceed_24h': 'በአንድ ቀን ውስጥ ከ24 ሰዓት መብለጥ አይችልም።',
    'err_wrong_password_approval': 'የተሳሳተ የይለፍ ቃል፤ ማጽደቁ ተሰርዟል።',
    'err_wrong_password_termination': 'የተሳሳተ የይለፍ ቃል፤ ስንብቱ ተሰርዟል።',
    'err_not_in_review': 'ይህ የደመወዝ ዝግጅት በግምገማ ሁኔታ ላይ አይደለም።',
    'err_not_ready_approval': 'ይህ የደመወዝ ዝግጅት ለማጽደቅ አልተዘጋጀም።',
    'err_already_member': 'ይህ ተጠቃሚ ቀድሞውኑ የድርጅትዎ አባል ነው።',
    'err_already_access': 'ይህ ተጠቃሚ ቀድሞውኑ ወደ ድርጅትዎ መግቢያ አለው።',
    'err_cannot_remove_self': 'እራስዎን መሰረዝ አይችሉም።',
    'err_no_access_company': 'ወደዚያ ድርጅት ለመግባት ፈቃድ የለዎትም።',
    'err_no_permission': 'ይህንን ተግባር ለማከናወን ፈቃድ የለዎትም።',
    'err_valid_date_hours': 'ትክክለኛ ቀን እና ሰዓታት ያስፈልጋሉ።',
    'err_payroll_data_not_found': 'የደመወዝ መረጃ አልተገኘም። ረቂቁ ተሰርዞ ሊሆን ይችላል፤ እባክዎ CSV ፋይሉን እንደገና ይጫኑ።',
    'msg_payroll_submitted': 'ደመወዙ ለባለቤቱ ማረጋገጫ ቀርቧል።',
    'msg_overtime_deleted': 'የትርፍ ሰዓት መረጃው ተሰርዟል።',
    'err_reports_completed_only': 'ሪፖርት ማውጣት የሚቻለው ለተጠናቀቁ የደመወዝ ስራዎች ብቻ ነው።',
    'err_bank_file_completed_only': 'የባንክ ፋይል ማዘጋጀት የሚቻለው ለተጠናቀቁ የደመወዝ ስራዎች ብቻ ነው።',
    'err_not_linked': 'መለያዎ ከሰራተኛ መዝገብ ጋር አልተያያዘም። እባክዎ የሰው ኃይል (HR) ባለሙያዎን ያነጋግሩ።',
    'err_both_required': 'ሰራተኛውም ሆነ ተጠቃሚው ያስፈልጋሉ።',
    'how_tax_calculated': 'ግብር እንዴት ይሰላል?',
    'tax_explainer_intro': 'የኢትዮጵያ ገቢ ግብር ተከታታይ ብርacket ይጠቀማል ( proclamation ቁጥር 1395/2025)። ጡረታ ከግብር በፊት ይቀነሳል፣ የሚተካ ገቢዎን ይቀንሳል።',
    'bracket': 'ብርacket',
    'taxable_range': 'የሚተካ ገቢ ክልል',
    'rate': 'መጠን',
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
