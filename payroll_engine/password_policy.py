"""Password strength validation for EthioPayroll."""

import re

# Expanded common passwords list (top 200 globally + Ethiopian-contextual)
COMMON_PASSWORDS = frozenset(
    {
        # Global top 50
        'password',
        '123456',
        '12345678',
        '123456789',
        '1234567890',
        'qwerty',
        'abc123',
        'monkey',
        'master',
        'dragon',
        '111111',
        'baseball',
        'iloveyou',
        'trustno1',
        'sunshine',
        'princess',
        'football',
        'charlie',
        'shadow',
        'michael',
        'password1',
        'password123',
        'letmein',
        'welcome',
        'admin',
        'admin123',
        'root',
        'toor',
        'pass',
        'test',
        'guest',
        'hello',
        'love',
        'god',
        'money',
        'freedom',
        'whatever',
        'computer',
        'internet',
        'secret',
        # Extended global
        'login',
        'starwars',
        'batman',
        'spiderman',
        'superman',
        'jordan',
        'phoenix',
        'mustang',
        'access',
        'killer',
        'hunter',
        'thomas',
        'robert',
        'daniel',
        'jessica',
        'matrix',
        'apple',
        'orange',
        'banana',
        'summer',
        'winter',
        'spring',
        'autumn',
        'soccer',
        'hockey',
        'ranger',
        'pepper',
        'cookie',
        'samsung',
        'iphone',
        # Ethiopian-contextual
        'ethiopia',
        'addis',
        'addisababa',
        'tigist',
        'dawit',
        'ethiopian',
        'payroll',
        'salary',
        'birr',
        'etb',
        'habesha',
        'meskel',
        'timkat',
        'genna',
        'ashenda',
        'selam',
        'merkato',
        'bole',
        'piassa',
        'arada',
        'amharic',
        'oromia',
        'tigray',
        'harar',
        'dire',
    }
)

# Keyboard patterns (adjacent key sequences)
KEYBOARD_PATTERNS = frozenset(
    {
        'qwerty',
        'qwertyui',
        'qwertyuiop',
        'asdfgh',
        'asdfghjkl',
        'zxcvbn',
        'zxcvbnm',
        'qazwsx',
        'edcrfv',
        'tgbyhn',
        'qweasd',
        'asdzxc',
        '1qaz2wsx',
        'q1w2e3',
        'zaq1xsw2',
        '1q2w3e',
        'q1w2e3r4',
        '1qaz2wsx3edc',
        'abcd',
        'abcdef',
        'abcdefg',
        'abcdefgh',
        'abcdefghi',
        'abcdefghij',
    }
)

# Common dictionary words that shouldn't be the base of a password
DICTIONARY_WORDS = frozenset(
    {
        'password',
        'passw0rd',
        'p@ssword',
        'p@ssw0rd',
        'admin',
        'root',
        'user',
        'login',
        'welcome',
        'master',
        'dragon',
        'monkey',
        'shadow',
        'sunshine',
        'princess',
        'football',
        'baseball',
        'soccer',
        'hockey',
        'computer',
        'internet',
        'security',
        'system',
        'network',
        'company',
        'office',
        'school',
        'college',
        'university',
        'family',
        'friend',
        'love',
        'baby',
        'angel',
        'money',
        'cash',
        'bank',
        'rich',
        'gold',
        'ethiopia',
        'addis',
        'habesha',
        'tigist',
        'dawit',
        'payroll',
        'salary',
        'worker',
        'employee',
        'manager',
    }
)


def _has_keyboard_pattern(password: str, min_length: int = 4) -> bool:
    """Check if password contains a keyboard walk pattern."""
    lower = password.lower()
    for pattern in KEYBOARD_PATTERNS:
        if pattern in lower:
            return True
    # Check for reverse patterns
    return any(pattern[::-1] in lower for pattern in KEYBOARD_PATTERNS)


def _has_repeated_chars(password: str, min_repeat: int = 3) -> bool:
    """Check for repeated characters (e.g., 'aaa', '111')."""
    return any(len(set(password[i : i + min_repeat])) == 1 for i in range(len(password) - min_repeat + 1))


