/**
 * Lighthouse audit — performance, accessibility, best practices, SEO.
 *
 * Evaluates: page speed on throttled mobile network (the "network" skill area),
 * plus accessibility / best-practices / SEO category scores.
 *
 * Usage:
 *   node lighthouse-audit.mjs                     # audits BASE_URL + /auth/login
 *   node lighthouse-audit.mjs --pages /,/register
 *
 * Reports: qa/reports/<stamp>-lighthouse/  (.html + .json per page per form factor)
 */
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import lighthouse from 'lighthouse';
import { launch as launchChrome } from 'chrome-launcher';
import { BASE_URL, newReportDir, warmup } from './lib/audit-common.mjs';

const TARGETS = {
  performance: 80, // Render free-tier cold starts make this flaky; judge warm runs
  accessibility: 90,
  'best-practices': 90,
  seo: 90,
};

const DESKTOP_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

const CHROME_FLAGS = [
  '--headless=new',
  '--no-sandbox',
  '--disable-gpu',
  '--disable-dev-shm-usage',
];

function parseArgs() {
  const args = process.argv.slice(2);
  let pages = ['/', '/auth/login'];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--pages') pages = args[++i].split(',').map((p) => p.trim());
  }
  return pages;
}

/** One Lighthouse run. Retries internally once on transient failures. */
async function runLhWithRetry(url, formFactor, attempts = 2) {
  let lastErr;
  for (let i = 1; i <= attempts; i++) {
    const chrome = await launchChrome({ chromeFlags: CHROME_FLAGS });
    try {
      // maxWaitForLoad raised so render-blocking CDNs on slow networks
      // don't abort the audit before the page settles.
      const baseSettings = { maxWaitForLoad: 120_000 };
      const config =
        formFactor === 'desktop'
          ? {
              extends: 'lighthouse:default',
              settings: {
                ...baseSettings,
                formFactor: 'desktop',
                screenEmulation: {
                  mobile: false,
                  width: 1350,
                  height: 940,
                  deviceScaleFactor: 1,
                  disabled: false,
                },
                emulatedUserAgent: DESKTOP_UA,
              },
            }
          : {
              extends: 'lighthouse:default',
              settings: baseSettings, // default = mobile emulation + throttled network
            };

      return await lighthouse(
        url,
        { port: chrome.port, output: ['html', 'json'], logLevel: 'error' },
        config
      );
    } catch (err) {
      lastErr = err;
      process.stdout.write(
        `  attempt ${i}/${attempts} failed: ${err.message.slice(0, 100)}
`
      );
      await new Promise((r) => setTimeout(r, 5_000));
    } finally {
      // Cleanup must never discard a successful run: Chrome temp-profile
      // deletion can fail on Windows (EBUSY / antivirus locks).
      try {
        await chrome.kill();
      } catch {
        /* ignore cleanup errors */
      }
    }
  }
  throw lastErr;
}

async function main() {
  const pages = parseArgs();
  await warmup('lighthouse target'); // wake Render before measuring
  const reportDir = newReportDir('lighthouse');
  const rows = [];

  for (const path of pages) {
    const url = `${BASE_URL}${path}`;
    for (const formFactor of ['mobile', 'desktop']) {
      process.stdout.write(`Running Lighthouse (${formFactor}) on ${url} ...
`);
      try {
        const result = await runLhWithRetry(url, formFactor);
        const lhr = result.lhr;
        const scores = {};
        for (const [cat, target] of Object.entries(TARGETS)) {
          const c = lhr.categories[cat];
          scores[cat] = c ? Math.round((c.score ?? 0) * 100) : null;
          scores[`${cat}_target`] = target;
        }
        const metrics = lhr.audits['metrics']?.details?.items?.[0] || {};
        rows.push({
          page: path,
          formFactor,
          scores,
          keyMetrics: {
            fcp: metrics.firstContentfulPaint,
            lcp: metrics.largestContentfulPaint,
            tbt: metrics.totalBlockingTime,
            cls: metrics.cumulativeLayoutShift,
            tti: metrics.interactive,
            speedIndex: metrics.speedIndex,
          },
        });
        const safe = `${path.replace(/\//g, '_') || '_root'}-${formFactor}`;
        writeFileSync(join(reportDir, `${safe}.html`), result.report[0]);
        writeFileSync(join(reportDir, `${safe}.json`), result.report[1]);
      } catch (err) {
        rows.push({ page: path, formFactor, error: err.message.slice(0, 160) });
      }
    }
  }

  process.stdout.write(`
=== LIGHTHOUSE SUMMARY (scores /100, target in brackets) ===
`);
  process.stdout.write(`page | form | perf | a11y | best-practices | seo
`);
  for (const r of rows) {
    if (r.error) {
      process.stdout.write(`${r.page} | ${r.formFactor} | ERROR: ${r.error}
`);
      continue;
    }
    const s = r.scores;
    process.stdout.write(
      `${r.page} | ${r.formFactor} | ${s.performance} [${s.performance_target}] | ${s.accessibility} [${s.accessibility_target}] | ${s['best-practices']} [${s['best-practices_target']}] | ${s.seo} [${s.seo_target}]
`
    );
  }

  writeFileSync(
    join(reportDir, 'summary.json'),
    JSON.stringify(
      { generatedAt: new Date().toISOString(), baseUrl: BASE_URL, targets: TARGETS, results: rows },
      null,
      2
    )
  );
  process.stdout.write(`
Full HTML reports (open in a browser) saved to: ${reportDir}
Note: first run after a cold start measures Render spin-up; re-run for warm numbers.
`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});