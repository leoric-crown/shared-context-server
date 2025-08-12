# E2E Regression Testing Script for Shared Context Server

This script is designed to be executed by an LLM to automatically test the server functionality. Execute each step in order and verify the expected results.

## Prerequisites
- Server is running and accessible
- LLM has access to shared-context-server tools
- Authentication is properly configured

## Important Testing Guidelines
- **Use authentication tokens**: Always pass auth_token parameter when available for proper identification
- **Validate responses**: Check not just success=true but actual data structure and values
- **Save test data**: Keep track of tokens, session_ids, memory keys throughout test execution
- **Time operations**: Note response times - flag any operation taking >2 seconds
- **Check data isolation**: Verify agents can only see data they should have access to

## Test Suite: Core Functionality Regression

### Test 1: Authentication System
**Goal**: Verify authentication system is working

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
- Agent_id matches input exactly
- Permissions: ["read", "write"]

**Critical Validations**:
- Token format looks correct (starts with "sct_")
- Expiration time is reasonable (about 1 hour)
- Store this token for use in subsequent tests
- Response includes all expected fields

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
- Session created successfully with session_id
- Session retrieval shows correct purpose and created_by
- Created_at timestamp is recent (within last minute)

**Critical Validations**:
- Session_id is a reasonable format
- Created_by field is populated
- Created_at shows recent time
- Store session_id for use in subsequent tests

---

### Test 3: Message Storage and Retrieval
**Goal**: Test message operations with visibility controls

**Execute**:
```
Using the session_id from Test 2 and auth_token from Test 1:

1. Add a public message:
   - content: "Public message for regression test"
   - visibility: "public"
   - auth_token: <token from Test 1>

2. Add a private message:
   - content: "Private message for regression test"
   - visibility: "private"
   - auth_token: <token from Test 1>

3. Add an agent-only message:
   - content: "Agent-only message for regression test"
   - visibility: "agent_only"
   - auth_token: <token from Test 1>

4. Get messages from the session (limit: 10, auth_token: <token from Test 1>)
```

**Expected Result**:
- All 3 messages stored successfully with sequential message_ids
- get_messages returns all 3 messages (agent can see all visibility types)
- Messages have correct timestamps, sender, and content
- Visibility fields match what was sent

**Critical Validations**:
- Sender field shows "test_regression_agent" (correct agent identification)
- Message IDs are sequential numbers
- Timestamps are recent and properly formatted
- All 3 messages returned (sender should see all their own messages)
- Test visibility filtering by using get_messages with visibility_filter parameter

---

### Test 4: Agent Memory Operations
**Goal**: Test private memory storage with session and global scopes

**Execute**:
```
Using the auth_token from Test 1:

1. Set session-scoped memory:
   - key: "regression_test_session"
   - value: {"test": "session_memory", "timestamp": current_timestamp}
   - session_id: use from Test 2
   - auth_token: <token from Test 1>

2. Set global memory:
   - key: "regression_test_global"
   - value: {"test": "global_memory", "shared": true}
   - (no session_id for global)
   - auth_token: <token from Test 1>

3. Retrieve session memory using key and session_id with auth_token
4. Retrieve global memory using key only with auth_token
5. List memory entries (should show both) with auth_token
```

**Expected Result**:
- Session memory stored and retrievable only with correct session_id
- Global memory stored and retrievable without session_id
- Both memories contain exact JSON values that were stored
- List shows both entries with correct scopes

**Critical Validations**:
- Data preservation: values retrieved exactly match what was stored
- Session memory requires session_id for retrieval
- Global memory accessible without session_id
- Memory keys are stored correctly
- List memory shows both entries with proper organization

---

### Test 5: Memory Isolation Testing
**Goal**: Verify session memory isolation between different sessions

