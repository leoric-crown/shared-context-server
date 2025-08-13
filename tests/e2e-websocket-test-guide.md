# E2E WebSocket Exploratory Test Guide

**Purpose:** Quick orientation and validation of the real-time WebSocket functionality
**Time Required:** 5-10 minutes
**Prerequisites:** Development server running

## Quick Start (30 seconds)

```bash
# 1. Start the development server (includes WebSocket)
uv run python -m shared_context_server.scripts.dev

# 2. Wait for startup logs showing:
#    - "WebSocket server enabled - starting on ws://127.0.0.1:8081"
#    - "🚀 Server started with PID [number]"
#    - "Uvicorn running on http://127.0.0.1:8081"

# 3. Open browser to dashboard
open http://localhost:23456/ui/
```

## Test Scenarios

### 1. 🏠 Dashboard Loading Test
**Objective:** Verify static assets and UI render correctly

**Steps:**
1. Navigate to `http://localhost:23456/ui/`
2. **Expected:** Dashboard loads with session cards
3. **Verify:** Browser console shows `Shared Context Server Web UI loaded`
4. **Check:** CSS styling applied (cards, navigation, colors)

**✅ Success:** Clean UI with no 404 errors in Network tab
**❌ Troubleshoot:** Check `websocket-implementation-findings.md` for static file issues

---

### 2. 🔌 WebSocket Connection Test
**Objective:** Verify real-time WebSocket connectivity

**Steps:**
1. Click any session card "View Session" button
2. Open Browser DevTools → Console tab
3. **Expected:** See connection attempt logs:
   ```
   Connecting to WebSocket: ws://localhost:8081/ws/session_[id]
   WebSocket connected for session: session_[id]
   Successfully subscribed to session updates
   ```
4. **Check:** Connection status shows "Real-time updates active"

**✅ Success:** Connection established, subscription confirmed
**❌ Troubleshoot:** Check port 8081 availability, server logs

---

### 3. 🔄 Manual Connection Test
**Objective:** Verify WebSocket protocol independently

**Steps:**
1. On any session page, open DevTools Console
2. Paste and run this test script:
   ```javascript
   // Manual WebSocket test
   const sessionId = window.location.pathname.split('/').pop();
   const testWs = new WebSocket(`ws://localhost:8081/ws/${sessionId}`);

   testWs.onopen = () => {
       console.log('✅ Manual connection success!');
       testWs.send(JSON.stringify({type: 'subscribe', session_id: sessionId}));
   };

   testWs.onmessage = (event) => {
       console.log('📨 Message received:', JSON.parse(event.data));
   };

   testWs.onclose = (event) => {
       console.log('🔌 Connection closed:', event.code);
   };
   ```

**✅ Success:** Console shows `✅ Manual connection success!` and subscription response
**❌ Troubleshoot:** WebSocket server not running on port 8081

---

### 4. 🏥 Health Check Test
**Objective:** Verify WebSocket server status

**Steps:**
1. Open new browser tab
2. Navigate to `http://127.0.0.1:8081/health`
3. **Expected JSON Response:**
   ```json
   {
     "status": "healthy",
     "websocket_support": true,
     "endpoints": {
       "web_ui": "/ws/{session_id}",
       "mcp_agents": "/mcp/{session_id}"
     },
     "mcpsock_version": "0.1.5",
     "timestamp": "2025-08-13T20:23:19.621993+00:00"
   }
   ```

**✅ Success:** JSON response with `"status": "healthy"`
**❌ Troubleshoot:** Connection refused = WebSocket server not running

---

### 5. 📊 Server Logs Verification
**Objective:** Confirm server-side WebSocket handling

**Steps:**
1. Return to terminal running dev server
2. After WebSocket connection, check for logs:
   ```
   INFO - Web UI WebSocket client connected to session: session_[id]
   INFO - "WebSocket /ws/session_[id]" [accepted]
   INFO - connection open
   ```
3. **Bonus:** Try disconnecting/reconnecting to see connection lifecycle

**✅ Success:** Connection logs appear in real-time
**❌ Troubleshoot:** No logs = connection not reaching server

---

## Troubleshooting Quick Reference

### 🚫 Common Issues

**"WebSocket connection failed"**
- Check port 8081 is free: `lsof -i :8081`
- Restart dev server: `Ctrl+C` then re-run startup command
- Verify `WEBSOCKET_PORT=8081` in `.env`

