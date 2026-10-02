import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class EmployeesPage extends BasePage {
  readonly page: Page;
  readonly addEmployeeButton: Locator;
  readonly employeeTable: Locator;
  readonly employeeRows: Locator;
  readonly searchInput: Locator;
  readonly importButton: Locator;
  readonly noEmployeesMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.page = page;
    this.addEmployeeButton = page.getByRole('button', { name: /add.*employee|new.*employee/i });
    this.employeeTable = page.locator('table.employees, .employee-table, table[data-table="employees"]');
    this.employeeRows = this.employeeTable.locator('tbody tr, .employee-row');
    this.searchInput = page.getByPlaceholder(/search.*employee|find.*employee/i);
    this.importButton = page.getByRole('button', { name: /import.*employee/i });
    this.noEmployeesMessage = page.locator('.empty-state, .no-employees, [data-empty="employees"]');
  }

  async goto() {
    await this.page.goto('/employees');
    await this.waitForLoad();
  }

  async clickAddEmployee() {
    await this.addEmployeeButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async importEmployees() {
    await this.importButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectEmployeeCount(count: number) {
    await expect(this.employeeRows).toHaveCount(count);
  }

  async expectEmployeeVisible(name: string) {
    await expect(this.page.locator(`text=${name}`).first()).toBeVisible();
  }

  async searchForEmployee(name: string) {
    await this.searchInput.fill(name);
    await this.page.waitForLoadState('domcontentloaded');
  }

  async clickEmployee(name: string) {
    await this.page.locator(`text=${name}`).first().click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectEmptyState() {
    await expect(this.noEmployeesMessage).toBeVisible();
  }
}
