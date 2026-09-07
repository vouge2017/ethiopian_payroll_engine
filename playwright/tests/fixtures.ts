import { test as base, Page, BrowserContext } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { SetupProfilePage } from '../pages/SetupProfilePage';
import { DashboardPage } from '../pages/DashboardPage';
import { EmployeesPage } from '../pages/EmployeesPage';
import { PayrollPage } from '../pages/PayrollPage';

type Fixtures = {
  loginPage: LoginPage;
  registerPage: RegisterPage;
  setupProfilePage: SetupProfilePage;
  dashboardPage: DashboardPage;
  employeesPage: EmployeesPage;
  payrollPage: PayrollPage;
  uniquePhone: () => string;
};

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  registerPage: async ({ page }, use) => {
    const registerPage = new RegisterPage(page);
    await use(registerPage);
  },

  setupProfilePage: async ({ page }, use) => {
    const setupProfilePage = new SetupProfilePage(page);
    await use(setupProfilePage);
  },

  dashboardPage: async ({ page }, use) => {
    const dashboardPage = new DashboardPage(page);
    await use(dashboardPage);
  },

  employeesPage: async ({ page }, use) => {
    const employeesPage = new EmployeesPage(page);
    await use(employeesPage);
  },

  payrollPage: async ({ page }, use) => {
    const payrollPage = new PayrollPage(page);
    await use(payrollPage);
  },

  uniquePhone: async () => {
    const timestamp = Date.now();
    const last3 = String(timestamp).slice(-3);
    return `911${last3}456`;
  },
});

export { expect } from '@playwright/test';
