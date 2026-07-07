"""
Multilingual Language Strings — Core UI Translation

Supports: English (en), Amharic (am), Afaan Oromoo (om)

Usage in templates:
    {{ _('dashboard') }}  → 'ዳሽቦርድ' (Amharic) or 'Dashboard' (English) or 'Gabatee' (Afaan Oromoo)
"""

from payroll_engine.i18n_om import STRINGS_OM

# Amharic strings for core UI elements
STRINGS = {
    # Navigation
    'dashboard': 'ዳሽቦርድ',
    'employees': 'ሰራተኞች',
    'payroll': 'የደመወዝ ክፍያ',
    'reports': 'ሪፖርቶች',
    'settings': 'ቅንብሮች',
    'logout': 'ውጣ',

    # Actions
    'run_payroll': 'የደመወዝ ክፍያ ጀምር',
    'add_employee': 'ሰራተኛ ጨምር',
    'save': 'አስቀምጥ',
    'cancel': 'ሰርዝ',
    'approve': 'አጽድቅ',
    'download': 'አውርድ',
    'upload': 'ስቀል',
    'search': 'ፈልግ',
    'view': 'ተመልከት',

    # Payroll
    'basic_salary': 'መሰረታዊ ደመወዝ',
    'allowances': 'አበሪዎች',
    'gross_salary': 'ጠቅላይ ደመወዝ',
    'income_tax': 'የገቢ ታክስ',
    'employee_pension': 'የሰራተኛ እቅድ',
    'employer_pension': 'የሰራተኛ አሰዳቢ እቅድ',
    'net_pay': 'ንፅ ደመወዝ',
    'payment_method': 'የክፍያ ዘዴ',

    # Status
    'completed': 'ተጠናቅቋል',
    'processing': 'በሂደት ላይ',
    'pending': 'በመጠባበቅ ላይ',
    'failed': 'አልተሳካም',
    'draft': 'ረቂቅ',
    'review': 'ግምገማ',

    # Employee
    'employee_id': 'የሰራተኛ መለያ',
    'full_name': 'ሙሉ ስም',
    'tin': 'የግብር መለያ ቁጥር',
    'bank_account': 'የባንክ ሂሳብ',

    # Reports
    'erca_report': 'ERCA ሪፖርት',
    'pension_report': 'የእቅድ ሪፖርት',
    'bank_file': 'የባንክ ፋይል',
    'compliance_score': 'የተገዢነት ነጥብ',

    # Messages
    'welcome': 'እንኳን ደህና መጣህ',
    'payroll_completed': 'የደመወዝ ክፍያ ተጠናቅቋል',
    'no_employees': 'ሰራተኞች የሉም',
    'no_payslips': 'የደመወዝ ቲcket የለም',

    # Validation
    'required_field': 'ይህ መስክ ያስፈልጋል',
    'invalid_number': 'ትክክለኛ ቁጥር ያስገቡ',
    'missing_bank': 'የባንክ መረጃ የለም',

    # Compliance
    'erca_deadline': 'ERCA የመጨረሻ ቀን',
    'pension_deadline': 'የእቅድ የመጨረሻ ቀን',
    'days_remaining': 'የቀሩ ቀናት',
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
