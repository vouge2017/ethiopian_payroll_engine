// EthioPayroll service worker — offline shell + push notifications.
const CACHE_NAME = 'ethiopayroll-assets-v4';

const STATIC_ASSETS = [
  '/static/css/design-system.css',
  '/static/css/responsive.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  return self.clients.claim();
});

// Fetch — only cache static assets. Never cache HTML, API, auth, or font requests.
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  
  // Never cache HTML pages — always get fresh from network
  if (request.mode === 'navigate') return;
  
  // Never cache API, auth, or dynamic endpoints
  if (request.url.includes('/api/') || request.url.includes('/auth/')) return;
  if (request.url.includes('/diff/') || request.url.includes('/demo')) return;
  if (request.url.includes('/favicon')) return;
  
  // Only cache known static assets and CDN resources
  const isStatic = request.url.includes('/static/') ||
                   request.url.includes('cdn.jsdelivr.net') ||
                   request.url.includes('fonts.googleapis.com') ||
                   request.url.includes('fonts.gstatic.com');
  
  if (!isStatic) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => caches.match('/offline'));
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

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});
