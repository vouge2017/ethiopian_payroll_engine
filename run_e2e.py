import pytest

# Run E2E full test
if __name__ == "__main__":
    exit_code = pytest.main(['tests/test_e2e_full.py', '-v', '--tb=line', '--no-header'])
    exit(exit_code)
