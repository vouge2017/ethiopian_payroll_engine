// Synthetic local browser journey; never target a hosted service.
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const readline = require('node:readline');
const { chromium } = require('playwright-core');

const base = 'http://127.0.0.1:5099';
const evidence = process.env.PAYROLL_EVIDENCE_DIR;
if (!evidence || !process.env.TEST_DATABASE_URL?.startsWith('postgresql://synthetic@127.0.0.1:55434/ep_milestone_')) {
  throw new Error('Supply the explicitly named local disposable database and evidence directory.');
}
fs.mkdirSync(evidence, { recursive: true });
const server = spawn(process.env.PAYROLL_PYTHON, ['-u', 'qa/monthly_approval_fixture.py'], {
  env: process.env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true,
});
let stderr = '';
server.stderr.on('data', chunk => { stderr += chunk; });

async function fixture() {
  const lines = readline.createInterface({ input: server.stdout });
  for await (const line of lines) {
    if (line.startsWith('FIXTURE ')) return JSON.parse(line.slice(8));
  }
  throw new Error(`Synthetic fixture exited: ${stderr}`);
}

async function main() {
  const { run_id: runId, cookie } = await fixture();
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  try {
    const context = await browser.newContext({ viewport: { width: 1365, height: 900 } });
    await context.addCookies([{ name: 'session', value: cookie, url: base }]);
    const page = await context.newPage();
    const confirmation = `${base}/payroll/${runId}/confirm`;
    const status = async () => (await page.request.get(`${base}/__synthetic/status`)).json();
    const control = async fail => page.request.post(`${base}/__synthetic/control`, { data: { fail } });
    await page.goto(confirmation);
    await page.getByRole('heading', { name: 'Approve payroll' }).waitFor();
    assert.equal(await page.locator('#approve-form input[name=idempotency_key]').count(), 1);
    await page.screenshot({ path: `${evidence}/01-confirmation.png`, fullPage: true });

    await control(true);
    await page.locator('#password').fill('Synthetic1!');
    await page.locator('#confirm_check').check();
    await Promise.all([page.waitForURL(`**/payroll/runs/${runId}/review`), page.locator('#approve-form button[type=submit]').click()]);
    assert.deepEqual(await status(), { status: 'review', payslips: 0, keys: 0 });
    assert((await page.locator('body').innerText()).includes('Approval did not complete. No payroll was approved.'));
    await page.screenshot({ path: `${evidence}/02-failed-before-commit.png`, fullPage: true });

    await control(false);
    await page.goto(confirmation);
    await page.locator('#password').fill('Synthetic1!');
    await page.locator('#confirm_check').check();
    let intercepted = false;
    await page.route('**/payroll/approve', async route => {
      const response = await route.fetch({ maxRedirects: 0 });
      assert.equal(response.status(), 302);
      intercepted = true;
      await route.abort('failed');
    });
    await page.locator('#approve-form button[type=submit]').click().catch(() => {});
    await page.waitForFunction(() => document.readyState === 'complete');
    assert(intercepted, 'Approval response was not intercepted');
    assert.deepEqual(await status(), { status: 'completed', payslips: 1, keys: 1 });
    await page.unroute('**/payroll/approve');
    await page.goto(confirmation);
    await page.waitForURL(`**/payroll/runs/${runId}`);
    assert((await page.locator('body').innerText()).includes('This payroll was already approved'));
    assert((await page.locator('body').innerText()).includes('Payment pending'));
    assert.equal(await page.locator('#approve-form').count(), 0);
    await page.screenshot({ path: `${evidence}/03-recovered-approved.png`, fullPage: true });
    // A second attempt to reopen the approval screen returns the existing
    // results and offers no second approval action.
    await page.goto(confirmation);
    await page.waitForURL(`**/payroll/runs/${runId}`);
    assert.equal(await page.locator('#approve-form').count(), 0);
    assert.deepEqual(await status(), { status: 'completed', payslips: 1, keys: 1 });
    console.log(JSON.stringify({ precommitFailure: 'rolled back', interruptedResponse: 'recovered', duplicateEffect: 'none', runId }));
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => server.kill());
