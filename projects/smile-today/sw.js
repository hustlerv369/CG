/* Smile Today — Service Worker
 * Keeps the app reachable offline and fires hourly notifications even
 * when the tab is hidden or closed. State is mirrored from the page
 * via postMessage('sync', ...).
 */

const CACHE = 'smile-today-v1';
const PRECACHE = [
  '/',
  '/index.html',
  '/style.css',
  '/script.js',
  '/logo.svg',
  '/manifest.json',
];

let nextSmileAt = 0;
let intervalMs = 60 * 60 * 1000;
let quiet = false;
let quotes = ['Smile at someone today.'];
let lastQuoteIndex = -1;

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).catch(() => {}),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((res) => {
        // Cache same-origin GETs
        if (res && res.status === 200 && new URL(event.request.url).origin === location.origin) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(event.request, clone)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match('/index.html'));
    }),
  );

  // Opportunistic check on each fetch: if a hidden tab missed its tick,
  // fire the reminder. (Bounded to once per intervalMs.)
  maybeFireScheduled();
});

self.addEventListener('message', (event) => {
  const msg = event.data || {};
  if (msg.type === 'sync') {
    nextSmileAt = msg.nextSmileAt || nextSmileAt;
    intervalMs = msg.intervalMs || intervalMs;
    quiet = !!msg.quietUntilMorning;
    if (Array.isArray(msg.quotes) && msg.quotes.length) quotes = msg.quotes;
    if (typeof msg.lastQuoteIndex === 'number') lastQuoteIndex = msg.lastQuoteIndex;
  } else if (msg.type === 'notify-now') {
    showSmile(msg.body || pickQuote());
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const c of clients) {
        if ('focus' in c) return c.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow('/');
    }),
  );
});

let lastFiredAt = 0;
function maybeFireScheduled() {
  if (!nextSmileAt) return;
  const now = Date.now();
  if (inQuiet()) return;
  if (now < nextSmileAt) return;
  if (now - lastFiredAt < intervalMs * 0.9) return; // dedupe
  lastFiredAt = now;
  showSmile(pickQuote());
  nextSmileAt = now + intervalMs;
}

function showSmile(body) {
  if (!self.registration || !self.registration.showNotification) return;
  return self.registration.showNotification('Smile Today', {
    body,
    icon: '/logo.svg',
    badge: '/logo.svg',
    tag: 'smile-today',
    renotify: true,
    requireInteraction: false,
  });
}

function pickQuote() {
  if (quotes.length === 0) return 'Smile at someone today.';
  if (quotes.length === 1) return quotes[0];
  let i;
  do { i = Math.floor(Math.random() * quotes.length); } while (i === lastQuoteIndex);
  lastQuoteIndex = i;
  return quotes[i];
}

function inQuiet() {
  if (!quiet) return false;
  const h = new Date().getHours();
  return h >= 22 || h < 7;
}
