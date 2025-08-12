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

Are you ready to begin the regression testing? Start by reading the test script file(s).
