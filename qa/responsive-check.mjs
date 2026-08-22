/**
 * Responsive design audit (mobile screens, tablet, web/desktop screens).
 *
 * Evaluates: layout integrity across device viewports + horizontal-overflow detection.
 * Usage:
 *   node responsive-check.mjs                 # public pages
 *   node responsive-check.mjs --authed        # include authenticated pages (demo mode / credentials)
 *   node responsive-check.mjs --pages /a,/b   # custom page list
 *
 * Reports: qa/reports/<stamp>-responsive/  (JSON summary + full-page screenshots)
 */
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  BASE_URL,
  ensureAuthenticated,
  goto,
  launchBrowser,
  newPage,
  newReportDir,
  warmup,
} from './lib/audit-common.mjs';

const VIEWPORTS = [
  { name: 'mobile-sm-360', width: 360, height: 740 }, // small Android
  { name: 'mobile-375', width: 375, height: 667 },    // iPhone SE
  { name: 'mobile-lg-414', width: 414, height: 896 }, // iPhone Plus
  { name: 'tablet-768', width: 768, height: 1024 },   // iPad portrait
  { name: 'desktop-1440', width: 1440, height: 900 }, // laptop / web
];

const PUBLIC_PAGES = ['/auth/login', '/auth/register'];
const AUTHED_PAGES = ['/', '/employees'];

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { authed: false, pages: null };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--authed') out.authed = true;
    if (args[i] === '--pages') out.pages = args[++i].split(',').map((p) => p.trim());
  }
  return out;
}

async function checkViewport(page, path, vp) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await goto(page, path);
  await page.waitForTimeout(1_200); // let responsive CSS settle

  const metrics = await page.evaluate(() => {
    const de = document.documentElement;
    const body = document.body;
    return {
      scrollWidth: Math.max(de.scrollWidth, body ? body.scrollWidth : 0),
      clientWidth: de.clientWidth,
      innerWidth: window.innerWidth,
      title: document.title,
      textLength: body ? body.innerText.trim().length : 0,
    };
  });

  const overflowPx = metrics.scrollWidth - metrics.clientWidth;
  const hasOverflow = overflowPx > 2; // 2px tolerance
  const screenshot = `${path.replace(/\//g, '_') || '_root'}-${vp.name}.png`;
  await page.screenshot({ path: join(reportDir, screenshot), fullPage: true });

  return {
    page: path,
    viewport: vp.name,
    width: vp.width,
    scrollWidth: metrics.scrollWidth,
    clientWidth: metrics.clientWidth,
    overflowPx,
    horizontalOverflow: hasOverflow,
    renderedTextChars: metrics.textLength,
    blankPage: metrics.textLength < 20,
    screenshot,
  };
}

let reportDir;

async function main() {
  const opts = parseArgs();
  let pages = opts.pages ?? [...PUBLIC_PAGES];
  if (opts.authed && !opts.pages) pages = [...PUBLIC_PAGES, ...AUTHED_PAGES];

  await warmup('responsive target');
  reportDir = newReportDir('responsive');
  const browser = await launchBrowser();
  const results = [];

  try {
    const { context, page } = await newPage(browser);
    if (opts.authed || (!opts.pages && AUTHED_PAGES.some((p) => pages.includes(p)))) {
      const ok = await ensureAuthenticated(page);
      process.stdout.write(`Authentication via demo/credentials: ${ok ? 'OK' : 'FAILED (auditing public pages only)'}
`);
      if (!ok) pages = pages.filter((p) => !AUTHED_PAGES.includes(p));
    }

    for (const path of pages) {
      for (const vp of VIEWPORTS) {
        process.stdout.write(`Checking ${path} @ ${vp.name} (${vp.width}px) ...
`);
        try {
          results.push(await checkViewport(page, path, vp));
        } catch (err) {
          results.push({
            page: path,
            viewport: vp.name,
            error: err.message.slice(0, 120),
            horizontalOverflow: null,
          });
        }
      }
    }
    await context.close();
  } finally {
    await browser.close();
  }

  process.stdout.write(`
=== RESPONSIVE SUMMARY (mobile / tablet / web screens) ===
`);
  process.stdout.write(`page | viewport | overflow(px) | verdict
`);
  for (const r of results) {
    const verdict =
      r.error ? `ERROR` : r.blankPage ? 'BLANK?' : r.horizontalOverflow ? 'OVERFLOW' : 'OK';
    process.stdout.write(`${r.page} | ${r.viewport} | ${r.overflowPx ?? '-'} | ${verdict}
`);
  }

  const failures = results.filter((r) => r.horizontalOverflow || r.blankPage || r.error);
  const summary = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    viewports: VIEWPORTS,
    threshold: 'no horizontal overflow at any viewport; page renders content',
    pass: failures.length === 0,
    results,
  };
  writeFileSync(join(reportDir, 'summary.json'), JSON.stringify(summary, null, 2));
  process.stdout.write(`
${failures.length ? `FAILURES: ${failures.length}` : 'ALL VIEWPORTS OK'}
Full reports + screenshots saved to: ${reportDir}
`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});