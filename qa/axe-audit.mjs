/**
 * Accessibility audit (axe-core + Playwright).
 *
 * Evaluates: WCAG 2.1 A/AA accessibility of key pages.
 * Usage:
 *   node axe-audit.mjs                 # public pages (/login, /register)
 *   node axe-audit.mjs --authed        # also audits authenticated pages via demo mode or AUDIT_EMAIL/PASSWORD
 *   node axe-audit.mjs --pages /a,/b   # custom page list
 *
 * Reports: qa/reports/<stamp>-a11y/
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  BASE_URL,
  ensureAuthenticated,
  goto,
  launchBrowser,
  newPage,
  newReportDir,
  warmup,
} from './lib/audit-common.mjs';

const AXE_PATH = fileURLToPath(
  new URL('./node_modules/axe-core/axe.min.js', import.meta.url)
);

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

async function auditPage(page, path) {
  await goto(page, path);
  // Give client-side rendering / fonts a moment to settle.
  await page.waitForTimeout(1_500);
  // CSP-safe injection: evaluate axe-core source directly via CDP (not subject to page CSP)
  const axeSource = readFileSync(AXE_PATH, 'utf8');
  await page.evaluate(axeSource);
  const results = await page.evaluate(async () => {
    const axe = window.axe;
    return await axe.run(document, {
      resultTypes: ['violations'],
      rules: {
        region: { enabled: false }, // noisy on dashboards; tracked separately
      },
    });
  });
  return {
    url: `${BASE_URL}${path}`,
    finalUrl: page.url(),
    title: await page.title(),
    violations: results.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      helpUrl: v.helpUrl,
      tags: v.tags.filter((t) => t.startsWith('wcag')),
      nodes: v.nodes.length,
      sampleTargets: v.nodes.slice(0, 3).map((n) => n.target),
    })),
    passes: results.passes.length,
    incomplete: results.incomplete.map((v) => ({ id: v.id, nodes: v.nodes.length })),
  };
}

async function main() {
  const opts = parseArgs();
  let pages = opts.pages ?? [...PUBLIC_PAGES];
  if (opts.authed && !opts.pages) pages = [...PUBLIC_PAGES, ...AUTHED_PAGES];

  await warmup('a11y target');
  const reportDir = newReportDir('a11y');
  const browser = await launchBrowser();
  const rows = [];
  const allResults = [];

  try {
    const { context, page } = await newPage(browser);
    if (opts.authed || (!opts.pages && AUTHED_PAGES.some((p) => pages.includes(p)))) {
      const ok = await ensureAuthenticated(page);
      process.stdout.write(`Authentication via demo/credentials: ${ok ? 'OK' : 'FAILED (auditing public pages only)'}
`);
      if (!ok) pages = pages.filter((p) => !AUTHED_PAGES.includes(p));
    }

    for (const path of pages) {
      process.stdout.write(`Auditing ${path} ...
`);
      try {
        const res = await auditPage(page, path);
        allResults.push(res);
        const critical = res.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
        const totalNodes = res.violations.reduce((s, v) => s + v.nodes, 0);
        rows.push([path, `${res.passes} passed`, `${res.violations.length} rules`, `${totalNodes} nodes`, critical.length ? 'FAIL' : 'PASS']);
        writeFileSync(join(reportDir, `axe${path.replace(/\//g, '_') || '_root'}.json`), JSON.stringify(res, null, 2));
      } catch (err) {
        rows.push([path, '-', '-', '-', `ERROR: ${err.message.slice(0, 80)}`]);
      }
    }
    await context.close();
  } finally {
    await browser.close();
  }

  process.stdout.write(`
=== ACCESSIBILITY SUMMARY (WCAG 2.1 A/AA) ===
`);
  process.stdout.write(`page | passes | violating rules | nodes | verdict
`);
  for (const row of rows) process.stdout.write(`${row.join(' | ')}
`);

  const summary = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    threshold: '0 serious/critical violations per page',
    results: allResults,
  };
  writeFileSync(join(reportDir, 'summary.json'), JSON.stringify(summary, null, 2));
  process.stdout.write(`
Full reports saved to: ${reportDir}
`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});