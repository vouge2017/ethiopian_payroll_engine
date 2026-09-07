import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class RegisterPage extends BasePage {
  readonly page: Page;
  readonly phoneInput: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly registerButton: Locator;
  readonly loginLink: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.page = page;
    this.phoneInput = page.getByLabel(/phone.*number/i).first();
    this.emailInput = page.getByLabel(/email/i).first();
    this.passwordInput = page.getByLabel(/^password$/i).first();
    this.confirmPasswordInput = page.getByLabel(/confirm.*password|password.*again/i).first();
    this.registerButton = page.getByRole('button', { name: /register|sign.*up|create.*account/i });
    this.loginLink = page.getByRole('link', { name: /already.*have.*account|log.*in/i });
    this.errorMessage = page.locator('.alert-danger, .error-message, [role="alert"], .invalid-feedback');
  }

  async goto() {
    await this.page.goto('/auth/register');
    await this.waitForLoad();
  }

  async register(phone: string, password: string, email?: string) {
    await this.phoneInput.fill(phone);

    if (email !== undefined) {
      await this.emailInput.fill(email);
    }

    await this.passwordInput.fill(password);
    await this.confirmPasswordInput.fill(password);
    await this.registerButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectErrorMessage(contains?: string) {
    await expect(this.errorMessage.first()).toBeVisible();
    if (contains) {
      await expect(this.errorMessage.first()).toContainText(contains);
    }
  }

  async expectPhoneValidationError() {
    await this.expectErrorMessage(/9.*digit|leading.*0|format/i);
  }

  async expectPasswordValidationError() {
    await this.expectErrorMessage(/password|symbol|uppercase|lowercase|number/i);
  }

  async clickLogin() {
    await this.loginLink.click();
    await this.page.waitForLoadState('domcontentloaded');
  }
}
