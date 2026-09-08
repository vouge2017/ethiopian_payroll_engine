import re

def validate_ethiopian_phone(phone: str) -> tuple:
    if not phone:
        return False, None, 'Phone number is required.'
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    m = re.match(r'^\+251(7\d{8}|9\d{8})$', cleaned)
    if m:
        return True, m.group(1), None
    m = re.match(r'^(7\d{8}|9\d{8})$', cleaned)
    if m:
        return True, m.group(1), None
    return False, None, 'Invalid phone format'

# Test the old format
old_phone = '0911123456'
is_valid, normalized, error = validate_ethiopian_phone(old_phone)
print(f'Old format: {old_phone} -> Valid: {is_valid}, Normalized: {normalized}, Error: {error}')

# Test the new format
new_phone = '911123456'
is_valid, normalized, error = validate_ethiopian_phone(new_phone)
print(f'New format: {new_phone} -> Valid: {is_valid}, Normalized: {normalized}, Error: {error}')

# Test with +251 prefix
intl_phone = '+251911123456'
is_valid, normalized, error = validate_ethiopian_phone(intl_phone)
print(f'Intl format: {intl_phone} -> Valid: {is_valid}, Normalized: {normalized}, Error: {error}')
