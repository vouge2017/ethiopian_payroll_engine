// EthioPayroll service worker — minimal offline shell + cache-first static assets.
// Payroll data is sensitive and time-critical, so we deliberately do NOT cache
// API responses or payslip PDFs. Only the app shell (CSS/JS/fonts) is cached.

const CACHE_NAME = 'ethiopayroll-shell-v1';

const SHELL_ASSETS = [
  '/',
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/offline'  // a simple "you're offline" fallback page — add this route/template
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Never intercept API calls, auth, or payroll data — always go to network.
  if (
    request.method !== 'GET' ||
    request.url.includes('/api/') ||
    request.url.includes('/auth/') ||
    request.url.includes('/payroll/') ||
    request.url.includes('/payslip')
  ) {
    return;
  }

  // Cache-first for static shell assets, fall back to network, then offline page.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).catch(() => caches.match('/offline'));
    })
  );
});
