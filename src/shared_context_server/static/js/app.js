// Global application JavaScript for Shared Context Server Web UI

// Global WebSocket connection
let websocketConnection = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Shared Context Server Web UI loaded');

    // Initialize global components
    initializeConnectionMonitor();
    initializeTimestamps();
    initializeClipboard();
    initializeMarkdownRenderer();
    initializeActivityIndicators();
    initializeWebSocket();
});

// Connection monitoring for health status
function initializeConnectionMonitor() {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;

    // Check connection status periodically
    setInterval(checkConnectionStatus, 30000); // Every 30 seconds

    // Initial check
    checkConnectionStatus();
}

async function checkConnectionStatus() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        const statusIndicator = document.querySelector('#connection-status .status-dot');
        const statusText = document.querySelector('#connection-status .status-text');

        if (statusIndicator && statusText) {
            statusIndicator.className = 'status-dot';

            if (data.status === 'healthy') {
                statusIndicator.classList.add('online');
                statusText.textContent = 'Online';
            } else {
                statusIndicator.classList.add('error');
                statusText.textContent = 'Unhealthy';
            }
        }
    } catch (error) {
        console.error('Failed to check connection status:', error);

        const statusIndicator = document.querySelector('#connection-status .status-dot');
        const statusText = document.querySelector('#connection-status .status-text');

        if (statusIndicator && statusText) {
            statusIndicator.className = 'status-dot offline';
            statusText.textContent = 'Offline';
        }
    }
}

// Initialize timestamp formatting
function initializeTimestamps() {
    formatTimestamps();

    // Update timestamps every minute for relative times
    setInterval(formatTimestamps, 60000);
}

function formatTimestamps() {
    const timestampElements = document.querySelectorAll('[data-timestamp]');

    timestampElements.forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        if (timestamp) {
            try {
                const date = new Date(timestamp);
                element.textContent = formatRelativeTime(date);
                element.title = date.toLocaleString(); // Show full time on hover
            } catch (error) {
                console.warn('Failed to parse timestamp:', timestamp);
            }
        }
    });
}

function formatRelativeTime(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 60) {
        return 'just now';
    } else if (diffMinutes < 60) {
        return `${diffMinutes} min ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hr ago`;
    } else if (diffDays < 7) {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

// Clipboard functionality
function initializeClipboard() {
    // Add click handlers for copy buttons
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('copy-btn')) {
            const textToCopy = event.target.previousElementSibling?.textContent ||
                              event.target.getAttribute('data-copy');

            if (textToCopy) {
                copyToClipboard(textToCopy);
            }
        }
    });
}

// Memory UI Functions

// Memory modal functions removed - templates handle their own enhanced modals with proper encapsulation

// Old modal functions removed - templates now use enhanced modals with proper encapsulation

// Utility Functions

// Copy text to clipboard with feedback
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => {
                showNotification('Copied to clipboard!');
            })
            .catch(error => {
                console.error('Failed to copy to clipboard:', error);
                fallbackCopyTextToClipboard(text);
            });
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

// Fallback copy method for older browsers
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;

    // Avoid scrolling to bottom
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.position = 'fixed';

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showNotification('Copied to clipboard!');
        } else {
            showNotification('Failed to copy to clipboard', 'error');
        }
    } catch (error) {
        console.error('Fallback copy failed:', error);
        showNotification('Failed to copy to clipboard', 'error');
    }

    document.body.removeChild(textArea);
}

// Show notification toast
function showNotification(message, type = 'success') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => {
        notification.remove();
    });

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Trigger show animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Auto-hide notification
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Escape HTML for security
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Debounce utility for performance optimization
function debounce(func, wait, immediate = false) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Theme management (future feature)
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Load saved theme preference
function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
}

// Auto-refresh functionality for dashboard
function enableAutoRefresh(intervalMs = 30000) {
    if (window.location.pathname === '/ui/') {
        setInterval(() => {
            // Only refresh if user hasn't interacted recently
            if (document.visibilityState === 'visible' &&
                Date.now() - getLastUserActivity() > 10000) {
                window.location.reload();
            }
        }, intervalMs);
    }
}

let lastUserActivity = Date.now();

