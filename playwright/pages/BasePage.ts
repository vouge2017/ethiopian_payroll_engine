import { Page, Locator, expect } from '@playwright/test';

export class BasePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly flashMessages: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1, h2').first();
    this.flashMessages = page.locator('.flash-messages .alert, .alert-success, .alert-danger, .alert-warning');
    this.loadingSpinner = page.locator('.spinner, .loading, [data-loading]');
  }

  async goto(path: string) {
    await this.page.goto(path);
    await this.waitForLoad();
  }

  async waitForLoad() {
    await this.page.waitForLoadState('domcontentloaded');
    await this.waitForSpinner();
  }

  async waitForSpinner() {
    try {
      await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 5000 });
    } catch {
      // No spinner present, continue
    }
  }

  async getFlashMessage(type?: 'success' | 'danger' | 'warning' | 'info'): Promise<string | null> {
    const selector = type ? `.alert-${type}` : '.alert';
    const messages = this.page.locator(`.flash-messages ${selector}, ${selector}.flash-messages`);
    const count = await messages.count();
    if (count === 0) return null;
    return messages.first().textContent();
  }

  async expectFlashMessage(type: 'success' | 'danger' | 'warning' | 'info', contains?: string) {
    const selector = `.alert-${type}`;
    const message = this.page.locator(`.flash-messages ${selector}`);
    await expect(message).toBeVisible();
    if (contains) {
      await expect(message).toContainText(contains);
    }
  }

  async isOnPage(path: string): Promise<boolean> {
    const url = this.page.url();
    return url.includes(path);
  }
}
