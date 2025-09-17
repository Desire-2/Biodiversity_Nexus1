/**
 * Notification Handler
 * 
 * This script handles browser notifications, service worker registration,
 * and notification permission management.
 */

class NotificationHandler {
  constructor() {
    this.hasNotificationPermission = false;
    this.serviceWorkerRegistration = null;
    this.notificationCount = 0;
    this.notificationSound = new Audio('/static/sounds/notification.mp3');
    this.messageSound = new Audio('/static/sounds/message.mp3');
    
    // Set volume
    this.notificationSound.volume = 0.5;
    this.messageSound.volume = 0.5;
    
    // Initialize
    this.init();
  }
  
  /**
   * Initialize the notification handler
   */
  async init() {
    // Check if browser supports notifications
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return;
    }
    
    // Check notification permission
    this.checkPermission();
    
    // Register service worker
    await this.registerServiceWorker();
    
    // Set up event listeners
    this.setupEventListeners();
  }
  
  /**
   * Check if notification permission is granted
   */
  checkPermission() {
    this.hasNotificationPermission = Notification.permission === 'granted';
    
    // Update UI based on permission status
    this.updatePermissionUI();
  }
  
  /**
   * Update UI elements based on notification permission
   */
  updatePermissionUI() {
    const permissionButtons = document.querySelectorAll('.notification-permission-btn');
    
    permissionButtons.forEach(button => {
      if (this.hasNotificationPermission) {
        button.textContent = 'Notifications Enabled';
        button.classList.add('enabled');
        button.classList.remove('disabled');
      } else {
        button.textContent = 'Enable Notifications';
        button.classList.add('disabled');
        button.classList.remove('enabled');
      }
    });
  }
  
  /**
   * Register the service worker
   */
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        this.serviceWorkerRegistration = await navigator.serviceWorker.register('/static/js/service-worker.js');
        console.log('Service Worker registered with scope:', this.serviceWorkerRegistration.scope);
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }
  
  /**
   * Set up event listeners
   */
  setupEventListeners() {
    // Listen for permission button clicks
    document.querySelectorAll('.notification-permission-btn').forEach(button => {
      button.addEventListener('click', () => this.requestPermission());
    });
    
    // Listen for custom notification events
    document.addEventListener('app:notification', event => {
      this.showNotification(event.detail.title, event.detail.body, event.detail.icon, event.detail.url);
    });
    
    // Listen for custom message events
    document.addEventListener('app:message', event => {
      this.showMessageNotification(event.detail.sender, event.detail.message, event.detail.url);
    });
  }
  
  /**
   * Request notification permission
   */
  async requestPermission() {
    if (!('Notification' in window)) {
      alert('This browser does not support desktop notifications');
      return;
    }
    
    if (Notification.permission === 'granted') {
      alert('Notifications are already enabled!');
      return;
    }
    
    if (Notification.permission === 'denied') {
      alert('You have previously denied notification permissions. Please enable them in your browser settings.');
      return;
    }
    
    try {
      const permission = await Notification.requestPermission();
      
      if (permission === 'granted') {
        this.hasNotificationPermission = true;
        this.updatePermissionUI();
        
        // Show a test notification
        this.showNotification('Notifications Enabled', 'You will now receive notifications when new messages arrive.');
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error);
    }
  }
  
  /**
   * Show a notification
   * 
   * @param {string} title - Notification title
   * @param {string} body - Notification body
   * @param {string} icon - Notification icon URL
   * @param {string} url - URL to open when notification is clicked
   */
  showNotification(title, body, icon = '/static/img/logo.png', url = '/') {
    // Check if we have permission
    if (!this.hasNotificationPermission) {
      console.log('No notification permission');
      return;
    }
    
    // Play notification sound
    this.playNotificationSound();
    
    // Update notification count
    this.updateNotificationCount(1);
    
    // If service worker is active and Push API is supported
    if (this.serviceWorkerRegistration && 'PushManager' in window) {
      // Use service worker to show notification
      this.serviceWorkerRegistration.showNotification(title, {
        body: body,
        icon: icon,
        badge: '/static/img/badge.png',
        data: {
          url: url
        },
        vibrate: [100, 50, 100],
        tag: 'notification',
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
      });
    } else {
      // Fallback to regular Notification API
      const notification = new Notification(title, {
        body: body,
        icon: icon
      });
      
      notification.onclick = function() {
        window.focus();
        window.location.href = url;
        notification.close();
      };
      
      // Auto close after 5 seconds
      setTimeout(() => {
        notification.close();
      }, 5000);
    }
  }
  
  /**
   * Show a message notification
   * 
   * @param {string} sender - Message sender
   * @param {string} message - Message content
   * @param {string} url - URL to open when notification is clicked
   */
  showMessageNotification(sender, message, url = '/messages') {
    this.showNotification(`New message from ${sender}`, message, '/static/img/message-icon.png', url);
    this.playMessageSound();
  }
  
  /**
   * Play notification sound
   */
  playNotificationSound() {
    this.notificationSound.currentTime = 0;
    this.notificationSound.play().catch(error => {
      console.error('Error playing notification sound:', error);
    });
  }
  
  /**
   * Play message sound
   */
  playMessageSound() {
    this.messageSound.currentTime = 0;
    this.messageSound.play().catch(error => {
      console.error('Error playing message sound:', error);
    });
  }
  
  /**
   * Update notification count
   * 
   * @param {number} count - Number to add to current count
   */
  updateNotificationCount(count) {
    this.notificationCount += count;
    
    // Update badge
    const badge = document.getElementById('notification-badge');
    if (badge) {
      if (this.notificationCount > 0) {
        badge.textContent = this.notificationCount;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    }
    
    // Update page title
    if (this.notificationCount > 0) {
      document.title = `(${this.notificationCount}) ${document.title.replace(/^\(\d+\)\s/, '')}`;
    } else {
      document.title = document.title.replace(/^\(\d+\)\s/, '');
    }
    
    // Update favicon with badge (would require additional library)
  }
  
  /**
   * Set notification count
   * 
   * @param {number} count - New count value
   */
  setNotificationCount(count) {
    this.notificationCount = count;
    
    // Update badge
    const badge = document.getElementById('notification-badge');
    if (badge) {
      if (this.notificationCount > 0) {
        badge.textContent = this.notificationCount;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    }
    
    // Update page title
    if (this.notificationCount > 0) {
      document.title = `(${this.notificationCount}) ${document.title.replace(/^\(\d+\)\s/, '')}`;
    } else {
      document.title = document.title.replace(/^\(\d+\)\s/, '');
    }
  }
}

// Initialize notification handler when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.notificationHandler = new NotificationHandler();
});