function trackUserActivity() {
    lastUserActivity = Date.now();
}

function getLastUserActivity() {
    return lastUserActivity;
}

// Track user activity
document.addEventListener('mousemove', trackUserActivity);
document.addEventListener('keydown', trackUserActivity);
document.addEventListener('click', trackUserActivity);

// Error handling
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    // Could send to monitoring service in production
});

// Service worker registration (future feature for offline support)
function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/ui/static/js/sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful:', registration.scope);
            })
            .catch(error => {
                console.log('ServiceWorker registration failed:', error);
            });
    }
}

// ============================================================================
// REAL-TIME WEBSOCKET FUNCTIONALITY
// ============================================================================

async function initializeWebSocket() {
    // Only initialize WebSocket on session pages
    const sessionMatch = window.location.pathname.match(/\/ui\/sessions\/(.+)$/);
    if (!sessionMatch) return;

    const sessionId = sessionMatch[1];
    await connectWebSocket(sessionId);
}

async function connectWebSocket(sessionId) {
    if (websocketConnection && websocketConnection.readyState === WebSocket.OPEN) {
        return; // Already connected
    }

    // Fetch WebSocket configuration from health endpoint
    let wsPort = '34567'; // Default fallback
    try {
        const healthResponse = await fetch('/health');
        const health = await healthResponse.json();
        if (health.config && health.config.websocket_port) {
            wsPort = health.config.websocket_port.toString();
        }
    } catch (error) {
        console.warn('Failed to fetch WebSocket config from health endpoint, using default port:', error);
    }

    // Connect to WebSocket server
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname;
    const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/${sessionId}`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);

    try {
        websocketConnection = new WebSocket(wsUrl);

        websocketConnection.onopen = function(event) {
            console.log('WebSocket connected for session:', sessionId);
            reconnectAttempts = 0;
            updateWebSocketStatus('connected');

            // Send initial subscription
            sendWebSocketMessage({
                type: 'subscribe',
                session_id: sessionId
            });
        };

        websocketConnection.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data, sessionId);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        websocketConnection.onclose = function(event) {
            console.log('WebSocket disconnected:', event.code, event.reason);
            updateWebSocketStatus('disconnected');

            // Attempt reconnection
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`Attempting to reconnect... (${reconnectAttempts}/${maxReconnectAttempts})`);
                setTimeout(() => connectWebSocket(sessionId), 2000 * reconnectAttempts);
            } else {
                console.error('Max reconnection attempts reached');
                updateWebSocketStatus('failed');
            }
        };

        websocketConnection.onerror = function(error) {
            console.error('WebSocket error:', error);
            updateWebSocketStatus('error');
        };

    } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        updateWebSocketStatus('error');
    }
}

function sendWebSocketMessage(message) {
    if (websocketConnection && websocketConnection.readyState === WebSocket.OPEN) {
        websocketConnection.send(JSON.stringify(message));
    } else {
        console.warn('WebSocket not connected, cannot send message:', message);
    }
}

function handleWebSocketMessage(data, sessionId) {
    console.log('WebSocket message received:', data);

    if (data.type === 'new_message') {
        // Add new message to the UI
        addMessageToUI(data.data);
        showNotification('New message received');
    } else if (data.type === 'session_update') {
        // Handle session updates
        updateSessionInfo(data);
    } else if (data.type === 'subscribed') {
        console.log('Successfully subscribed to session updates');
        updateWebSocketStatus('subscribed');
    } else {
        console.log('Unknown WebSocket message type:', data.type);
    }
}

function addMessageToUI(messageData) {
    const messagesContainer = document.querySelector('.messages-container .messages-list');
    if (!messagesContainer) return;

    // Create message element
    const messageElement = document.createElement('div');
    messageElement.className = 'message-card';
    messageElement.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${escapeHtml(messageData.sender)}</span>
            <span class="message-time">${formatRelativeTime(messageData.timestamp)}</span>
            <span class="message-visibility ${messageData.visibility}">${messageData.visibility}</span>
        </div>
        <div class="message-content">${escapeHtml(messageData.content)}</div>
        ${messageData.metadata ? `<div class="message-metadata">Metadata: ${JSON.stringify(messageData.metadata)}</div>` : ''}
    `;

    // Add to container with animation
    messageElement.style.opacity = '0';
    messagesContainer.appendChild(messageElement);

    // Fade in animation
    setTimeout(() => {
        messageElement.style.transition = 'opacity 0.3s ease-in-out';
        messageElement.style.opacity = '1';
    }, 10);

    // Scroll to new message
    messageElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function updateSessionInfo(sessionData) {
    // Update session statistics if available
    const sessionInfo = document.querySelector('.session-info');
    if (sessionInfo && sessionData.message_count) {
        const messageCount = sessionInfo.querySelector('.message-count');
        if (messageCount) {
            messageCount.textContent = sessionData.message_count;
        }
    }
}

function updateWebSocketStatus(status) {
    const statusElement = document.querySelector('.websocket-status');
    if (!statusElement) return;

    const statusDot = statusElement.querySelector('.status-dot');
    const statusText = statusElement.querySelector('.status-text');

    if (statusDot) statusDot.className = 'status-dot';

    switch (status) {
        case 'connected':
        case 'subscribed':
            if (statusDot) statusDot.classList.add('online');
            if (statusText) statusText.textContent = 'Real-time updates active';
            break;
        case 'disconnected':
            if (statusDot) statusDot.classList.add('warning');
            if (statusText) statusText.textContent = 'Reconnecting...';
            break;
        case 'error':
        case 'failed':
            if (statusDot) statusDot.classList.add('error');
            if (statusText) statusText.textContent = 'Real-time updates unavailable';
            break;
    }
}

// Keep connection alive with periodic pings
setInterval(() => {
    if (websocketConnection && websocketConnection.readyState === WebSocket.OPEN) {
        sendWebSocketMessage({ type: 'ping' });
    }
}, 30000); // Ping every 30 seconds

// ============================================================================
// MARKDOWN RENDERING
// ============================================================================

function initializeMarkdownRenderer() {
    // Configure marked for safe rendering
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (typeof Prism !== 'undefined' && Prism.languages[lang]) {
                    return Prism.highlight(code, Prism.languages[lang], lang);
                }
                return code;
            },
            breaks: true,
            gfm: true,
            sanitize: false, // We'll sanitize manually
            smartypants: true
        });
    }

    // Render existing message content
    renderMarkdownContent();
}