def _has_dict_word_plus_year(password: str) -> bool:
    """Check if password is a dictionary/common word + year or short number."""
    lower = password.lower().strip()

    # Only match if the word part is in our known dictionary/common lists
    patterns = [
        r'^([a-z]+)(20\d{2})$',  # word2024, word2025
        r'^([a-z]+)(19\d{2})$',  # word1990
        r'^([a-z]+)(\d{1,3})$',  # word1, word12, word123
        r'^(\d{4})([a-z]+)$',  # 2025word
        r'^([a-z]+)[!@#$%&*](\d*)$',  # word!123, word@2025
        r'^([a-z]+)(\d*)[!@#$%&*]$',  # word123!, word2025@
    ]

    known_words = DICTIONARY_WORDS | COMMON_PASSWORDS

    for pattern in patterns:
        m = re.match(pattern, lower)
        if m:
            word_part = m.group(1)
            if word_part in known_words:
                return True

    return False


def _has_sequential_chars(password: str, min_length: int = 4) -> bool:
    """Check for sequential characters (abcd, 1234, dcba, 4321)."""
    lower = password.lower()
    # Ascending sequences
    for i in range(len(lower) - min_length + 1):
        chunk = lower[i : i + min_length]
        if chunk.isalpha() and all(ord(chunk[j + 1]) == ord(chunk[j]) + 1 for j in range(len(chunk) - 1)):
            return True
        if chunk.isdigit() and all(int(chunk[j + 1]) == int(chunk[j]) + 1 for j in range(len(chunk) - 1)):
            return True
    # Descending sequences
    for i in range(len(lower) - min_length + 1):
        chunk = lower[i : i + min_length]
        if chunk.isalpha() and all(ord(chunk[j + 1]) == ord(chunk[j]) - 1 for j in range(len(chunk) - 1)):
            return True
        if chunk.isdigit() and all(int(chunk[j + 1]) == int(chunk[j]) - 1 for j in range(len(chunk) - 1)):
            return True
    return False


def check_password_strength(password: str) -> tuple:
    """
    Check password strength with comprehensive pattern detection.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Not a common password
    - Not a keyboard pattern
    - Not dictionary word + year/number
    - No repeated character runs (3+)
    - No sequential character runs (4+)

    Returns:
        (is_strong: bool, error_message: str or None)
    """
    if not password:
        return False, 'Password is required.'

    if len(password) < 8:
        return False, 'Password must be at least 8 characters.'

    if len(password) > 128:
        return False, 'Password is too long (max 128 characters).'

    # Character class requirements
    if not any(c.isupper() for c in password):
        return False, 'Password must contain at least one uppercase letter.'

    if not any(c.islower() for c in password):
        return False, 'Password must contain at least one lowercase letter.'

    if not any(c.isdigit() for c in password):
        return False, 'Password must contain at least one digit.'

    lower = password.lower().strip()

    # Common password check
    if lower in COMMON_PASSWORDS:
        return False, 'This password is too common. Choose something more unique.'

    # Common password + common suffix (password!, password1, etc.)
    base = lower.rstrip('0123456789!@#$%&*')
    if base in COMMON_PASSWORDS:
        return False, 'This password is based on a common password.'

    # Keyboard pattern check
    if _has_keyboard_pattern(password):
        return False, 'Password contains a keyboard pattern (e.g., qwerty, asdf).'

    # Dictionary word + year/number
    if _has_dict_word_plus_year(password):
        return False, 'Password is a predictable word+number pattern (e.g., ethiopia2025).'

    # Sequential characters (abcd, 1234)
    if _has_sequential_chars(password):
        return False, 'Password contains sequential characters (e.g., abcd, 1234).'

    # Repeated characters (aaa, 111)
    if _has_repeated_chars(password):
        return False, 'Password contains repeated characters (e.g., aaa, 111).'

    # All-same character check (redundant with repeated, but explicit)
    if len(set(password)) == 1:
        return False, 'Password cannot be all the same character.'

    # Must contain at least one letter or digit (not all symbols)
    if not any(c.isalnum() for c in password):
        return False, 'Password must contain at least one letter or number.'

    return True, None