**"404 Not Found" on static files**
- Static assets served via FastMCP custom routes
- Check server startup logs for route registration
- Clear browser cache: `Cmd/Ctrl + Shift + R`

**"403 Forbidden" WebSocket handshake**
- Old cached JavaScript trying wrong port (23456 vs 8081)
- Force refresh: `Cmd/Ctrl + F5`
- Check actual JS file: `http://localhost:23456/ui/static/js/app.js`

**JavaScript "reconnectAttempts already declared"**
- Multiple script loads due to hot reload
- Refresh page to clean state
- Non-critical for functionality testing

### 🔧 Debug Commands

```bash
# Check WebSocket server status
curl http://127.0.0.1:8081/health

# Kill any conflicting processes
lsof -i :8081
# then: kill -9 [PID]

# Check JavaScript contains correct port
curl http://localhost:23456/ui/static/js/app.js | grep "8081"

# Test WebSocket with wscat (if installed)
wscat -c ws://localhost:8081/ws/test_session
```

### 📋 Success Criteria Checklist

**Basic Functionality:**
- [ ] Dashboard loads without 404 errors
- [ ] Session pages display correctly
- [ ] WebSocket connects to port 8081
- [ ] Subscription message exchange works
- [ ] Health endpoint returns healthy status
- [ ] Server logs show connection events
- [ ] Manual WebSocket test succeeds
- [ ] No critical console errors (deprecation warnings OK)

**Real-Time Broadcasting:**
- [ ] MCP messages appear in WebUI without page reload
- [ ] Message count updates automatically
- [ ] Rapid message sequences display in correct order
- [ ] Cross-session isolation maintained
- [ ] Tab lifecycle doesn't break WebSocket connection
- [ ] Performance remains stable under message load
- [ ] WebSocket events visible in browser console

### 6. 🚀 Real-Time Message Broadcasting Test
**Objective:** Verify MCP messages appear in WebUI without page reload

**Steps:**
1. Open session page in browser (keep WebSocket connected)
2. Note current message count in UI
3. In separate terminal, run this MCP command to add a message:
   ```bash
   # Add new message via MCP (replace session_id with actual ID)
   claude mcp call shared-context-server add_message '{"session_id": "session_[your_id]", "content": "Real-time test message from MCP"}'
   ```
4. **Expected:** Message appears in browser immediately (within 1-2 seconds)
5. **Verify:** Message count updates, new message shows at bottom
6. **Check:** No page reload occurred, WebSocket connection maintained

**✅ Success:** New message appears instantly in WebUI without refresh
**❌ Troubleshoot:** Check WebSocket connection, verify MCP server connection

---

### 7. 🎯 Multi-Message Rapid Broadcasting Test
**Objective:** Test rapid message updates and UI responsiveness

**Steps:**
1. Keep session page open with WebSocket connected
2. Open DevTools Console to monitor WebSocket messages
3. Run multiple MCP commands rapidly:
   ```bash
   # Run these commands in quick succession
   claude mcp call shared-context-server add_message '{"session_id": "session_[id]", "content": "Message 1 - Rapid test"}'
   claude mcp call shared-context-server add_message '{"session_id": "session_[id]", "content": "Message 2 - Performance check"}'
   claude mcp call shared-context-server add_message '{"session_id": "session_[id]", "content": "Message 3 - Final verification"}'
   ```
4. **Expected:** All three messages appear in order, console shows WebSocket events
5. **Verify:** UI remains responsive, scroll position updates, timestamps are sequential

**✅ Success:** All messages appear in correct order with timestamps
**❌ Troubleshoot:** Check for message queuing, WebSocket buffer issues

---

### 8. 🔗 Cross-Session Isolation Test
**Objective:** Verify messages only appear in correct session

**Steps:**
1. Create two test sessions via MCP:
   ```bash
   claude mcp call shared-context-server create_session '{"purpose": "Session A - Isolation Test"}'
   claude mcp call shared-context-server create_session '{"purpose": "Session B - Isolation Test"}'
   ```
2. Open both sessions in separate browser tabs
3. Add message to Session A only:
   ```bash
   claude mcp call shared-context-server add_message '{"session_id": "session_A_id", "content": "This should only appear in Session A"}'
   ```
4. **Expected:** Message appears only in Session A tab, not Session B
5. **Verify:** Session B WebSocket still connected but no new message

**✅ Success:** Message isolation maintained between sessions
**❌ Troubleshoot:** Check session_id routing, WebSocket subscription logic

