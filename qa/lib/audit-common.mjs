/**
 * Shared helpers for the UI/UX audit scripts.
 *
 * Environment variables:
 *   AUDIT_BASE_URL   Target site (default: https://ethiopian-payroll-engine.onrender.com)
 *   AUDIT_EMAIL      Optional login id (phone or email) for authenticated audits
 *   AUDIT_PASSWORD   Optional password for authenticated audits
 */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import http from 'node:http';
import https from 'node:https';
import { chromium } from 'playwright-core';

export const BASE_URL = (
  process.env.AUDIT_BASE_URL || 'https://ethiopian-payroll-engine.onrender.com'
).replace(/\/+$/, '');

const QA_DIR = fileURLToPath(new URL('..', import.meta.url));
export const REPORTS_ROOT = join(QA_DIR, 'reports');

/** Create a timestamped report directory: qa/reports/<stamp>-<prefix>/ */
export function newReportDir(prefix) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const dir = join(REPORTS_ROOT, `${stamp}-${prefix}`);
  mkdirSync(dir, { recursive: true });
  return dir;
}

/** Launch an installed Chrome/Edge via playwright-core (no browser download needed). */
const CHANNELS = ['chrome', 'msedge', 'chrome-beta', 'edge'];
export async function launchBrowser() {
  let lastErr;
  for (const channel of CHANNELS) {
    try {
      return await chromium.launch({ channel, headless: true });
    } catch (err) {
      lastErr = err;
    }
  }
  throw new Error(
    [
      'Could not launch Google Chrome or Microsoft Edge.',
      'Fix: install Google Chrome, or run "npx playwright install chromium" and switch',
      'launchBrowser() to chromium.launch() without a channel.',
      `Last error: ${lastErr && lastErr.message}`,
    ].join('\\n')
  );
}

/** Open a page in a fresh context with the given viewport. */
export async function newPage(browser, viewport) {
  const context = await browser.newContext({
    viewport: viewport || { width: 1280, height: 800 },
    locale: 'en-US',
  });
  const page = await context.newPage();
  return { context, page };
}

/**
 * Navigate with generous timeouts (Render free tier cold starts can take minutes).
 *
 * Uses waitUntil:'commit' then a bounded wait for DOMContentLoaded so that
 * render-blocking third-party CDNs (fonts/jsdelivr) that hang on slow or
 * filtered networks cannot stall the whole audit.
 */
export async function goto(page, path, opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
  await page.goto(url, {
    waitUntil: 'commit',
    timeout: opts.timeout ?? 90_000,
  });
  await page
    .waitForLoadState('domcontentloaded', { timeout: 20_000 })
    .catch(() => {});
  await page.waitForTimeout(opts.settleMs ?? 2_500);
}

/**
 * Warm up the target (wake a sleeping Render instance) before auditing.
 *
 * Uses node:http(s) instead of fetch because some networks (TLS-intercepting
 * proxies / corporate firewalls) present a self-signed certificate that Node's
 * default CA bundle rejects. Set AUDIT_STRICT_TLS=1 to enforce certificate
 * validation instead.
 */
export async function warmup(label = 'target') {
  process.stdout.write(`Warming up ${label}: ${BASE_URL} ...
`);
  const rejectUnauthorized = process.env.AUDIT_STRICT_TLS === '1';
  const deadline = Date.now() + 180_000;
  while (Date.now() < deadline) {
    const up = await new Promise((resolve) => {
      try {
        const u = new URL(BASE_URL);
        const mod = u.protocol === 'http:' ? http : https;
        const req = mod.request(
          u,
          { method: 'GET', rejectUnauthorized, timeout: 30_000 },
          (res) => {
            res.resume();
            resolve(Boolean(res.statusCode && res.statusCode < 500));
          }
        );
        req.on('timeout', () => {
          req.destroy();
          resolve(false);
        });
        req.on('error', () => resolve(false));
        req.end();
      } catch {
        resolve(false);
      }
    });
    if (up) {
      process.stdout.write(`Target is up.
`);
      return true;
    }
    await new Promise((r) => setTimeout(r, 5_000));
  }
  throw new Error(`Target did not respond within 180s: ${BASE_URL}`);
}

/**
 * GET a URL as text using node:http(s) with the same TLS policy as warmup()
 * (lenient by default; AUDIT_STRICT_TLS=1 enforces validation).
 * Returns { status, headers, text }.
 */
export function httpGetText(url) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const mod = u.protocol === 'http:' ? http : https;
    const req = mod.request(
      u,
      {
        method: 'GET',
        rejectUnauthorized: process.env.AUDIT_STRICT_TLS === '1',
        timeout: 30_000,
      },
      (res) => {
        if (
          res.statusCode >= 300 &&
          res.statusCode < 400 &&
          res.headers.location
        ) {
          res.resume();
          resolve(httpGetText(new URL(res.headers.location, u).toString()));
          return;
        }
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (c) => (data += c));
        res.on('end', () =>
          resolve({ status: res.statusCode, headers: res.headers, text: data })
        );
      }
    );
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('request timed out'));
    });
    req.on('error', reject);
    req.end();
  });
}

/** Log in through the demo-mode link (no credentials needed), if available. */
export async function loginViaDemo(page) {
  try {
    await goto(page, '/demo');
    await page.waitForTimeout(2_000);
    return !page.url().includes('/login');
  } catch {
    return false;
  }
}

/** Log in through the /auth/login form using AUDIT_EMAIL / AUDIT_PASSWORD. */
export async function loginViaForm(page, loginId, password) {
  if (!loginId || !password) return false;
  try {
    await goto(page, '/auth/login');
    await page.fill('#login_id', loginId);
    await page.fill('#password', password);
    await Promise.all([
      page
        .waitForURL((u) => !u.pathname.includes('/login'), { timeout: 60_000 })
        .catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    return !page.url().includes('/login');
  } catch {
    return false;
  }
}

/** Try demo mode first, then form credentials. Returns true if authenticated. */
export async function ensureAuthenticated(page) {
  if (await loginViaDemo(page)) return true;
  return loginViaForm(page, process.env.AUDIT_EMAIL, process.env.AUDIT_PASSWORD);
}

/** Simple console table printer. */
export function printTable(rows) {
  for (const row of rows) {
    process.stdout.write(`${row.join(' | ')}
`);
  }
}