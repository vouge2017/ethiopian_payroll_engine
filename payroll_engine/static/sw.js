// EthioPayroll service worker — offline shell + offline pages + push notifications.
//
// Strategy:
//   - Static assets: cache-first (shell cache)
//   - Page navigations: network-first, cached for offline reuse, /offline fallback
//   - /api/* and /auth/*: never intercepted (always live)

const SHELL_CACHE = 'ethiopayroll-shell-v3';
const PAGE_CACHE = 'ethiopayroll-pages-v1';

const SHELL_ASSETS = [
  '/static/css/design-system.css',
  '/static/css/responsive.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean up any caches from previous versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== PAGE_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  let url;
  try {
    url = new URL(request.url);
  } catch {
    return;
  }

  // Never intercept cross-origin requests (CDNs, fonts, analytics).
  if (url.origin !== self.location.origin) return;

  // ── Page navigations: network-first with offline fallback ──
  // This is what makes the app usable during power/network outages:
  // the last-seen pages are served from cache, and if nothing is cached
  // the friendly /offline screen renders instead of a browser error.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful, non-login pages for offline reuse.
          // Login/register pages are never cached (avoids stale auth states).
          const finalUrl = response.url || request.url;
          const isLoginPage =
            finalUrl.includes('/auth/login') || finalUrl.includes('/auth/register');
          if (response && response.ok && !isLoginPage && !response.redirected) {
            const copy = response.clone();
            caches.open(PAGE_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(async () => {
          const cached =
            (await caches.match(request)) || (await caches.match('/offline'));
          return (
            cached ||
            new Response('<h1>Offline</h1><p>You are offline.</p>', {
              status: 503,
              headers: { 'Content-Type': 'text/html' },
            })
          );
        })
    );
    return;
  }

  // ── API & auth requests: always hit the network ──
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) {
    return;
  }

  // ── Same-origin static assets: cache-first ──
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).catch(() => caches.match('/offline'));
    })
  );
});

// Push notifications
self.addEventListener('push', (event) => {
  let data = { title: 'EthioPayroll', body: 'You have a new notification' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' },
    actions: [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Focus existing window if open
      for (const client of windowClients) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise open new window
      return clients.openWindow(url);
    })
  );
});