---

### 9. 📱 Browser Tab Lifecycle Test
**Objective:** Test WebSocket behavior with tab management

**Steps:**
1. Open session page, verify WebSocket connected
2. Switch to another tab for 30 seconds
3. Add message via MCP while tab is inactive
4. Return to session tab
5. **Expected:** Message visible immediately (received while tab inactive)
6. Close and reopen session tab
7. **Expected:** All messages still present, WebSocket reconnects

**✅ Success:** Messages persist across tab lifecycle events
**❌ Troubleshoot:** Check browser WebSocket handling, reconnection logic

---

### 10. ⚡ Performance and Load Test
**Objective:** Test system under moderate message load

**Steps:**
1. Open session page with WebSocket connected
2. Monitor browser performance tab (optional)
3. Create 10 messages rapidly via script:
   ```bash
   # Bash loop for load testing
   for i in {1..10}; do
     claude mcp call shared-context-server add_message '{"session_id": "session_[id]", "content": "Load test message #'$i' - Testing performance"}'
     sleep 0.5
   done
   ```
4. **Expected:** All 10 messages appear smoothly, no UI lag
5. **Verify:** WebSocket connection stable, memory usage reasonable

**✅ Success:** System handles moderate load without performance degradation
**❌ Troubleshoot:** Check WebSocket message queuing, UI rendering performance

---

## Automated Test Script

### Complete E2E Test Automation
Save this as `run-websocket-e2e.sh` for automated testing:

```bash
#!/bin/bash
set -e

echo "🚀 Starting E2E WebSocket Test Suite"
echo "Prerequisites: Dev server running on ports 23456 and 8081"

# Create test session
echo "📝 Creating test session..."
SESSION_RESPONSE=$(claude mcp call shared-context-server create_session '{"purpose": "Automated E2E WebSocket Test"}')
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id')
echo "✅ Created session: $SESSION_ID"

# Add initial message
echo "📤 Adding initial message..."
claude mcp call shared-context-server add_message "{\"session_id\": \"$SESSION_ID\", \"content\": \"Initial message for E2E testing\"}" > /dev/null
echo "✅ Initial message added"

echo "🌐 Open this URL in browser: http://localhost:23456/ui/sessions/$SESSION_ID"
echo "⏳ Waiting 5 seconds for manual browser setup..."
sleep 5

# Test rapid message addition
echo "🚀 Testing rapid message broadcasting..."
for i in {1..5}; do
  claude mcp call shared-context-server add_message "{\"session_id\": \"$SESSION_ID\", \"content\": \"Auto test message #$i - $(date)\"}" > /dev/null
  echo "📨 Sent message $i"
  sleep 1
done

echo "✅ E2E test sequence complete!"
echo "📋 Manual verification checklist:"
echo "   - [ ] All 5 auto messages appeared in browser without refresh"
echo "   - [ ] Messages appeared within 1-2 seconds of sending"
echo "   - [ ] WebSocket connection remained stable"
echo "   - [ ] Message timestamps are sequential"
echo "   - [ ] UI scroll updated to show new messages"

# Cleanup
echo "🧹 Cleaning up test session..."
claude mcp call shared-context-server add_message "{\"session_id\": \"$SESSION_ID\", \"content\": \"Test completed - session can be cleaned up\"}" > /dev/null
echo "✅ Test suite finished!"
```

Make executable with: `chmod +x run-websocket-e2e.sh`

---

## Advanced Testing

### 🔀 Multi-Tab Test
Open multiple session pages simultaneously to verify:
- Independent WebSocket connections per session
- No cross-session message leakage
- Proper connection cleanup on tab close

### 🤖 MCP Endpoint Test
Verify AI agent endpoint works differently:
```javascript
// This should fail from browser (different protocol)
const mcpWs = new WebSocket('ws://localhost:8081/mcp/test_session');
// Expected: Connection may fail due to protocol mismatch - this is correct!
```

### 🔄 Reconnection Test
1. Kill WebSocket server: Find PID with `lsof -i :8081`, then `kill [PID]`
2. Browser should show reconnection attempts
3. Restart server - connection should restore automatically

---

**✨ If all tests pass:** WebSocket implementation is fully functional!
**🐛 If issues found:** Check `websocket-implementation-findings.md` for detailed debugging

---

*Last updated: August 13, 2025*
*Test environment: Development server with hot reload*
