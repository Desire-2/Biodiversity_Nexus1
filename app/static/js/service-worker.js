// Service Worker for handling background notifications
const CACHE_NAME = 'chat-app-cache-v1';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/sounds/notification.mp3',
  '/static/sounds/message.mp3',
  '/static/img/logo.png'
];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - serve from cache if available
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Push event - handle incoming push notifications
self.addEventListener('push', event => {
  let data = {};
  if (event.data) {
    data = event.data.json();
  }

  const title = data.title || 'New Notification';
  const options = {
    body: data.body || 'You have a new notification',
    icon: data.icon || '/static/img/logo.png',
    badge: '/static/img/badge.png',
    data: {
      url: data.url || '/'
    },
    vibrate: [100, 50, 100],
    tag: data.tag || 'default',
    renotify: true,
    actions: [
      {
        action: 'open',
        title: 'Open'
      },
      {
        action: 'close',
        title: 'Close'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification click event - handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  // Default action is to open the app
  event.waitUntil(
    clients.matchAll({
      type: 'window'
    })
    .then(clientList => {
      // If a window client is already open, focus it
      for (const client of clientList) {
        if (client.url === event.notification.data.url && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise open a new window
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data.url);
      }
    })
  );
});

// Sync event - handle background sync
self.addEventListener('sync', event => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

// Function to sync messages in the background
async function syncMessages() {
  try {
    // Get unsent messages from IndexedDB
    const unsentMessages = await getUnsentMessages();
    
    // Send each message
    for (const message of unsentMessages) {
      await sendMessage(message);
    }
    
    // Clear unsent messages
    await clearUnsentMessages();
  } catch (error) {
    console.error('Error syncing messages:', error);
  }
}

// These functions would be implemented to work with IndexedDB
// For now they're just placeholders
async function getUnsentMessages() {
  return [];
}

async function sendMessage(message) {
  return fetch('/api/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(message)
  });
}

async function clearUnsentMessages() {
  // Clear unsent messages from IndexedDB
}