**Execute**:
```
Using the auth_token from Test 1:

1. Create a second session: purpose "Isolation test session"
2. In new session, try to get memory key "regression_test_session" (should fail)
3. In new session, try to get global memory "regression_test_global" (should succeed)
4. Set new session memory in second session:
   - key: "regression_test_session" (same key, different session)
   - value: {"test": "different_session", "isolated": true}
   - session_id: second session ID
   - auth_token: <token from Test 1>
5. Verify first session still has original session memory
```

**Expected Result**:
- Session memory from first session is NOT accessible from second session
- Global memory IS accessible from second session
- Each session can have same key with different values (isolation working)
- Original session memory unchanged

**Critical Validations**:
- Memory isolation: session memory cannot be accessed from different sessions
- Global memory sharing: same global memory available across sessions
- Separate storage: same key in different sessions stores different values
- Data protection: original session memory unchanged after isolation test

---

### Test 6: Search Functionality
**Goal**: Test fuzzy search across messages

**Execute**:
```
Using the session from Test 2 and auth_token from Test 1:
1. Search for "regression" in the session
2. Search for "private" in the session
3. Search for "nonexistent" in the session
4. Test fuzzy search with "regresion" (typo)
```

**Expected Result**:
- "regression" search returns multiple messages (all 3 contain this word)
- "private" search returns the private message
- "nonexistent" search returns empty results
- All results include similarity scores and proper message data

**Critical Validations**:
- Search results include similarity scores
- Message data in results looks correct
- Search shows appropriate messages based on access rules
- Fuzzy search handles typos reasonably well
- Search completes quickly (under 1 second)

---

### Test 7: Cleanup and TTL Testing
**Goal**: Test memory expiration and cleanup

**Execute**:
```
Using auth_token from Test 1:

1. Set memory with short TTL:
   - key: "ttl_test"
   - value: {"expires": "soon"}
   - expires_in: "5" (5 seconds - test string conversion)
   - auth_token: <token from Test 1>

2. Immediately retrieve the memory (should work)
3. Wait 6 seconds
4. Try to retrieve the memory again (should fail)
5. Test TTL edge case with expires_in: 0 (should mean no expiration)
```

**Expected Result**:
- Memory stored successfully with expiration
- Immediate retrieval works
- After expiration, retrieval fails with "MEMORY_NOT_FOUND"
- TTL system working correctly

**Critical Validations**:
- TTL accepts both number and text values ("5" vs 5)
- expires_in: 0 creates permanent memory (no expiration)
- Error messages are appropriate when memory expires
- Timing works correctly: memory expires close to expected time
- Different TTL formats work properly

---

### Test 8: Error Handling and Edge Cases
**Goal**: Test system resilience and error responses

**Execute**:
```
1. Try to get session with invalid session_id: "invalid_session"
2. Try to get memory with non-existent key: "does_not_exist"
3. Try to add message to non-existent session: "invalid_session"
4. Try to create session with empty purpose: ""
5. Test invalid visibility levels: "invalid_visibility"
6. Test malformed authentication token: "invalid.token"
7. Test expired/invalid tokens
```

**Expected Result**:
- All operations fail gracefully with proper error codes
- Error messages are descriptive and include suggestions
- No server crashes or unexpected responses
- Error structure includes: success=false, error, code, severity

**Critical Validations**:
- Error response format is consistent across all operations
- Error codes are meaningful and clear
- Error messages are helpful and descriptive
- No sensitive data leaked in error messages
- Server remains stable after error conditions
- System handles invalid requests gracefully

---

### Test 9: Concurrent Operations Simulation
**Goal**: Test multi-agent scenario simulation

**Execute**:
```
1. Authenticate a second agent:
   - agent_id: "concurrent_test_agent"
   - agent_type: "gemini"
   - Store this token as agent2_token

2. Have both agents add messages to the same session rapidly:
   - Agent 1 (Test 1 token): "Message from agent 1 - test 1" (auth_token: agent1_token)
   - Agent 2 (new token): "Message from agent 2 - test 1" (auth_token: agent2_token)
   - Agent 1: "Message from agent 1 - test 2" (auth_token: agent1_token)
   - Agent 2: "Message from agent 2 - test 2" (auth_token: agent2_token)

3. Retrieve all messages and verify ordering with each agent's token
4. Test cross-agent message visibility (agent1 vs agent2 private messages)
```

