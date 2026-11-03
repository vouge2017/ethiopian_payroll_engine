const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright-core');

const baseUrl = process.env.PAYROLL_E2E_BASE_URL;
if (!baseUrl || !/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(baseUrl)) {
  throw new Error('Set PAYROLL_E2E_BASE_URL to a localhost-only synthetic app instance.');
}

const password = 'Synthetic1!';
const screenshotDir = process.env.PAYROLL_E2E_SCREENSHOT_DIR;
const existingPhone = process.env.PAYROLL_E2E_PHONE;
if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1365, height: 900 } });
    if (existingPhone) {
      await page.goto(`${baseUrl}/auth/login`);
      await page.locator('#login_id').fill(existingPhone);
      await page.locator('#password').fill(password);
      await Promise.all([
        page.waitForURL('**/'),
        page.locator('#loginForm button[type=submit]').click(),
      ]);
    } else {
      const phone = `9${Date.now().toString().slice(-8)}`;
      await page.goto(`${baseUrl}/auth/register`);
      await page.locator('#phone').fill(phone);
      await page.locator('#password').fill(password);
      await page.locator('#password2').fill(password);
      await Promise.all([
        page.waitForURL('**/auth/setup-profile'),
        page.locator('#registerForm button[type=submit]').click(),
      ]);

      await page.locator('#firstName').fill('Synthetic');
      await page.locator('#middleName').fill('Owner');
      await page.locator('#companyName').fill(`Synthetic Payroll ${Date.now()}`);
      await Promise.all([
        page.waitForURL('**/'),
        page.locator('#setupProfileForm button[type=submit]').click(),
      ]);
    }

    await page.goto(`${baseUrl}/quick-start`);
    const attack = '<img src=x onerror=window.__previewXss=1>';
    await page.locator('#paste-data').fill(`${attack}\t911111111\t8000`);
    await page.getByRole('button', { name: /Preview & Continue/ }).click();
    await page.waitForTimeout(300);
    assert.equal(await page.locator('#preview-body img').count(), 0);
    assert.notEqual(await page.evaluate('window.__previewXss'), true);
    assert((await page.locator('#preview-body').innerText()).includes(attack));
    if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/import-preview.png`, fullPage: true });

    if (!existingPhone) {
      await page.goto(`${baseUrl}/quick-start`);
      await page.locator('#paste-data').fill('Synthetic Employee\t911234567\t10000');
      await page.getByRole('button', { name: /Preview & Continue/ }).click();
      await page.locator('#import-btn').click();
      await page.waitForFunction(() => document.querySelector('#step-3').style.display === 'block');
      assert((await page.locator('#import-summary').innerText()).includes('1 employees imported'));
    }

    await page.goto(`${baseUrl}/payroll/spreadsheet`);
    assert((await page.locator('.monthly-employee').count()) >= 1);
    if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/monthly-preparation.png`, fullPage: true });
    await Promise.all([
      page.waitForURL('**/payroll/spreadsheet'),
      page.locator('#worksheet-save').click(),
    ]);
    await Promise.all([
      page.waitForURL(/\/payroll\/runs\/\d+\/review$/),
      page.locator('#worksheet-review-button').click(),
    ]);
    const review = await page.locator('body').innerText();
    assert(review.includes('Synthetic Employee'));
    assert(review.includes('10,000.00'));
    assert(review.includes('Missing bank account'), 'Incomplete payment details were not flagged.');
    assert.equal(await page.getByRole('link', { name: 'Continue to approval' }).count(), 0);
    if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/monthly-review-blocked.png`, fullPage: true });

    const runId = page.url().match(/\/payroll\/runs\/(\d+)\/review$/)?.[1];
    assert(runId, 'Payroll review URL did not contain a run ID.');
    const editHref = await page.locator('a').evaluateAll(links =>
      links.map(link => link.getAttribute('href')).find(href => /^\/employees\/\d+\/edit$/.test(href)),
    );
    assert(editHref, 'The review did not link to the employee missing payment details.');
    await page.goto(`${baseUrl}${editHref}`);
    await page.locator('#bank_account').fill('cbe:1000123456789');
    await page.locator('#tin').fill('1234567890');
    await Promise.all([
      page.waitForURL(/\/employees\/\d+$/),
      page.locator('form[data-employee-form] button[type=submit]').click(),
    ]);
    await page.goto(`${baseUrl}/payroll/runs/${runId}/review`);
    await page.getByText('How this review stays current').click();
    await page.getByRole('button', { name: /Refresh review from current payroll details/ }).click();
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      page.locator('#confirmModalOk').click(),
    ]);
    await page.waitForURL(new RegExp(`/payroll/runs/${runId}/review$`));
    const refreshedReview = await page.locator('body').innerText();
    assert(!refreshedReview.includes('Missing bank account'));
    assert(!refreshedReview.includes('Missing TIN'));
    assert.equal(await page.getByRole('link', { name: 'Continue to approval' }).count(), 1);
    if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/monthly-review.png`, fullPage: true });

    const continueToApproval = page.getByRole('link', { name: 'Continue to approval' });
    assert.equal(await continueToApproval.count(), 1, 'Owner approval action was not available.');
    await Promise.all([
      page.waitForURL(`**/payroll/${runId}/confirm`),
      continueToApproval.click(),
    ]);
    await page.locator('#password').fill(password);
    await page.locator('#confirm_check').check();
    await Promise.all([
      page.waitForURL(new RegExp(`/payroll/runs/${runId}$`)),
      page.locator('#approve-form button[type=submit]').click(),
    ]);
    assert((await page.locator('body').innerText()).toLowerCase().includes('approved'));
    if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/approved-payroll-synthetic.png`, fullPage: true });

    const payslipLink = page.getByRole('link', { name: /Download PDF|Generate PDF/ }).first();
    assert.equal(await payslipLink.count(), 1, 'Payslip PDF action was not available.');
    const [payslipDownload] = await Promise.all([page.waitForEvent('download'), payslipLink.click()]);
    assert(payslipDownload.suggestedFilename().toLowerCase().endsWith('.pdf'));

    const bankFile = await page.request.get(`${baseUrl}/reports/bank/${runId}?format=csv&bank=cbe`);
    assert.equal(bankFile.status(), 200);
    assert((await bankFile.text()).includes('7650.00'));

    console.log(JSON.stringify({
      companySetup: 'passed',
      employeeImport: existingPhone ? 'reused imported synthetic employee' : 'passed',
      importPreviewXss: 'passed; input rendered as text',
      payrollPreparation: 'passed',
      payrollReview: 'missing bank/TIN flagged, corrected, and refreshed',
      ownerApproval: 'passed',
      payslipPdf: 'generated/downloaded',
      bankInstructionExport: 'passed; not a payment confirmation',
      runId,
    }));
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
