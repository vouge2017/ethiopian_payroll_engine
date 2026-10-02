import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class SetupProfilePage extends BasePage {
  readonly page: Page;
  readonly firstNameInput: Locator;
  readonly middleNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly companyNameInput: Locator;
  readonly continueButton: Locator;
  readonly skipButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.page = page;
    this.firstNameInput = page.getByLabel(/first.*name/i).first();
    this.middleNameInput = page.getByLabel(/middle.*name/i).first();
    this.lastNameInput = page.getByLabel(/last.*name/i).first();
    this.companyNameInput = page.getByLabel(/company.*name|organization.*name/i).first();
    this.continueButton = page.getByRole('button', { name: /continue|next|save|submit/i });
    this.skipButton = page.getByRole('button', { name: /skip/i });
    this.errorMessage = page.locator('.alert-danger, .error-message, [role="alert"], .invalid-feedback');
  }

  async goto() {
    await this.page.goto('/auth/setup-profile');
    await this.waitForLoad();
  }

  async completeProfile(firstName: string, lastName: string, companyName: string, middleName?: string) {
    await this.firstNameInput.fill(firstName);

    if (middleName !== undefined) {
      await this.middleNameInput.fill(middleName);
    }

    await this.lastNameInput.fill(lastName);
    await this.companyNameInput.fill(companyName);
    await this.continueButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async skipProfile() {
    await this.skipButton.click();
    await this.page.waitForLoadState('domcontentloaded');
  }

  async expectErrorMessage(contains?: string) {
    await expect(this.errorMessage.first()).toBeVisible();
    if (contains) {
      await expect(this.errorMessage.first()).toContainText(contains);
    }
  }

  async expectValidationError(field: 'firstName' | 'lastName' | 'companyName') {
    const fieldMap = {
      firstName: this.firstNameInput,
      lastName: this.lastNameInput,
      companyName: this.companyNameInput,
    };
    const input = fieldMap[field];
    await expect(input).toHaveClass(/is-invalid/);
  }
}
