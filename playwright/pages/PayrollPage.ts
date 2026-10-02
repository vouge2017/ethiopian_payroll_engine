import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class PayrollPage extends BasePage {
  readonly page: Page;
  readonly newPayrollButton: Locator;
  readonly payrollTable: Locator;
  readonly payrollRows: Locator;
  readonly periodSelector: Locator;
  readonly statusBadge: Locator;
  readonly totalGross: Locator;
  readonly totalNet: Locator;

  constructor(page: Page) {
    super(page);
    this.page = page;
    this.newPayrollButton = page.getByRole('button', { name: /new.*payroll|run.*payroll|process.*payroll/i });
    this.payrollTable = page.locator('table.payroll, .payroll-table, table[data-table="payroll"]');
    this.payrollRows = this.payrollTable.locator('tbody tr, .payroll-row');
    this.periodSelector = page.locator('select[name*="period"], [data-period-selector]').first();
    this.statusBadge = page.locator('.badge, .status-badge');
    this.totalGross = page.locator('[data-total-gross], .total-gross').first();
    this.totalNet = page.locator('[data-total-net], .total-net').first();
  }

  async goto() {
    await this.page.goto('/payroll');
    await this.waitForLoad();
  }

  async clickNewPayroll() {
    await this.newPayrollButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async selectPeriod(period: string) {
    await this.periodSelector.selectOption(period);
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectPayrollCount(count: number) {
    await expect(this.payrollRows).toHaveCount(count);
  }

  async expectPayrollStatus(status: 'draft' | 'pending' | 'approved' | 'completed' | 'paid') {
    const statusBadge = this.statusBadge.filter({ hasText: new RegExp(status, 'i') });
    await expect(statusBadge.first()).toBeVisible();
  }

  async clickPayrollRun(index: number = 0) {
    await this.payrollRows.nth(index).click();
    await this.page.waitForLoadState('domcontentloaded');
  }
}
