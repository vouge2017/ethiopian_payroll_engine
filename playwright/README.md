# Ethiopian Payroll Engine - Playwright E2E Tests

Comprehensive end-to-end test suite for the Ethiopian Payroll Engine application.

## Overview

This test suite covers the critical user flows:
- **Onboarding Flow**: Registration, profile setup, progressive profiling
- **Login Flow**: Authentication, session management, error handling
- **Dashboard Navigation**: Sidebar navigation, quick actions, role-based access
- **Payroll Workflow**: Employee management, payroll processing, reports

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Browser binaries installed (Chromium, Firefox, WebKit)

## Installation

```bash
# Navigate to playwright directory
cd playwright

# Install dependencies
npm install

# Install browser binaries
npx playwright install
```

## Running Tests

### Run all tests
```bash
npm test
```

### Run with UI (headed mode)
```bash
npm run test:headed
```

### Run with interactive UI
```bash
npm run test:ui
```

### Debug mode
```bash
npm run test:debug
```

### Run specific test file
```bash
npx playwright test tests/onboarding.spec.ts
```

### Run tests matching pattern
```bash
npx playwright test --grep "login"
npx playwright test --grep "@smoke"
```

## Test Structure

```
playwright/
├── package.json
├── playwright.config.ts
├── pages/
│   ├── BasePage.ts          # Base page object
│   ├── LoginPage.ts         # Login page object
│   ├── RegisterPage.ts      # Registration page object
│   ├── SetupProfilePage.ts  # Profile setup page object
│   ├── DashboardPage.ts     # Dashboard page object
│   ├── EmployeesPage.ts     # Employees page object
│   └── PayrollPage.ts       # Payroll page object
├── tests/
│   ├── fixtures.ts          # Test fixtures and helpers
│   ├── onboarding.spec.ts   # Onboarding flow tests
│   ├── login.spec.ts        # Login flow tests
│   ├── dashboard.spec.ts    # Dashboard navigation tests
│   └── payroll-workflow.spec.ts # Payroll workflow tests
└── README.md
```

## Configuration

The test suite uses environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `https://ethiopian-payroll-engine.onrender.com` | Application base URL |
| `CI` | `false` | Run in CI mode (retries, single worker) |

### Example: Run against local development server
```bash
BASE_URL=http://localhost:5000 npm test
```

## Test Tags

Tests are organized with descriptive names:

- `@onboarding` - Registration and profile setup
- `@login` - Authentication flows
- `@dashboard` - Dashboard navigation
- `@payroll` - Payroll processing
- `@smoke` - Quick smoke tests

## Page Object Model

Tests use the Page Object Model pattern for maintainability:

```typescript
// Example: Using page objects
test('should login successfully', async ({ loginPage, dashboardPage }) => {
  await loginPage.goto();
  await loginPage.login('911234567', 'SecurePass123!');
  await expect(dashboardPage.logoutButton).toBeVisible();
});
```

## Assertions

Common assertions used:

```typescript
// Visibility
await expect(element).toBeVisible();
await expect(element).toBeHidden();

// Text content
await expect(element).toHaveText('Expected');
await expect(element).toContainText('Expected');

// URL
await expect(page).toHaveURL(/\/dashboard/);

// Form fields
await expect(input).toHaveValue('text');
await expect(input).toBeDisabled();
```

## Troubleshooting

### Browser not installed
```bash
npx playwright install
```

### Connection refused
Ensure the application is running:
```bash
# For local testing, start the app
flask run --debug
```

### Tests timeout
Increase timeout in `playwright.config.ts`:
```typescript
timeout: 60000, // 60 seconds
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Playwright Tests
  run: npm test
  env:
    CI: true
    BASE_URL: ${{ vars.DEPLOYMENT_URL }}
```

## Viewing Reports

After test run, open the HTML report:
```bash
npm run report
```

Reports are saved to `playwright-report/` directory.

## Writing New Tests

1. Add page object methods in `pages/`
2. Create test file in `tests/`
3. Use fixtures from `fixtures.ts`
4. Follow naming convention: `*.spec.ts`

## Coverage Goals

These tests aim to cover:
- Happy path flows
- Error handling
- Edge cases
- Role-based access control
- Responsive design

## Maintenance

- Update selectors when UI changes
- Keep page objects in sync with application
- Add new test cases for bug fixes
- Run full suite before releases
