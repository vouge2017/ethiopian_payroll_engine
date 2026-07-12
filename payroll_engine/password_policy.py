"""Password strength validation for EthioPayroll."""

# Top 50 most common passwords globally + Ethiopian-contextual ones
COMMON_PASSWORDS = frozenset({
    'password', '123456', '12345678', '123456789', '1234567890',
    'qwerty', 'abc123', 'monkey', 'master', 'dragon',
    '111111', 'baseball', 'iloveyou', 'trustno1', 'sunshine',
    'princess', 'football', 'charlie', 'shadow', 'michael',
    'password1', 'password123', 'letmein', 'welcome', 'admin',
    'admin123', 'root', 'toor', 'pass', 'test',
    'guest', 'hello', 'love', 'god', 'money',
    'freedom', 'whatever', 'computer', 'internet', 'secret',
    'ethiopia', 'addis', 'addisababa', 'tigist', 'dawit',
    'ethiopian', 'payroll', 'salary', 'birr', 'etb',
})


def check_password_strength(password: str) -> tuple:
    """
    Check password strength beyond just length.

    Returns:
        (is_strong: bool, error_message: str or None)
    """
    if not password:
        return False, 'Password is required.'

    if len(password) < 8:
        return False, 'Password must be at least 8 characters.'

    if len(password) > 128:
        return False, 'Password is too long (max 128 characters).'

    lower = password.lower().strip()

    if lower in COMMON_PASSWORDS:
        return False, 'This password is too common. Choose something more unique.'

    # Check for all-same characters (e.g., 'aaaaaaa', '1111111')
    if len(set(password)) == 1:
        return False, 'Password cannot be all the same character.'

    # Check for sequential numbers
    if password in ('12345678', '123456789', '1234567890', '0987654321', '987654321'):
        return False, 'Password cannot be a sequential number.'

    # Must contain at least one letter or digit (not all symbols)
    if not any(c.isalnum() for c in password):
        return False, 'Password must contain at least one letter or number.'

    return True, None
