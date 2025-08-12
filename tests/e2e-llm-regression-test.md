# E2E LLM Regression Testing Script for Shared Context MCP Server

This script is designed to be executed by an LLM to automatically test the Shared Context MCP Server functionality. Execute each step in order and verify the expected results.

## Prerequisites
- MCP server is running and accessible
- LLM has access to shared-context-server MCP tools
- API_KEY is properly configured for authentication

## Test Suite: Core Functionality Regression

### Test 1: Authentication System
**Goal**: Verify secure token authentication (PRP-006) is working

**Execute**:
```
Use the authenticate_agent tool with:
- agent_id: "test_regression_agent"
- agent_type: "claude"
- requested_permissions: ["read", "write"]
```

**Expected Result**:
- Success: true
- Token format: starts with "sct_"
- Token type: "Protected"
- Expires_at: ~1 hour from now
- Agent_id matches input

**Validation**: Check that the token is NOT a raw JWT (should not contain dots)

---

### Test 2: Session Management
**Goal**: Test session creation and retrieval

**Execute**:
```
1. Use create_session tool with purpose: "E2E regression testing session"
2. Store the returned session_id for use in subsequent tests
3. Use get_session tool with the session_id from step 1
```

**Expected Result**:
- Session created successfully with UUID format session_id
- Session retrieval shows correct purpose and created_by
- Created_at timestamp is recent (within last minute)

---

### Test 3: Message Storage and Retrieval
**Goal**: Test message operations with visibility controls

**Execute**:
```
Using the session_id from Test 2:

1. Add a public message:
   - content: "Public message for regression test"
   - visibility: "public"

2. Add a private message:
   - content: "Private message for regression test"
   - visibility: "private"

3. Add an agent-only message:
   - content: "Agent-only message for regression test"
   - visibility: "agent_only"

4. Get messages from the session (limit: 10)
```

**Expected Result**:
- All 3 messages stored successfully with sequential message_ids
- get_messages returns all 3 messages (agent can see all visibility types)
- Messages have correct timestamps, sender, and content
- Visibility fields match what was sent

---

### Test 4: Agent Memory Operations
**Goal**: Test private memory storage with session and global scopes

**Execute**:
```
1. Set session-scoped memory:
   - key: "regression_test_session"
   - value: {"test": "session_memory", "timestamp": current_timestamp}
   - session_id: use from Test 2

2. Set global memory:
   - key: "regression_test_global"
   - value: {"test": "global_memory", "shared": true}
   - (no session_id for global)

3. Retrieve session memory using key and session_id
4. Retrieve global memory using key only
5. List memory entries (should show both)
```

**Expected Result**:
- Session memory stored and retrievable only with correct session_id
- Global memory stored and retrievable without session_id
- Both memories contain exact JSON values that were stored
- List shows both entries with correct scopes

---

### Test 5: Memory Isolation Testing
**Goal**: Verify session memory isolation between different sessions

**Execute**:
```
1. Create a second session: purpose "Isolation test session"
2. In new session, try to get memory key "regression_test_session"
3. In new session, try to get global memory "regression_test_global"
4. Set new session memory in second session:
   - key: "regression_test_session" (same key, different session)
   - value: {"test": "different_session", "isolated": true}
5. Verify first session still has original session memory
```

**Expected Result**:
- Session memory from first session is NOT accessible from second session
- Global memory IS accessible from second session
- Each session can have same key with different values (isolation working)
- Original session memory unchanged

---

### Test 6: Search Functionality
**Goal**: Test fuzzy search across messages

**Execute**:
```
Using the session from Test 2:
1. Search for "regression" in the session
2. Search for "private" in the session
3. Search for "nonexistent" in the session
```

**Expected Result**:
- "regression" search returns multiple messages (all 3 contain this word)
- "private" search returns the private message
- "nonexistent" search returns empty results
- All results include similarity scores and proper message data

---

### Test 7: Cleanup and TTL Testing
**Goal**: Test memory expiration and cleanup

**Execute**:
```
1. Set memory with short TTL:
   - key: "ttl_test"
   - value: {"expires": "soon"}
   - expires_in: 5 (5 seconds)

2. Immediately retrieve the memory (should work)
3. Wait 6 seconds
4. Try to retrieve the memory again (should fail)
```

**Expected Result**:
- Memory stored successfully with expiration
- Immediate retrieval works
- After expiration, retrieval fails with "MEMORY_NOT_FOUND"
- TTL system working correctly

---

### Test 8: Error Handling and Edge Cases
**Goal**: Test system resilience and error responses

**Execute**:
```
1. Try to get session with invalid session_id: "invalid_session"
2. Try to get memory with non-existent key: "does_not_exist"
3. Try to add message to non-existent session: "invalid_session"
4. Try to create session with empty purpose: ""
```

**Expected Result**:
- All operations fail gracefully with proper error codes
- Error messages are descriptive and include suggestions
- No server crashes or unexpected responses
- Error structure includes: success=false, error, code, severity

---

### Test 9: Concurrent Operations Simulation
**Goal**: Test multi-agent scenario simulation

**Execute**:
```
1. Authenticate a second agent:
   - agent_id: "concurrent_test_agent"
   - agent_type: "gemini"

2. Have both agents add messages to the same session rapidly:
   - Agent 1: "Message from agent 1 - test 1"
   - Agent 2: "Message from agent 2 - test 1"
   - Agent 1: "Message from agent 1 - test 2"
   - Agent 2: "Message from agent 2 - test 2"

3. Retrieve all messages and verify ordering
```

**Expected Result**:
- Both agents authenticated with different tokens
- All messages stored successfully without conflicts
- Messages have proper sender attribution
- No database locking or concurrency issues

---

### Test 10: Performance and Scale Testing
**Goal**: Test system under moderate load

**Execute**:
```
1. Create 5 sessions with different purposes
2. Add 10 messages to each session (50 total messages)
3. Set 10 memory entries (mix of session and global)
4. Search across all sessions for common term
5. Retrieve all sessions and verify data integrity
```

**Expected Result**:
- All operations complete successfully
- Response times remain reasonable (< 1 second each)
- Data integrity maintained across all operations
- Memory usage stable

---

## Test Results Summary

After completing all tests, provide a summary:

**PASS/FAIL Status for each test (1-10)**

**Critical Issues Found** (if any):
- List any test failures with details
- Note any performance concerns
- Identify any security vulnerabilities

**System Health Indicators**:
- Authentication: Working/Broken
- Session Management: Working/Broken
- Memory Isolation: Working/Broken
- Search Functionality: Working/Broken
- Error Handling: Working/Broken
- Concurrency: Working/Broken

**Regression Detection**:
- Are there any new failures compared to previous runs?
- Are response times degraded?
- Any functionality that used to work but now fails?

## Execution Notes

- Run this entire suite whenever making changes to core server functionality
- Each test should complete in under 30 seconds
- Total test suite runtime should be under 5 minutes
- Save test results with timestamps for regression comparison
- If any test fails, investigate before deploying changes

## Emergency Rollback Criteria

Stop testing and rollback if:
- Authentication system fails (Test 1)
- Data corruption detected (messages/memory wrong)
- Server becomes unresponsive
- Memory leaks detected (performance degradation)
- Security vulnerabilities discovered

This script ensures the Shared Context MCP Server maintains reliability and functionality across updates and deployments.
