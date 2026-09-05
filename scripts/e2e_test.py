"""End-to-end Playwright tests for EthioPayroll authentication flows.

Tests the live Render deployment at https://ethiopian-payroll-engine.onrender.com
for:
  1. User registration (progressive profiling step 1)
  2. Onboarding (progressive profiling step 2: setup profile)
  3. Login (with the credentials from registration)
"""
import os
import sys
import io
import time
import random
import string
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright, expect, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://ethiopian-payroll-engine.onrender.com"
SCREENSHOT_DIR = Path("scripts/e2e_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def random_phone():
    """Generate a random 9-digit Ethiopian phone (starts with 9 or 7)."""
    first = random.choice(["7", "9"])
    rest = "".join(random.choices(string.digits, k=8))
    return f"{first}{rest}"


def random_email():
    """Generate a random email for testing."""
    suffix = "".join(random.choices(string.ascii_lowercase, k=8))
    return f"e2e.{suffix}@ethiopayroll-test.com"


def log_result(test_name, status, details=""):
    icon = "OK" if status == "PASS" else "FAIL" if status == "FAIL" else "WARN"
    print(f"[{status}] [{icon}] {test_name}")
    if details:
        for line in details.split("\n"):
            print(f"   {line}")


def test_registration_flow(page: Page, test_report: list):
    """Test Step 1 of registration: phone + password only."""
    test_name = "Registration (Step 1: phone + password)"
    try:
        phone = random_phone()
        email = random_email()
        password = "TestPass1!Secure"

        # Navigate to register page
        page.goto(f"{BASE_URL}/auth/register", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        page.screenshot(path=SCREENSHOT_DIR / "01_register_page.png", full_page=True)

        # Verify the form has ONLY phone + email + password (no name fields)
        html = page.content()
        if 'name="phone"' not in html:
            test_report.append({"test": test_name, "status": "FAIL", "details": "phone field missing"})
            log_result(test_name, "FAIL", "phone field missing")
            return None, None, None
        if 'name="password"' not in html:
            test_report.append({"test": test_name, "status": "FAIL", "details": "password field missing"})
            log_result(test_name, "FAIL", "password field missing")
            return None, None, None
        if 'name="first_name"' in html:
            test_report.append({"test": test_name, "status": "FAIL", "details": "first_name field SHOULD NOT exist (progressive profiling)"})
            log_result(test_name, "FAIL", "first_name exists (progressive profiling not applied)")
            return None, None, None
        if 'name="company_name"' in html:
            test_report.append({"test": test_name, "status": "FAIL", "details": "company_name field SHOULD NOT exist (progressive profiling)"})
            log_result(test_name, "FAIL", "company_name exists (progressive profiling not applied)")
            return None, None, None

        # Fill the form
        page.fill('input[name="phone"]', phone)
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.fill('input[name="password2"]', password)

        page.screenshot(path=SCREENSHOT_DIR / "02_register_filled.png", full_page=True)

        # Submit
        page.click('button[type="submit"]')

        # Wait for any URL change (not specific URL)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            pass
        time.sleep(3)

        current_url = page.url
        page.screenshot(path=SCREENSHOT_DIR / "03_after_register.png", full_page=True)

        if "/auth/setup-profile" in current_url:
            test_report.append({
                "test": test_name,
                "status": "PASS",
                "details": f"Registered {phone}, redirected to {current_url}",
            })
            log_result(test_name, "PASS", f"Phone {phone} registered, redirected to setup-profile")
            return phone, email, password
        else:
            # Check for error
            body = page.content()
            error_text = ""
            for indicator in ["error", "invalid", "required", "failed", "missing", "expired"]:
                if indicator in body.lower():
                    idx = body.lower().find(indicator)
                    # Find alert class
                    error_match = body[max(0, idx-200):idx+200]
                    if "alert" in error_match.lower():
                        error_text = error_match
                        break
            test_report.append({
                "test": test_name,
                "status": "FAIL",
                "details": f"Expected /auth/setup-profile, got {current_url}. Error: {error_text[:200] if error_text else 'no error visible'}",
                "phone": phone, "email": email, "password": password,
            })
            log_result(test_name, "FAIL", f"Got {current_url}, expected /auth/setup-profile. Error: {error_text[:200] if error_text else 'none'}")
            return phone, email, password  # Return credentials anyway so other tests can run

    except Exception as e:
        page.screenshot(path=SCREENSHOT_DIR / f"register_exception_{int(time.time())}.png", full_page=True)
        test_report.append({
            "test": test_name,
            "status": "FAIL",
            "details": f"Exception: {type(e).__name__}: {e}",
        })
        log_result(test_name, "FAIL", f"Exception: {type(e).__name__}: {e}")
        return None, None, None


def test_onboarding_flow(page: Page, phone: str, email: str, password: str, test_report: list):
    """Test Step 2 of registration: setup profile (name + company)."""
    test_name = "Onboarding (Step 2: setup profile)"
    try:
        # We should already be on /auth/setup-profile from the previous test
        if "/auth/setup-profile" not in page.url:
            page.goto(f"{BASE_URL}/auth/setup-profile", wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)

        # Generate unique company name
        company_name = f"E2E Test Co {random.randint(1000, 9999)}"

        # Fill the setup profile form
        page.fill('input[name="first_name"]', "E2E")
        page.fill('input[name="middle_name"]', "Test")
        page.fill('input[name="last_name"]', "User")
        page.fill('input[name="company_name"]', company_name)

        page.screenshot(path=SCREENSHOT_DIR / "04_setup_profile_filled.png", full_page=True)

        # Submit
        page.click('button[type="submit"]')

        # Wait for redirect to /
        try:
            page.wait_for_url(f"{BASE_URL}/", timeout=30000)
        except PlaywrightTimeoutError:
            current_url = page.url
            page.screenshot(path=SCREENSHOT_DIR / "05_setup_profile_error.png", full_page=True)
            test_report.append({
                "test": test_name,
                "status": "FAIL",
                "details": f"Expected redirect to / but got {current_url}",
            })
            log_result(test_name, "FAIL", f"Got {current_url}, expected /")
            return False

        time.sleep(2)
        page.screenshot(path=SCREENSHOT_DIR / "05_dashboard.png", full_page=True)

        # Verify we're logged in (no longer on auth pages)
        body = page.content()
        if "/auth/login" in page.url or "/auth/register" in page.url:
            test_report.append({
                "test": test_name,
                "status": "FAIL",
                "details": f"User not logged in after profile setup. URL: {page.url}",
            })
            log_result(test_name, "FAIL", f"User not logged in, URL: {page.url}")
            return False

        test_report.append({
            "test": test_name,
            "status": "PASS",
            "details": f"Profile completed for company '{company_name}'. User is now logged in. URL: {page.url}",
        })
        log_result(test_name, "PASS", f"Profile completed, company '{company_name}', logged in")
        return True

    except Exception as e:
        page.screenshot(path=SCREENSHOT_DIR / f"onboarding_exception_{int(time.time())}.png", full_page=True)
        test_report.append({
            "test": test_name,
            "status": "FAIL",
            "details": f"Exception: {type(e).__name__}: {e}",
        })
        log_result(test_name, "FAIL", f"Exception: {type(e).__name__}: {e}")
        return False


def test_logout(page: Page, test_report: list):
    """Test logout."""
    test_name = "Logout"
    try:
        # Try common logout URLs
        logout_urls = ["/auth/logout", "/logout"]
        for url in logout_urls:
            try:
                r = page.goto(f"{BASE_URL}{url}", wait_until="domcontentloaded", timeout=10000)
                if r and r.status == 200:
                    time.sleep(1)
                    if "/auth/login" in page.url:
                        log_result(test_name, "PASS", f"Logged out via {url}, redirected to login")
                        test_report.append({"test": test_name, "status": "PASS", "details": f"Logged out via {url}"})
                        return True
            except Exception:
                continue
        log_result(test_name, "WARN", "Could not find logout URL")
        test_report.append({"test": test_name, "status": "WARN", "details": "No logout URL found"})
        return False
    except Exception as e:
        log_result(test_name, "FAIL", f"Exception: {e}")
        test_report.append({"test": test_name, "status": "FAIL", "details": f"Exception: {e}"})
        return False


def test_login_flow(page: Page, phone: str, password: str, test_report: list):
    """Test login with credentials from registration."""
    test_name = "Login with registered credentials"
    try:
        # Make sure we're logged out
        page.goto(f"{BASE_URL}/auth/logout", timeout=10000)
        time.sleep(1)

        # Go to login page
        page.goto(f"{BASE_URL}/auth/login", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        page.screenshot(path=SCREENSHOT_DIR / "06_login_page.png", full_page=True)

        # Verify Phone/Email tabs are present
        html = page.content()
        assert 'data-phone-tab="phone"' in html, "Phone tab missing"
        assert 'data-phone-tab="email"' in html, "Email tab missing"
        assert 'phone-prefix-box' in html, "Phone prefix box missing"

        # Fill the login form
        page.fill('input[name="login_id"]', phone)
        page.fill('input[name="password"]', password)

        page.screenshot(path=SCREENSHOT_DIR / "07_login_filled.png", full_page=True)

        # Submit
        page.click('button[type="submit"]')

        # Wait for redirect to dashboard (NOT to /auth/login)
        try:
            # Wait for URL to NOT be /auth/login
            page.wait_for_url(lambda url: "/auth/login" not in url, timeout=30000)
        except PlaywrightTimeoutError:
            current_url = page.url
            body = page.content()
            page.screenshot(path=SCREENSHOT_DIR / "08_login_error.png", full_page=True)
            # Check for error message
            error_indicators = ["incorrect", "invalid", "failed", "error"]
            error_text = ""
            for indicator in error_indicators:
                if indicator in body.lower():
                    idx = body.lower().find(indicator)
                    error_text = body[max(0, idx-20):idx+100]
                    break
            test_report.append({
                "test": test_name,
                "status": "FAIL",
                "details": f"Login failed. Still on {current_url}. Error: {error_text}",
            })
            log_result(test_name, "FAIL", f"Login failed at {current_url}: {error_text[:100]}")
            return False

        time.sleep(2)
        page.screenshot(path=SCREENSHOT_DIR / "09_dashboard_after_login.png", full_page=True)

        test_report.append({
            "test": test_name,
            "status": "PASS",
            "details": f"Login successful. Redirected to {page.url}",
        })
        log_result(test_name, "PASS", f"Logged in, redirected to {page.url}")
        return True

    except Exception as e:
        page.screenshot(path=SCREENSHOT_DIR / f"login_exception_{int(time.time())}.png", full_page=True)
        test_report.append({
            "test": test_name,
            "status": "FAIL",
            "details": f"Exception: {type(e).__name__}: {e}",
        })
        log_result(test_name, "FAIL", f"Exception: {type(e).__name__}: {e}")
        return False


def test_login_with_bad_password(page: Page, phone: str, test_report: list):
    """Test login with wrong password — should show error."""
    test_name = "Login with wrong password (negative test)"
    try:
        page.goto(f"{BASE_URL}/auth/login", wait_until="domcontentloaded", timeout=30000)
        time.sleep(1)

        page.fill('input[name="login_id"]', phone)
        page.fill('input[name="password"]', "WrongPassword1!")
        page.click('button[type="submit"]')

        # Should stay on /auth/login with an error
        time.sleep(3)
        if "/auth/login" in page.url:
            body = page.content()
            has_error = any(word in body.lower() for word in ["incorrect", "invalid", "wrong", "failed"])
            if has_error:
                test_report.append({"test": test_name, "status": "PASS", "details": "Wrong password correctly rejected"})
                log_result(test_name, "PASS", "Wrong password rejected with error message")
                return True
            else:
                test_report.append({"test": test_name, "status": "WARN", "details": "Stayed on login but no error visible"})
                log_result(test_name, "WARN", "No error message visible")
                return False
        else:
            test_report.append({"test": test_name, "status": "FAIL", "details": f"Redirected to {page.url} with wrong password"})
            log_result(test_name, "FAIL", f"Wrong password didn't keep user on login, got {page.url}")
            return False
    except Exception as e:
        test_report.append({"test": test_name, "status": "FAIL", "details": f"Exception: {e}"})
        log_result(test_name, "FAIL", f"Exception: {e}")
        return False


def test_login_form_ux(page: Page, test_report: list):
    """Test login form UX: tabs, prefix, placeholders."""
    test_name = "Login form UX (tabs, prefix, placeholders)"
    try:
        page.goto(f"{BASE_URL}/auth/login", wait_until="domcontentloaded", timeout=30000)
        time.sleep(1)
        page.screenshot(path=SCREENSHOT_DIR / "10_login_ux.png", full_page=True)

        html = page.content()
        issues = []

        # Verify Phone/Email tabs
        if 'data-phone-tab="phone"' not in html:
            issues.append("Missing Phone tab")
        if 'data-phone-tab="email"' not in html:
            issues.append("Missing Email tab")

        # Verify +251 prefix
        if 'phone-prefix-box' not in html:
            issues.append("Missing phone prefix box")
        if '+251' not in html:
            issues.append("Missing +251 prefix text")

        # Verify placeholder
        if '91 234 5678' not in html:
            issues.append("Phone placeholder '91 234 5678' missing")

        # Test tab switching
        page.click('[data-phone-tab="email"]')
        time.sleep(0.5)
        page.screenshot(path=SCREENSHOT_DIR / "11_email_tab.png", full_page=True)
        email_html = page.content()

        if 'name="company"' in email_html.lower() or "email" not in email_html.lower():
            # Tab might not have switched properly
            issues.append("Email tab didn't switch correctly")

        if issues:
            test_report.append({"test": test_name, "status": "FAIL", "details": "; ".join(issues)})
            log_result(test_name, "FAIL", "; ".join(issues))
            return False
        else:
            test_report.append({"test": test_name, "status": "PASS", "details": "All UX elements present and functional"})
            log_result(test_name, "PASS", "All UX elements present")
            return True
    except Exception as e:
        test_report.append({"test": test_name, "status": "FAIL", "details": f"Exception: {e}"})
        log_result(test_name, "FAIL", f"Exception: {e}")
        return False


def main():
    print(f"\n{'='*70}")
    print(f"E2E Test Suite for EthioPayroll Authentication")
    print(f"Target: {BASE_URL}")
    print(f"Screenshots: {SCREENSHOT_DIR.absolute()}")
    print(f"{'='*70}\n")

    test_report = []

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context: BrowserContext = browser.new_context(viewport={"width": 1280, "height": 900})
        page: Page = context.new_page()

        # Run tests in sequence (since they depend on each other)
        # Test 1: Registration
        phone, email, password = test_registration_flow(page, test_report)
        if phone is None:
            print("\n❌ Registration failed — cannot test subsequent flows")
            browser.close()
            return test_report

        # Test 2: Onboarding (progressive step 2)
        success = test_onboarding_flow(page, phone, email, password, test_report)
        if not success:
            print("\n❌ Onboarding failed — cannot test login")

        # Test 3: Logout
        test_logout(page, test_report)

        # Test 4: Login with registered credentials
        test_login_flow(page, phone, password, test_report)

        # Test 5: Login with wrong password
        test_login_with_bad_password(page, phone, test_report)

        # Test 6: Login form UX
        test_login_form_ux(page, test_report)

        browser.close()

    # Print summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")
    passed = sum(1 for r in test_report if r["status"] == "PASS")
    failed = sum(1 for r in test_report if r["status"] == "FAIL")
    warned = sum(1 for r in test_report if r["status"] == "WARN")
    print(f"Total: {len(test_report)} | ✅ Passed: {passed} | ❌ Failed: {failed} | ⚠️ Warnings: {warned}\n")

    if failed > 0:
        print("FAILED TESTS:")
        for r in test_report:
            if r["status"] == "FAIL":
                print(f"  - {r['test']}: {r['details']}")

    return test_report


if __name__ == "__main__":
    report = main()
    sys.exit(0 if all(r["status"] != "FAIL" for r in report) else 1)
