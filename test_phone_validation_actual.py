import sys
sys.path.insert(0, '.')

from payroll_engine.models import validate_ethiopian_phone

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