**Expected Result**:
- Both agents authenticated with different tokens
- All messages stored successfully without conflicts
- Messages have proper sender attribution
- No database locking or concurrency issues

**Critical Validations**:
- Sender attribution: messages show correct agent names ("test_regression_agent" vs "concurrent_test_agent")
- Token uniqueness: each agent gets different authentication tokens
- Message ordering: timestamps show proper sequence
- Privacy rules: private messages only visible to the sender
- No conflicts: messages don't get mixed up or lost
- Performance: operations remain fast with multiple agents

---

### Test 10: Performance and Scale Testing
**Goal**: Test system under moderate load

**Execute**:
```
Using auth_token from Test 1:

1. Create 5 sessions with different purposes ("Scale test 1", "Scale test 2", etc.)
2. Add 10 messages to each session (50 total messages) with auth_token
3. Set 10 memory entries (mix of session and global) with auth_token
4. Search across all sessions for common term "scale"
5. Retrieve all sessions and verify data integrity
6. Measure response times for each operation type
7. Test list_memory performance with larger dataset
```

**Expected Result**:
- All operations complete successfully
- Response times remain reasonable (< 1 second each)
- Data integrity maintained across all operations
- Memory usage stable

**Critical Validations**:
- Performance benchmarks:
  * Session creation: under 1 second each
  * Message addition: under 1 second each
  * Memory operations: under 1 second each
  * Search operations: under 1 second each
- Data accuracy: all created data retrievable and correct
- Proper isolation: data stays separated across sessions
- Reasonable scale: performance doesn't degrade significantly with more data
- System stability: no crashes or major slowdowns
- Consistent behavior: operations work the same way under load

---

## Test Results Summary

After completing all tests, provide a comprehensive summary:

**PASS/FAIL Status for each test (1-10)**
```
Test 1 (Authentication): PASS/FAIL - [details if failed]
Test 2 (Session Management): PASS/FAIL - [details if failed]
Test 3 (Message Operations): PASS/FAIL - [details if failed]
Test 4 (Agent Memory): PASS/FAIL - [details if failed]
Test 5 (Memory Isolation): PASS/FAIL - [details if failed]
Test 6 (Search Functionality): PASS/FAIL - [details if failed]
Test 7 (TTL Testing): PASS/FAIL - [details if failed]
Test 8 (Error Handling): PASS/FAIL - [details if failed]
Test 9 (Concurrency): PASS/FAIL - [details if failed]
Test 10 (Performance): PASS/FAIL - [details if failed]
```

**Critical Issues Found** (if any):
- List any test failures with specific error details
- Note any performance degradation (response times >expected)
- Identify any security vulnerabilities or data leaks
- Authentication or authorization bypasses
- Data corruption or inconsistencies

**System Health Indicators**:
- Authentication: ✅/❌ - Token generation and validation system
- Session Management: ✅/❌ - Session creation, retrieval, isolation
- Memory System: ✅/❌ - Data storage and isolation between agents/sessions
- Search Functionality: ✅/❌ - Search with proper access controls
- Error Handling: ✅/❌ - Graceful failures with clear error messages
- Multi-Agent Support: ✅/❌ - Multiple agents working without conflicts

**Performance Metrics** (if measured):
- Average session creation time: [ms]
- Average message addition time: [ms]
- Average memory operation time: [ms]
- Average search time: [ms]
- Total test suite runtime: [minutes:seconds]

**Regression Detection**:
- New failures compared to previous runs?
- Response time degradation since last test?
- Features that previously worked but now fail?
- Changes in error message format or codes?

**Data Validation Results**:
- Authentication token format: ✅/❌
- Message sender identification: ✅/❌
- Message visibility controls: ✅/❌
- Memory isolation between agents/sessions: ✅/❌
- Memory expiration timing: ✅/❌

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