function renderMarkdownContent() {
    const messageElements = document.querySelectorAll('.message-content[data-raw-content]');

    messageElements.forEach(element => {
        const rawContent = element.getAttribute('data-raw-content');
        if (rawContent && typeof marked !== 'undefined') {
            try {
                // Render markdown
                const htmlContent = marked.parse(rawContent);
                element.innerHTML = htmlContent;

                // Add copy buttons to code blocks
                addCopyButtonsToCodeBlocks(element);

                // Highlight code if Prism is available
                if (typeof Prism !== 'undefined') {
                    Prism.highlightAllUnder(element);
                }
            } catch (error) {
                console.error('Failed to render markdown:', error);
                // Fallback to plain text
                element.textContent = rawContent;
            }
        }
    });
}

function addCopyButtonsToCodeBlocks(container) {
    const codeBlocks = container.querySelectorAll('pre > code');

    codeBlocks.forEach(codeBlock => {
        const pre = codeBlock.parentElement;

        // Skip if copy button already exists
        if (pre.querySelector('.copy-code-btn')) return;

        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-code-btn';
        copyBtn.innerHTML = '📋';
        copyBtn.title = 'Copy code';
        copyBtn.setAttribute('data-copy', codeBlock.textContent);

        // Position button
        pre.style.position = 'relative';
        copyBtn.style.position = 'absolute';
        copyBtn.style.top = '8px';
        copyBtn.style.right = '8px';
        copyBtn.style.background = 'rgba(0,0,0,0.1)';
        copyBtn.style.border = 'none';
        copyBtn.style.borderRadius = '4px';
        copyBtn.style.padding = '4px 8px';
        copyBtn.style.cursor = 'pointer';
        copyBtn.style.fontSize = '12px';

        copyBtn.addEventListener('click', () => {
            copyToClipboard(codeBlock.textContent);
        });

        pre.appendChild(copyBtn);
    });
}

