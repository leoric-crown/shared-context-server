# CI Environment Testing

## SQLite In-Memory Database Limitations

### Issue
CI environments use in-memory SQLite databases (`sqlite:///:memory:`) which have concurrency limitations:
- No WAL (Write-Ahead Logging) mode support
- Limited concurrent transaction handling
- "cannot commit transaction - SQL statements in progress" errors

### Current Solutions
- **Reduce concurrency**: Use fewer parallel operations in CI (e.g., 3 vs 10 agents)
- **Batch execution**: Process operations in smaller batches (2 at a time)
- **CI detection**: Use `_is_ci_environment()` to adapt test behavior

### Example Implementation
```python
from shared_context_server.database import _is_ci_environment

# Reduce concurrency in CI environments
agent_count = 3 if _is_ci_environment() else 10

if _is_ci_environment():
    # Process in batches to avoid SQLite concurrency issues
    results = []
    for i in range(0, len(tasks), 2):
        batch = tasks[i:i+2]
        batch_results = await asyncio.gather(*batch)
        results.extend(batch_results)
else:
    results = await asyncio.gather(*tasks)
```

## Future Improvements
- **Dedicated test database**: Use PostgreSQL test instance in CI
- **Better isolation**: Separate database per test worker
- **Connection pooling**: Optimize database connections for CI workloads
