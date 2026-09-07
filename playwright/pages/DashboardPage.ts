import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class DashboardPage extends BasePage {
  readonly page: Page;
  readonly sidebar: Locator;
  readonly employeeNav: Locator;
  readonly payrollNav: Locator;
  readonly reportsNav: Locator;
  readonly settingsNav: Locator;
  readonly logoutButton: Locator;
  readonly userMenu: Locator;
  readonly companyName: Locator;
  readonly employeeCount: Locator;
  readonly pendingPayrollBadge: Locator;
  readonly quickActions: Locator;

  constructor(page: Page) {
    super(page);
    this.page = page;
    this.sidebar = page.locator('aside.sidebar, nav.sidebar, .sidebar-nav');
    this.employeeNav = page.getByRole('link', { name: /employee/i });
    this.payrollNav = page.getByRole('link', { name: /payroll/i });
    this.reportsNav = page.getByRole('link', { name: /report/i });
    this.settingsNav = page.getByRole('link', { name: /setting/i });
    this.logoutButton = page.getByRole('button', { name: /log.*out|sign.*out/i });
    this.userMenu = page.locator('.user-menu, [data-user-menu], .dropdown-toggle');
    this.companyName = page.locator('.company-name, [data-company-name]').first();
    this.employeeCount = page.locator('[data-employee-count], .employee-count').first();
    this.pendingPayrollBadge = page.locator('.badge-warning, .pending-badge, [data-pending-count]').first();
    this.quickActions = page.locator('.quick-actions, .action-buttons, .dashboard-actions');
  }

  async goto() {
    await this.page.goto('/');
    await this.waitForLoad();
  }

  async navigateToEmployees() {
    await this.employeeNav.first().click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async navigateToPayroll() {
    await this.payrollNav.first().click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async navigateToReports() {
    await this.reportsNav.first().click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async navigateToSettings() {
    await this.settingsNav.first().click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async logout() {
    await this.logoutButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectToBeLoggedIn() {
    await expect(this.page).toHaveURL(/\/(?!auth\/)/);
    await expect(this.logoutButton).toBeVisible();
  }

  async expectCompanyName(contains?: string) {
    await expect(this.companyName).toBeVisible();
    if (contains) {
      await expect(this.companyName).toContainText(contains);
    }
  }

  async expectEmployeeCount(count?: number) {
    await expect(this.employeeCount).toBeVisible();
    if (count !== undefined) {
      await expect(this.employeeCount).toContainText(String(count));
    }
  }

  async expectQuickActions() {
    await expect(this.quickActions).toBeVisible();
  }

  async openUserMenu() {
    await this.userMenu.click();
    await this.page.waitForLoadState('domcontentloaded');
  }
}
