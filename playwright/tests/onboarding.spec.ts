import { test, expect } from './fixtures';
import { RegisterPage } from '../pages/RegisterPage';
import { SetupProfilePage } from '../pages/SetupProfilePage';
import { DashboardPage } from '../pages/DashboardPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('Onboarding Flow', () => {
  let uniquePhone: string;

  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const last4 = String(timestamp).slice(-4);
    uniquePhone = `911${last4}456`;
  });

  test.afterEach(async ({ page }) => {
    // Cleanup - logout if logged in
    try {
      await page.goto('/auth/logout');
    } catch {
      // Ignore cleanup errors
    }
  });

  test.describe('1. Registration', () => {
    test('should display registration form with all required fields', async ({ registerPage }) => {
      await registerPage.goto();

      await expect(registerPage.phoneInput).toBeVisible();
      await expect(registerPage.passwordInput).toBeVisible();
      await expect(registerPage.confirmPasswordInput).toBeVisible();
      await expect(registerPage.registerButton).toBeVisible();
    });

    test('should register new user with valid phone and password', async ({ registerPage, setupProfilePage }) => {
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      // Should redirect to setup-profile
      await expect(page).toHaveURL(/\/auth\/setup-profile/);

      // Setup profile page should be visible
      await expect(setupProfilePage.firstNameInput).toBeVisible();
    });

    test('should reject invalid phone format (leading zero)', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.phoneInput.fill('0911234567');
      await registerPage.passwordInput.fill('SecurePass123!');
      await registerPage.confirmPasswordInput.fill('SecurePass123!');
      await registerPage.registerButton.click();

      await registerPage.expectPhoneValidationError();
    });

    test('should reject invalid phone format (too short)', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.phoneInput.fill('91234');
      await registerPage.passwordInput.fill('SecurePass123!');
      await registerPage.confirmPasswordInput.fill('SecurePass123!');
      await registerPage.registerButton.click();

      await registerPage.expectPhoneValidationError();
    });

    test('should reject weak password', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.phoneInput.fill(uniquePhone);
      await registerPage.passwordInput.fill('123');
      await registerPage.confirmPasswordInput.fill('123');
      await registerPage.registerButton.click();

      await registerPage.expectPasswordValidationError();
    });

    test('should reject password without uppercase', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.phoneInput.fill(uniquePhone);
      await registerPage.passwordInput.fill('securepass123!');
      await registerPage.confirmPasswordInput.fill('securepass123!');
      await registerPage.registerButton.click();

      await registerPage.expectPasswordValidationError();
    });

    test('should reject password without symbol', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.phoneInput.fill(uniquePhone);
      await registerPage.passwordInput.fill('SecurePass123');
      await registerPage.confirmPasswordInput.fill('SecurePass123');
      await registerPage.registerButton.click();

      await registerPage.expectPasswordValidationError();
    });

    test('should reject password mismatch', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.phoneInput.fill(uniquePhone);
      await registerPage.passwordInput.fill('SecurePass123!');
      await registerPage.confirmPasswordInput.fill('DifferentPass123!');
      await registerPage.registerButton.click();

      await expect(page.locator('.alert-danger, .error-message').first()).toBeVisible();
    });

    test('should reject duplicate phone number', async ({ registerPage }) => {
      // First registration
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      // Logout
      await page.goto('/auth/logout');

      // Try to register with same phone
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      await registerPage.expectErrorMessage(/already.*registered|exists/i);
    });

    test('should navigate to login from register page', async ({ registerPage }) => {
      await registerPage.goto();
      await registerPage.clickLogin();

      await expect(page).toHaveURL(/\/auth\/login/);
    });
  });

  test.describe('2. Profile Setup', () => {
    test('should complete profile setup and redirect to dashboard', async ({ registerPage, setupProfilePage, dashboardPage }) => {
      // Register first
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      // Complete profile
      await setupProfilePage.completeProfile('Tigist', 'Hailu', 'Tigist Trading PLC');

      // Should be on dashboard
      await expect(page).toHaveURL(/\/$|\/dashboard/);
      await expect(dashboardPage.logoutButton).toBeVisible();
    });

    test('should require first name', async ({ registerPage, setupProfilePage }) => {
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      await setupProfilePage.lastNameInput.fill('Test');
      await setupProfilePage.companyNameInput.fill('Test Company');
      await setupProfilePage.continueButton.click();

      await setupProfilePage.expectValidationError('firstName');
    });

    test('should require last name', async ({ registerPage, setupProfilePage }) => {
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      await setupProfilePage.firstNameInput.fill('Test');
      await setupProfilePage.companyNameInput.fill('Test Company');
      await setupProfilePage.continueButton.click();

      await setupProfilePage.expectValidationError('lastName');
    });

    test('should require company name', async ({ registerPage, setupProfilePage }) => {
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      await setupProfilePage.firstNameInput.fill('Test');
      await setupProfilePage.lastNameInput.fill('User');
      await setupProfilePage.continueButton.click();

      await setupProfilePage.expectValidationError('companyName');
    });

    test('should reject duplicate company name', async ({ registerPage, setupProfilePage }) => {
      const companyName = `Test Company ${Date.now()}`;

      // First user creates company
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');
      await setupProfilePage.completeProfile('First', 'User', companyName);

      // Logout
      await page.goto('/auth/logout');

      // Second user tries same company name
      const phone2 = `912${String(Date.now()).slice(-4)}456`;
      await registerPage.goto();
      await registerPage.register(phone2, 'SecurePass123!');
      await setupProfilePage.completeProfile('Second', 'User', companyName);

      await setupProfilePage.expectErrorMessage(/already.*exists|taken/i);
    });

    test('should redirect authenticated user without company to setup-profile', async ({ page }) => {
      // Direct navigation to dashboard should redirect
      await page.goto('/');

      // Should redirect to either setup-profile or setup-company
      await expect(page).toHaveURL(/\/(setup-profile|setup-company|auth\/)/);
    });
  });

  test.describe('3. Complete Onboarding Flow', () => {
    test('should complete full onboarding: register -> setup profile -> dashboard', async ({ registerPage, setupProfilePage, dashboardPage }) => {
      const companyName = `E2E Test Company ${Date.now()}`;

      // Step 1: Register
      await registerPage.goto();
      await expect(registerPage.registerButton).toBeVisible();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      // Verify redirect to profile setup
      await expect(page).toHaveURL(/\/auth\/setup-profile/);

      // Step 2: Complete Profile
      await setupProfilePage.completeProfile('Test', 'User', companyName);

      // Verify redirect to dashboard
      await expect(page).toHaveURL(/\/$/);
      await expect(dashboardPage.logoutButton).toBeVisible();

      // Verify dashboard content
      await expect(dashboardPage.companyName).toBeVisible();
    });

    test('should allow skipping profile setup', async ({ registerPage, setupProfilePage }) => {
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      await setupProfilePage.skipProfile();

      // Should be on dashboard but with incomplete profile banner
      await expect(page).toHaveURL(/\/$/);
    });
  });

  test.describe('4. Progressive Profiling Edge Cases', () => {
    test('should redirect to setup-profile if accessing protected route without company', async ({ page }) => {
      // Register but don't complete profile
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      // Try to access employees page
      await page.goto('/employees');

      // Should redirect back to setup-profile
      await expect(page).toHaveURL(/\/auth\/setup-profile/);
    });

    test('should allow access to setup-profile page without redirect loop', async ({ registerPage, setupProfilePage }) => {
      await registerPage.goto();
      await registerPage.register(uniquePhone, 'SecurePass123!');

      // Access setup-profile multiple times - should not cause redirect loop
      await setupProfilePage.goto();
      await expect(page).toHaveURL(/\/auth\/setup-profile/);

      await page.goto('/');
      await expect(page).toHaveURL(/\/auth\/setup-profile/);
    });
  });
});
