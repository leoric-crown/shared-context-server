# Run E2E Regression Testing

This command provides the prompt for running comprehensive end-to-end regression testing on the Shared Context MCP Server.

## Testing Script: $ARGUMENTS

## Prompt

You are a QA automation specialist tasked with running comprehensive end-to-end regression testing on the Shared Context MCP Server. Your goal is to systematically validate all core functionality and detect any regressions.

**Context**: You have access to MCP tools for a shared context server that enables multi-agent collaboration with secure token authentication, session management, message storage, and agent memory systems.

**Your Task**: Execute the complete regression test suite located at `tests/e2e-llm-regression-test.md` following these guidelines:

### Execution Instructions

1. **Read the Test Script**: First, read the complete test script(s)

2. **Execute Systematically**: Run each test in sequential order:
   - Follow the exact tool calls specified
   - Validate expected results after each step
   - Record pass/fail status for each test
   - If a test fails, note the failure details but continue with remaining tests

3. **Data Validation**: For each test, carefully verify:
   - Response structure matches expected format
   - Data values are correct (IDs, timestamps, content)
   - Error handling works as specified
   - Security features are functioning (token format, isolation)

4. **Performance Monitoring**: Track response times and note any:
   - Unusually slow responses (>2 seconds)
   - Memory usage concerns
   - System instability

5. **Report Results**: After completing all tests, provide a comprehensive summary:
   ```
   # E2E Regression Test Results

   **Execution Date**: [timestamp]
   **Total Tests**: N
   **Passed**: [number]
   **Failed**: [number]

   ## Test Results Detail
   - Test 1 (Authentication): PASS/FAIL [details if failed]
   - Test 2 (Session Management): PASS/FAIL [details if failed]
   - Test 3 (Message Operations): PASS/FAIL [details if failed]
   ...
   - Test 10 (Performance Testing): PASS/FAIL [details if failed]

   ## Critical Issues
   [List any failures that would require immediate attention]

   ## System Health Status
   - Authentication System: ✅/❌
   - Data Integrity: ✅/❌
   - Memory Isolation: ✅/❌
   - Performance: ✅/❌
   - Error Handling: ✅/❌

   ## Regression Assessment
   [Any new issues or performance degradation compared to expected baseline]

   ## Recommendations
   [Next steps based on test results]
   ```

### Important Notes

- **Execute Don't Simulate**: Actually call the MCP tools - don't just describe what you would do
- **Save Test Data**: Keep track of session IDs, memory keys, and other data between tests
- **Validate Thoroughly**: Don't just check for success=true, validate the actual data returned
- **Report Honestly**: Mark tests as FAIL if results don't match expectations, even partially
- **Stop if Critical**: If authentication (Test 1) fails, note it and assess if other tests can run

### Quality Standards

- Each test should complete within 30 seconds
- All security features must pass (token format, memory isolation)
- Data integrity must be maintained throughout
- Error handling must be graceful and informative

**Begin by reading the test script(s) and then execute all tests sequentially. Work through each test methodically, validating results at each step.**

### Focused Summary for Issue Resolution

After providing the comprehensive report above, include this additional focused summary to enable effective debugging:

```
# Issue Resolution Summary

## Critical Path Analysis
[For each failure, trace the exact sequence of steps that led to the issue]

## Context & Evidence Package
**Test Data Used**:
- Session IDs: [list all session IDs created/used]
- Agent Tokens: [list token formats - redacted values but show structure]
- Memory Keys: [all memory keys that were set/retrieved]
- Message IDs: [specific message IDs that failed]

**Exact Error Messages**:
```
[Copy/paste exact error responses, stack traces, or unexpected outputs]
```

**System State at Failure**:
- Server logs/status at time of failure
- Database state (number of sessions, messages, memory entries)
- Performance metrics (response times, memory usage)

## Minimal Reproduction Steps
[For each failed test, provide the shortest possible sequence of tool calls to reproduce the issue]

1. Test X Failure Reproduction:
   - Step 1: [exact tool call with parameters]
   - Step 2: [exact tool call with parameters]
   - Expected: [what should happen]
   - Actual: [what actually happened]

## Environment Snapshot
- Test execution timestamp: [when tests ran]
- System load/performance during tests
- Any external factors that may have influenced results

## Targeted Fix Recommendations
[Based on the evidence collected, provide specific actionable guidance]

**Priority 1 - Critical Issues**:
- [Specific issue] → [Exact location to investigate] → [Suggested fix approach]

**Priority 2 - Data/Logic Issues**:
- [Specific issue] → [Exact location to investigate] → [Suggested fix approach]

**Priority 3 - Performance/UX Issues**:
- [Specific issue] → [Exact location to investigate] → [Suggested fix approach]
```

This focused summary should provide all necessary context and evidence for developers to quickly understand, reproduce, and resolve any issues found during regression testing.

Are you ready to begin the regression testing? Start by reading the test script file(s).

## Exploratory Testing Session

After completing all structured regression tests, conduct an exploratory testing session to identify potential edge cases or unexpected behaviors:

### Manual Exploration Phase (15-20 minutes)

1. **Edge Case Discovery**: Try unusual combinations or boundary conditions not covered in the formal tests:
   - Very long session names or message content (test limits)
   - Special characters in session IDs, memory keys, or content
   - Concurrent operations (rapid sequential requests)
   - Invalid but plausible data formats
   - Boundary values (empty strings, null values, very large numbers)

2. **Workflow Variations**: Test non-standard usage patterns:
   - Creating sessions but never adding messages
   - Adding messages to non-existent sessions
   - Retrieving data immediately after creation (timing issues)
   - Mixed agent types in single sessions
   - Overlapping memory keys across sessions

3. **System Behavior Probing**: Look for unexpected system responses:
   - Monitor for memory leaks during extended operations
   - Test error recovery after invalid operations
   - Check for data corruption with rapid operations
   - Verify cleanup behavior after failed operations

4. **User Experience Edge Cases**: Consider real-world usage scenarios:
   - What happens with network timeouts?
   - How does the system behave under load?
   - Are error messages helpful for debugging?
   - Do successful operations provide sufficient feedback?

### Exploratory Testing Report

Document any unexpected findings:

```
## Exploratory Testing Results

**Duration**: [time spent]
**Focus Areas**: [list areas explored]

### Unexpected Behaviors Found
- **Issue**: [description of unexpected behavior]
  - **Steps**: [how to reproduce]
  - **Impact**: [severity and potential user impact]
  - **Recommendation**: [suggested investigation or fix]

### Edge Cases Identified
- **Scenario**: [description of edge case]
  - **Current Behavior**: [what happens now]
  - **Expected/Desired**: [what should happen or needs clarification]

### System Resilience Observations
- **Strengths**: [areas where system handled edge cases well]
- **Vulnerabilities**: [areas that may need additional protection]

### Recommendations for Test Coverage
[Suggest additional formal tests based on exploratory findings]
```

**Note**: This exploratory phase is designed to complement the structured regression tests by discovering issues that formal test cases might miss. Focus on creative, real-world usage patterns and edge conditions that could reveal system weaknesses or user experience issues.
