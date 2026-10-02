/**
 * PWA & network resilience audit.
 *
 * Evaluates:
 *   1. Web App manifest validity (installability: name, icons 192+512, display, colors)
 *   2. Service worker availability (offline-first capability)
 *   3. Offline behaviour: page still renders when the network drops
 *
 * Reports: qa/reports/<stamp>-pwa/
 */
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  BASE_URL,
  goto,
  httpGetText,
  launchBrowser,
  newPage,
  newReportDir,
  warmup,
} from './lib/audit-common.mjs';

async function checkManifest() {
  const url = `${BASE_URL}/static/manifest.json`;
  const { status, text } = await httpGetText(url);
  if (status !== 200) throw new Error(`HTTP ${status} for ${url}`);
  const manifest = JSON.parse(text);
  const icons = Array.isArray(manifest.icons) ? manifest.icons : [];
  const sizes = icons.map((i) => String(i.sizes || ''));
  const checks = {
    name_or_short_name: Boolean(manifest.name || manifest.short_name),
    start_url: Boolean(manifest.start_url),
    display: ['standalone', 'fullscreen', 'minimal-ui'].includes(manifest.display),
    icon_192: sizes.some((s) => s.includes('192')),
    icon_512: sizes.some((s) => s.includes('512')),
    theme_color: Boolean(manifest.theme_color),
    background_color: Boolean(manifest.background_color),
  };
  const pass = Object.values(checks).every(Boolean);
  return { url, pass, checks, manifest };
}

async function checkServiceWorkerFile() {
  const url = `${BASE_URL}/static/sw.js`;
  const { status, headers, text } = await httpGetText(url);
  return {
    url,
    status,
    contentType: headers['content-type'] || '',
    bytes: text.length,
    looksLikeJs: /self\.|addEventListener|caches/i.test(text),
    pass: status === 200 && text.length > 100,
  };
}

async function checkOfflineBehaviour(browser) {
  const { context, page } = await newPage(browser);
  try {
    await goto(page, '/');
    // Wait for a service worker to become active (up to 15s).
    const swActive = await page
      .waitForFunction(() => navigator.serviceWorker?.ready.then(() => true), {
        timeout: 15_000,
      })
      .then(() => true)
      .catch(() => false);

    // Give the SW a moment to claim the page if it just registered.
    await page.waitForTimeout(2_000);

    await context.setOffline(true);
    let offlineRendered = false;
    let offlineTitle = '';
    let offlineTextLength = 0;
    try {
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 20_000 });
      await page.waitForTimeout(1_500);
      offlineTitle = await page.title();
      offlineTextLength = await page.evaluate(
        () => document.body?.innerText.trim().length || 0
      );
      offlineRendered = offlineTextLength > 20;
    } catch {
      offlineRendered = false;
    }
    await context.setOffline(false);

    // Verdict: PASS if SW active AND offline reload renders; WARN if no SW; FAIL if offline shows nothing.
    let verdict;
    if (swActive && offlineRendered) verdict = 'PASS';
    else if (!swActive) verdict = 'WARN (no active service worker detected)';
    else verdict = 'FAIL (offline reload rendered nothing)';
    return { swActive, offlineRendered, offlineTitle, offlineTextLength, verdict };
  } finally {
    await context.close();
  }
}

async function main() {
  await warmup('pwa target');
  const reportDir = newReportDir('pwa');
  const browser = await launchBrowser();

  process.stdout.write(`Checking web app manifest ...
`);
  const manifest = await checkManifest().catch((e) => ({ pass: false, error: e.message }));
  process.stdout.write(`Checking service worker file ...
`);
  const swFile = await checkServiceWorkerFile().catch((e) => ({ pass: false, error: e.message }));
  process.stdout.write(`Testing offline behaviour ...
`);
  const offline = await checkOfflineBehaviour(browser).catch((e) => ({
    verdict: `ERROR: ${e.message.slice(0, 80)}`,
  }));
  await browser.close();

  process.stdout.write(`
=== PWA / NETWORK RESILIENCE SUMMARY ===
`);
  process.stdout.write(`manifest installable : ${manifest.pass ? 'PASS' : 'FAIL'} ${JSON.stringify(manifest.checks || {})}
`);
  process.stdout.write(`service worker file  : ${swFile.pass ? 'PASS' : 'FAIL'} (${swFile.bytes ?? '?'} bytes)
`);
  process.stdout.write(`offline behaviour    : ${offline.verdict}
`);

  const summary = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    manifest,
    serviceWorkerFile: swFile,
    offline,
  };
  writeFileSync(join(reportDir, 'summary.json'), JSON.stringify(summary, null, 2));
  process.stdout.write(`
Full report saved to: ${reportDir}
`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});