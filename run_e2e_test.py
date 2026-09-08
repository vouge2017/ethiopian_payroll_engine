import pytest
import sys

# Run just the e2e_full test to see if it passes
print('Running E2E full test...')
result = pytest.main(['tests/test_e2e_full.py', '-v', '--tb=line'])
if result == 0:
    print('SUCCESS: E2E full test passed!')
else:
    print(f'FAILED: E2E full test failed with exit code {result}')
    sys.exit(1)
