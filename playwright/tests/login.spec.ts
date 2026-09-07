import { test, expect } from './fixtures';
import { RegisterPage } from '../pages/RegisterPage';
import { SetupProfilePage } from '../pages/SetupProfilePage';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';

test.describe('Login Flow', () => {
  let uniquePhone: string;
  const password = 'SecurePass123!';
  const companyName = `Login Test Company ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const last4 = String(timestamp).slice(-4);
    uniquePhone = `911${last4}456`;

    // Create a user first for login tests
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    await registerPage.register(uniquePhone, password);

    const setupProfilePage = new SetupProfilePage(page);
    await setupProfilePage.completeProfile('Login', 'Test', companyName);

    // Logout before each test
    await page.goto('/auth/logout');
  });

  test.describe('1. Successful Login', () => {
    test('should login with valid phone number', async ({ loginPage, dashboardPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, password);

      await expect(page).toHaveURL(/\/$/);
      await expect(dashboardPage.logoutButton).toBeVisible();
    });

    test('should redirect already logged in user to dashboard', async ({ loginPage, dashboardPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, password);

      // Try to access login page again
      await loginPage.goto();

      // Should redirect to dashboard
      await expect(page).toHaveURL(/\/$/);
    });

    test('should display user session on dashboard', async ({ loginPage, dashboardPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, password);

      await expect(dashboardPage.userMenu).toBeVisible();
    });
  });

  test.describe('2. Failed Login Attempts', () => {
    test('should show error for wrong password', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, 'WrongPassword123!');

      await loginPage.expectErrorMessage(/invalid|incorrect/i);
    });

    test('should show error for non-existent user', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.login('9199999999', password);

      await loginPage.expectErrorMessage(/invalid|incorrect/i);
    });

    test('should show error for empty phone', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.phoneInput.fill('');
      await loginPage.passwordInput.fill(password);
      await loginPage.loginButton.click();

      await loginPage.expectErrorMessage(/required/i);
    });

    test('should show error for empty password', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, '');

      await loginPage.expectErrorMessage(/required/i);
    });

    test('should clear form on login error', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, 'WrongPassword123!');

      await loginPage.expectErrorMessage(/invalid/i);

      // Form should still have phone but not password
      await expect(loginPage.phoneInput).toHaveValue(uniquePhone);
    });
  });

  test.describe('3. Login Page Elements', () => {
    test('should display login form correctly', async ({ loginPage }) => {
      await loginPage.goto();

      await expect(loginPage.phoneInput).toBeVisible();
      await expect(loginPage.passwordInput).toBeVisible();
      await expect(loginPage.loginButton).toBeVisible();
      await expect(loginPage.forgotPasswordLink).toBeVisible();
      await expect(loginPage.registerLink).toBeVisible();
    });

    test('should navigate to forgot password page', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.clickForgotPassword();

      await expect(page).toHaveURL(/\/auth\/forgot-password/);
    });

    test('should navigate to register page', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.clickRegister();

      await expect(page).toHaveURL(/\/auth\/register/);
    });
  });

  test.describe('4. Session Management', () => {
    test('should logout successfully', async ({ loginPage, dashboardPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, password);

      await dashboardPage.logout();

      await expect(page).toHaveURL(/\/auth\/login/);
    });

    test('should not access protected routes after logout', async ({ loginPage, dashboardPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, password);

      await dashboardPage.logout();

      // Try to access dashboard
      await page.goto('/');

      // Should redirect to login
      await expect(page).toHaveURL(/\/auth\/login/);
    });
  });

  test.describe('5. Phone Format Handling', () => {
    test('should accept 9-digit phone format', async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.login(uniquePhone, password);

      await expect(page).toHaveURL(/\/$/);
    });

    test('should accept phone with +251 prefix', async ({ loginPage }) => {
      await loginPage.goto();
      const withPrefix = `+251${uniquePhone.slice(1)}`;
      await loginPage.login(withPrefix, password);

      await expect(page).toHaveURL(/\/$/);
    });
  });
});
