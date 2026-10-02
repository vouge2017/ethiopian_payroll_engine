import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  readonly page: Page;
  readonly phoneInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly forgotPasswordLink: Locator;
  readonly registerLink: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.page = page;
    this.phoneInput = page.getByLabel(/phone|login.*id/i).first();
    this.passwordInput = page.getByLabel(/password/i).first();
    this.loginButton = page.getByRole('button', { name: /log.*in|sign.*in/i });
    this.forgotPasswordLink = page.getByRole('link', { name: /forgot.*password/i });
    this.registerLink = page.getByRole('link', { name: /register|sign.*up|create.*account/i });
    this.errorMessage = page.locator('.alert-danger, .error-message, [role="alert"]');
  }

  async goto() {
    await this.page.goto('/auth/login');
    await this.waitForLoad();
  }

  async login(phoneOrEmail: string, password: string) {
    await this.phoneInput.fill(phoneOrEmail);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectErrorMessage(contains?: string) {
    await expect(this.errorMessage).toBeVisible();
    if (contains) {
      await expect(this.errorMessage).toContainText(contains);
    }
  }

  async expectToBeRedirectedToRegister() {
    await expect(this.page).toHaveURL(/\/auth\/register/);
  }

  async clickForgotPassword() {
    await this.forgotPasswordLink.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async clickRegister() {
    await this.registerLink.click();
    await this.page.waitForLoadState('domcontentloaded');
  }
}