// ============================================================================
// ACTIVITY INDICATORS
// ============================================================================

function initializeActivityIndicators() {
    updateSessionActivityIndicators();

    // Update every minute
    setInterval(updateSessionActivityIndicators, 60000);
}

function updateSessionActivityIndicators() {
    const sessionCards = document.querySelectorAll('.session-card[data-session-id]');

    sessionCards.forEach(card => {
        const timestampElements = card.querySelectorAll('.timestamp-value');
        let lastActivityTime = null;

        // Find the most recent activity time
        timestampElements.forEach(element => {
            const text = element.textContent.trim();
            // Look for "Last Activity:" timestamp
            if (element.closest('.timestamp-item')?.querySelector('.timestamp-label')?.textContent.includes('Last Activity')) {
                lastActivityTime = parseTimestampFromElement(element);
            }
        });

        // If no last activity, use created time
        if (!lastActivityTime) {
            timestampElements.forEach(element => {
                const text = element.textContent.trim();
                if (element.closest('.timestamp-item')?.querySelector('.timestamp-label')?.textContent.includes('Created')) {
                    lastActivityTime = parseTimestampFromElement(element);
                }
            });
        }

        if (lastActivityTime) {
            const activityClass = getActivityClass(lastActivityTime);

            // Remove existing activity classes
            card.classList.remove('activity-fresh', 'activity-recent', 'activity-stale');
            card.classList.add(activityClass);

            // Add activity indicator badge if it doesn't exist
            addActivityIndicator(card, activityClass);
        }
    });
}

function parseTimestampFromElement(element) {
    // Try to extract timestamp from various formats
    const text = element.textContent.trim();

    // Try parsing as date
    const date = new Date(text);
    if (!isNaN(date.getTime())) {
        return date;
    }

    // Try to find pattern like "X hours ago" or "X min ago"
    const relativeMatch = text.match(/(\d+)\s*(min|minutes?|hr|hours?|day|days?)\s*ago/i);
    if (relativeMatch) {
        const value = parseInt(relativeMatch[1]);
        const unit = relativeMatch[2].toLowerCase();
        const now = new Date();

        if (unit.startsWith('min')) {
            return new Date(now.getTime() - (value * 60 * 1000));
        } else if (unit.startsWith('hr') || unit.startsWith('hour')) {
            return new Date(now.getTime() - (value * 60 * 60 * 1000));
        } else if (unit.startsWith('day')) {
            return new Date(now.getTime() - (value * 24 * 60 * 60 * 1000));
        }
    }

    return null;
}

function getActivityClass(timestamp) {
    const now = new Date();
    const diffMs = now - timestamp;
    const diffMinutes = diffMs / (1000 * 60);

    if (diffMinutes < 5) {
        return 'activity-fresh';  // < 5 minutes
    } else if (diffMinutes < 60) {
        return 'activity-recent'; // < 1 hour
    } else {
        return 'activity-stale';  // > 1 hour
    }
}

function addActivityIndicator(card, activityClass) {
    // Check if indicator already exists
    if (card.querySelector('.activity-indicator')) return;

    const indicator = document.createElement('span');
    indicator.className = `activity-indicator ${activityClass.replace('activity-', '')}`;

    let text, icon;
    switch (activityClass) {
        case 'activity-fresh':
            text = 'Active';
            icon = '🟢';
            break;
        case 'activity-recent':
            text = 'Recent';
            icon = '🟡';
            break;
        case 'activity-stale':
            text = 'Stale';
            icon = '⚪';
            break;
        default:
            text = 'Unknown';
            icon = '⚫';
    }

    indicator.innerHTML = `${icon} ${text}`;

    // Add to session header
    const sessionHeader = card.querySelector('.session-header');
    if (sessionHeader) {
        sessionHeader.appendChild(indicator);
    }
}

// Export functions for global use
window.SharedContextUI = {
    showNotification,
    copyToClipboard,
    formatRelativeTime,
    escapeHtml,
    debounce,
    toggleTheme,
    checkConnectionStatus,
    connectWebSocket,
    sendWebSocketMessage,
    renderMarkdownContent,
    updateSessionActivityIndicators
};
