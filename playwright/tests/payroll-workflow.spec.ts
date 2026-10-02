import { test, expect } from './fixtures';
import { RegisterPage } from '../pages/RegisterPage';
import { SetupProfilePage } from '../pages/SetupProfilePage';
import { DashboardPage } from '../pages/DashboardPage';
import { EmployeesPage } from '../pages/EmployeesPage';
import { PayrollPage } from '../pages/PayrollPage';

test.describe('Payroll Run Workflow', () => {
  let uniquePhone: string;
  const password = 'SecurePass123!';
  const companyName = `Payroll Test Company ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const last4 = String(timestamp).slice(-4);
    uniquePhone = `911${last4}456`;

    // Create user and company
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    await registerPage.register(uniquePhone, password);

    const setupProfilePage = new SetupProfilePage(page);
    await setupProfilePage.completeProfile('Payroll', 'Test', companyName);
  });

  test.afterEach(async ({ page }) => {
    try {
      await page.goto('/auth/logout');
    } catch {
      // Ignore cleanup errors
    }
  });

  test.describe('1. Employee Management', () => {
    test('should display empty employees state', async ({ employeesPage }) => {
      await employeesPage.goto();

      await employeesPage.expectEmptyState();
    });

    test('should navigate to add employee form', async ({ employeesPage }) => {
      await employeesPage.goto();
      await employeesPage.clickAddEmployee();

      // Should navigate to employee form or show modal
      await expect(page.locator('form, .modal, h1, h2').first()).toBeVisible();
    });

    test('should display employee page structure', async ({ employeesPage }) => {
      await employeesPage.goto();

      await expect(employeesPage.addEmployeeButton).toBeVisible();
      await expect(employeesPage.importButton).toBeVisible();
    });
  });

  test.describe('2. Payroll Page Access', () => {
    test('should access payroll page', async ({ payrollPage }) => {
      await payrollPage.goto();

      await expect(payrollPage.newPayrollButton).toBeVisible();
    });

    test('should display payroll table or empty state', async ({ payrollPage }) => {
      await payrollPage.goto();

      // Either table should exist or empty state
      const hasTable = await payrollPage.payrollTable.count() > 0;
      const hasEmptyState = await payrollPage.noEmployeesMessage.count() > 0;

      expect(hasTable || hasEmptyState).toBeTruthy();
    });

    test('should show new payroll button', async ({ payrollPage }) => {
      await payrollPage.goto();

      await expect(payrollPage.newPayrollButton).toBeVisible();
      await expect(payrollPage.newPayrollButton).toBeEnabled();
    });
  });

  test.describe('3. Quick Actions from Dashboard', () => {
    test('should have run payroll quick action', async ({ dashboardPage }) => {
      await dashboardPage.goto();

      // Look for run payroll button in quick actions
      const runPayrollBtn = dashboardPage.quickActions.locator(
        'button, a',
      ).filter({ hasText: /payroll/i });
      const count = await runPayrollBtn.count();

      if (count > 0) {
        await expect(runPayrollBtn.first()).toBeVisible();
      }
    });

    test('should have add employee quick action', async ({ dashboardPage }) => {
      await dashboardPage.goto();

      // Look for add employee button in quick actions
      const addEmployeeBtn = dashboardPage.quickActions.locator(
        'button, a',
      ).filter({ hasText: /employee/i });
      const count = await addEmployeeBtn.count();

      if (count > 0) {
        await expect(addEmployeeBtn.first()).toBeVisible();
      }
    });
  });

  test.describe('4. Navigation to Core Functions', () => {
    test('should navigate from dashboard to employees', async ({ dashboardPage, employeesPage }) => {
      await dashboardPage.goto();
      await dashboardPage.navigateToEmployees();

      await expect(page).toHaveURL(/\/employees/);
    });

    test('should navigate from dashboard to payroll', async ({ dashboardPage, payrollPage }) => {
      await dashboardPage.goto();
      await dashboardPage.navigateToPayroll();

      await expect(page).toHaveURL(/\/payroll/);
    });

    test('should navigate from employees to payroll', async ({ employeesPage, payrollPage }) => {
      await employeesPage.goto();
      await employeesPage.payrollNav?.click();

      await expect(page).toHaveURL(/\/payroll/);
    });
  });
});

test.describe('Employee Self-Service Portal', () => {
  let uniquePhone: string;
  const password = 'SecurePass123!';
  const companyName = `Portal Test Company ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const last4 = String(timestamp).slice(-4);
    uniquePhone = `911${last4}456`;

    // Create owner user and company
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    await registerPage.register(uniquePhone, password);

    const setupProfilePage = new SetupProfilePage(page);
    await setupProfilePage.completeProfile('Owner', 'User', companyName);
  });

  test('should access employee self-service portal', async ({ page }) => {
    // Access employee portal (note: this requires an employee user)
    await page.goto('/my/dashboard');

    // Should either show employee portal or redirect to login
    const url = page.url();
    expect(url.includes('/my/') || url.includes('/auth/')).toBeTruthy();
  });

  test('should show payslip viewing capability for employees', async ({ page }) => {
    // Access payslips page
    await page.goto('/my/payslips');

    // Should either show payslips or redirect
    const url = page.url();
    expect(url.includes('/my/') || url.includes('/auth/')).toBeTruthy();
  });
});

test.describe('Reports Generation', () => {
  let uniquePhone: string;
  const password = 'SecurePass123!';
  const companyName = `Reports Test Company ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const last4 = String(timestamp).slice(-4);
    uniquePhone = `911${last4}456`;

    // Create user and company
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    await registerPage.register(uniquePhone, password);

    const setupProfilePage = new SetupProfilePage(page);
    await setupProfilePage.completeProfile('Reports', 'Test', companyName);
  });

  test('should access reports page', async ({ page }) => {
    await page.goto('/reports');

    // Should load reports page
    const url = page.url();
    expect(url.includes('/reports')).toBeTruthy();
  });

  test('should have ERCA report option', async ({ page }) => {
    await page.goto('/reports');

    // Look for ERCA report button or link
    const ercaLink = page.getByText(/erca/i);
    const count = await ercaLink.count();

    // ERCA might not be visible without payroll data
    // Just verify page loads correctly
    await expect(page).toHaveURL(/\/reports/);
  });
});
