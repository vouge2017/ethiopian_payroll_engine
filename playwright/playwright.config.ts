import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: 'list',

  use: {
    baseURL: process.env.BASE_URL || 'https://ethiopian-payroll-engine.onrender.com',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
    navigationTimeout: 30000,
    actionTimeout: 10000,
  },

  projects: [
    // Default: Chromium only for fast local testing (~5 min)
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Full CI matrix (run with: CI=true npx playwright test) (~30 min)
    ...(process.env.CI ? [
      { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
      { name: 'webkit', use: { ...devices['Desktop Safari'] } },
      { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
      { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } },
    ] : []),
  ],

  // No local webServer - tests run against BASE_URL
  // For local testing with Flask: flask run --debug
  webServer: undefined,
});
