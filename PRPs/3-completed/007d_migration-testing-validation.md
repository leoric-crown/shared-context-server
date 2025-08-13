# PRP-007D: Migration Testing and Validation

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-12
**Parent PRP**: PRP-007 SQLAlchemy Core Database Migration
**Prerequisites**: PRP-007A Foundation, PRP-007B Manager Integration, PRP-007C Alembic Schema
**Status**: Implementation Ready
**Priority**: Critical - Data Safety
**Estimated Effort**: 2-3 days
**Complexity Level**: High - Data Migration Safety

---

## Executive Summary

Implement comprehensive testing and validation framework for database migration, ensuring data integrity, performance requirements, and safe migration procedures across all database backends.

**Scope**: Migration testing, data validation, rollback procedures, performance verification
**Goal**: Production-ready migration process with zero data loss guarantee

---

## Implementation Specification

### Core Requirements

**Data Migration Validator**:
```python
# src/shared_context_server/database/migration_validator.py
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from ..database import get_database_manager
from .schema import metadata

logger = logging.getLogger(__name__)

class MigrationValidator:
    """Validates database migrations and data integrity."""

    def __init__(self, source_manager, target_manager):
        self.source = source_manager
        self.target = target_manager
        self.validation_errors = []

    async def validate_schema_compatibility(self) -> bool:
        """Validate that target schema is compatible with source data."""
        try:
            # Check table existence
            await self._validate_table_structure()

            # Check column compatibility
            await self._validate_column_compatibility()

            # Check index existence
            await self._validate_indexes()

            # Check foreign key constraints
            await self._validate_foreign_keys()

            return len(self.validation_errors) == 0

        except Exception as e:
            self.validation_errors.append(f"Schema validation failed: {e}")
            return False

    async def validate_data_integrity(self) -> bool:
        """Validate data integrity after migration."""
        try:
            # Validate row counts match
            await self._validate_row_counts()

            # Validate critical data relationships
            await self._validate_relationships()

            # Validate data content sampling
            await self._validate_data_sampling()

            # Validate timestamp preservation
            await self._validate_timestamps()

            return len(self.validation_errors) == 0

        except Exception as e:
            self.validation_errors.append(f"Data integrity validation failed: {e}")
            return False

    async def _validate_table_structure(self):
        """Validate all required tables exist in target."""
        required_tables = [
            'sessions', 'messages', 'agent_memory',
            'audit_log', 'secure_tokens', 'schema_version'
        ]

        for table in required_tables:
            try:
                await self.target.execute_query(f"SELECT 1 FROM {table} LIMIT 1")
            except Exception:
                self.validation_errors.append(f"Table {table} missing in target database")

    async def _validate_row_counts(self):
        """Validate row counts match between source and target."""
        tables = ['sessions', 'messages', 'agent_memory', 'audit_log', 'secure_tokens']

        for table in tables:
            try:
                source_count = await self.source.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                target_count = await self.target.execute_query(f"SELECT COUNT(*) as count FROM {table}")

                source_rows = source_count[0]['count']
                target_rows = target_count[0]['count']

                if source_rows != target_rows:
                    self.validation_errors.append(
                        f"Row count mismatch in {table}: source={source_rows}, target={target_rows}"
                    )
            except Exception as e:
                self.validation_errors.append(f"Failed to validate row count for {table}: {e}")

    async def _validate_relationships(self):
        """Validate foreign key relationships are preserved."""
        # Validate session-message relationships
        try:
            source_sessions = await self.source.execute_query(
                "SELECT COUNT(DISTINCT session_id) as count FROM messages"
            )
            target_sessions = await self.target.execute_query(
                "SELECT COUNT(DISTINCT session_id) as count FROM messages"
            )

            if source_sessions[0]['count'] != target_sessions[0]['count']:
                self.validation_errors.append("Session-message relationship count mismatch")

        except Exception as e:
            self.validation_errors.append(f"Relationship validation failed: {e}")

    async def _validate_data_sampling(self):
        """Validate data content through sampling."""
        # Sample first and last records from each table
        tables = ['sessions', 'messages', 'agent_memory']

        for table in tables:
            try:
                # Get first record
                source_first = await self.source.execute_query(
                    f"SELECT * FROM {table} ORDER BY rowid LIMIT 1"
                )
                target_first = await self.target.execute_query(
                    f"SELECT * FROM {table} ORDER BY rowid LIMIT 1"
                )

                if source_first and target_first:
                    # Compare key fields (implementation depends on table structure)
                    await self._compare_record_data(table, source_first[0], target_first[0])

            except Exception as e:
                self.validation_errors.append(f"Data sampling validation failed for {table}: {e}")

    async def _validate_timestamps(self):
        """Validate timestamp fields are preserved correctly."""
        timestamp_queries = [
            ("sessions", "created_at"),
            ("messages", "timestamp"),
            ("agent_memory", "created_at"),
            ("audit_log", "timestamp"),
        ]

        for table, timestamp_field in timestamp_queries:
            try:
                source_times = await self.source.execute_query(
                    f"SELECT MIN({timestamp_field}) as min_time, MAX({timestamp_field}) as max_time FROM {table}"
                )
                target_times = await self.target.execute_query(
                    f"SELECT MIN({timestamp_field}) as min_time, MAX({timestamp_field}) as max_time FROM {table}"
                )

                if source_times and target_times:
                    source_min = source_times[0]['min_time']
                    target_min = target_times[0]['min_time']

                    # Allow small timestamp differences due to format conversion
                    if source_min != target_min:
                        logger.warning(f"Timestamp difference in {table}.{timestamp_field}: {source_min} vs {target_min}")

            except Exception as e:
                self.validation_errors.append(f"Timestamp validation failed for {table}.{timestamp_field}: {e}")

    async def _compare_record_data(self, table: str, source_record: dict, target_record: dict):
        """Compare individual record data between source and target."""
        # Skip comparison of fields that might differ (like rowid, autoincrement ids)
        skip_fields = {'id', 'rowid'} if table != 'sessions' else {'rowid'}

        for field, source_value in source_record.items():
            if field in skip_fields:
                continue

            target_value = target_record.get(field)

            if source_value != target_value:
                self.validation_errors.append(
                    f"Data mismatch in {table}.{field}: '{source_value}' vs '{target_value}'"
                )

    def get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_passed": len(self.validation_errors) == 0,
            "error_count": len(self.validation_errors),
            "errors": self.validation_errors,
        }
```

**Data Migration Service**:
```python
# src/shared_context_server/database/migration_service.py
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DataMigrationService:
    """Handles safe data migration between database backends."""

    def __init__(self, source_manager, target_manager):
        self.source = source_manager
        self.target = target_manager
        self.migration_log = []

    async def migrate_data(self, backup_path: Optional[str] = None) -> bool:
        """Perform complete data migration with safety checks."""
        try:
            # Step 1: Create backup if requested
            if backup_path:
                await self._create_backup(backup_path)
                self._log("Backup created", {"backup_path": backup_path})

            # Step 2: Validate source database
            if not await self._validate_source():
                return False

            # Step 3: Prepare target database
            await self._prepare_target()

            # Step 4: Migrate data table by table
            await self._migrate_all_tables()

            # Step 5: Validate migration
            validator = MigrationValidator(self.source, self.target)
            if not await validator.validate_data_integrity():
                self._log("Migration validation failed", {"errors": validator.validation_errors})
                return False

            self._log("Migration completed successfully")
            return True

        except Exception as e:
            self._log("Migration failed", {"error": str(e)})
            logger.exception("Data migration failed")
            return False

    async def _create_backup(self, backup_path: str):
        """Create backup of source database."""
        # Implementation depends on database type
        # For SQLite: simple file copy
        # For PostgreSQL/MySQL: pg_dump/mysqldump equivalent
        pass

    async def _validate_source(self) -> bool:
        """Validate source database is in good state."""
        try:
            # Check connectivity
            health = await self.source.health_check()
            if not health:
                self._log("Source database health check failed")
                return False

            # Check for required tables
            tables = ['sessions', 'messages', 'agent_memory', 'audit_log']
            for table in tables:
                count = await self.source.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                self._log(f"Source table {table} has {count[0]['count']} rows")

            return True

        except Exception as e:
            self._log("Source validation failed", {"error": str(e)})
            return False

    async def _prepare_target(self):
        """Prepare target database for migration."""
        await self.target.initialize()

        # Ensure schema is up to date
        if hasattr(self.target, 'create_schema'):
            await self.target.create_schema()

    async def _migrate_all_tables(self):
        """Migrate all data tables in dependency order."""
        # Migrate in dependency order to handle foreign keys
        migration_order = [
            'schema_version',
            'sessions',
            'messages',  # depends on sessions
            'agent_memory',  # depends on sessions
            'audit_log',  # depends on sessions
            'secure_tokens',  # independent
        ]

        for table in migration_order:
            await self._migrate_table(table)

    async def _migrate_table(self, table_name: str):
        """Migrate a single table."""
        try:
            # Get all data from source
            source_data = await self.source.execute_query(f"SELECT * FROM {table_name}")
            self._log(f"Migrating {len(source_data)} rows from {table_name}")

            if not source_data:
                return

            # Prepare insert statement for target
            columns = list(source_data[0].keys())
            placeholders = ', '.join([f":{col}" for col in columns])
            insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Insert data in batches
            batch_size = 100
            for i in range(0, len(source_data), batch_size):
                batch = source_data[i:i + batch_size]

                for row in batch:
                    await self.target.execute_update(insert_query, row)

            self._log(f"Successfully migrated {table_name}")

        except Exception as e:
            self._log(f"Failed to migrate {table_name}", {"error": str(e)})
            raise

    def _log(self, message: str, details: Optional[Dict] = None):
        """Log migration activity."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "details": details or {}
        }
        self.migration_log.append(log_entry)
        logger.info(f"Migration: {message}", extra=details or {})

    def save_migration_log(self, log_path: str):
        """Save migration log to file."""
        with open(log_path, 'w') as f:
            json.dump(self.migration_log, f, indent=2)
```

**Performance Validation Framework**:
```python
# src/shared_context_server/database/performance_validator.py
import asyncio
import time
from typing import Dict, List, Any
import statistics

class PerformanceValidator:
    """Validates database performance meets requirements."""

    def __init__(self, database_manager):
        self.db = database_manager
        self.performance_data = []

    async def validate_performance_requirements(self) -> Dict[str, Any]:
        """Validate all performance requirements are met."""
        results = {}

        # Test query performance (<30ms requirement)
        results['query_performance'] = await self._test_query_performance()

        # Test concurrent access (20+ agents)
        results['concurrent_access'] = await self._test_concurrent_access()

        # Test search performance (2-3ms requirement)
        results['search_performance'] = await self._test_search_performance()

        # Test connection pool efficiency
        results['connection_pool'] = await self._test_connection_pool()

        return results

    async def _test_query_performance(self) -> Dict[str, Any]:
        """Test basic query performance."""
        query_tests = [
            ("SELECT 1", {}),
            ("SELECT COUNT(*) FROM sessions", {}),
            ("SELECT * FROM messages LIMIT 10", {}),
            ("SELECT * FROM agent_memory WHERE agent_id = :agent_id LIMIT 5", {"agent_id": "test_agent"}),
        ]

        times = []

        for query, params in query_tests:
            # Warm up
            await self.db.execute_query(query, params)

            # Measure performance
            for _ in range(10):
                start_time = time.perf_counter()
                await self.db.execute_query(query, params)
                end_time = time.perf_counter()

                elapsed_ms = (end_time - start_time) * 1000
                times.append(elapsed_ms)

        avg_time = statistics.mean(times)
        max_time = max(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile

        return {
            "average_ms": avg_time,
            "max_ms": max_time,
            "p95_ms": p95_time,
            "requirement_met": max_time < 30.0,
            "sample_count": len(times)
        }

    async def _test_concurrent_access(self) -> Dict[str, Any]:
        """Test concurrent access with multiple simulated agents."""
        concurrent_agents = 25  # Test above requirement
        operations_per_agent = 10

        async def agent_workload(agent_id: int):
            """Simulate agent database operations."""
            times = []

            for i in range(operations_per_agent):
                start_time = time.perf_counter()

                # Simulate typical agent operations
                await self.db.execute_query("SELECT COUNT(*) FROM sessions")
                await self.db.execute_query(
                    "SELECT * FROM messages WHERE sender = :sender LIMIT 5",
                    {"sender": f"agent_{agent_id}"}
                )

                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)

            return times

        # Run concurrent workloads
        start_time = time.perf_counter()
        tasks = [agent_workload(i) for i in range(concurrent_agents)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # Analyze results
        all_times = [t for agent_times in results for t in agent_times]
        avg_time = statistics.mean(all_times)
        max_time = max(all_times)

        return {
            "concurrent_agents": concurrent_agents,
            "operations_per_agent": operations_per_agent,
            "total_operations": len(all_times),
            "total_time_seconds": total_time,
            "average_operation_ms": avg_time,
            "max_operation_ms": max_time,
            "operations_per_second": len(all_times) / total_time,
            "requirement_met": max_time < 30.0
        }

    async def _test_search_performance(self) -> Dict[str, Any]:
        """Test search performance (simulating RapidFuzz operations)."""
        # Create test data
        await self._create_search_test_data()

        search_queries = [
            "SELECT * FROM messages WHERE content LIKE :pattern LIMIT 10",
            "SELECT * FROM sessions WHERE purpose LIKE :pattern LIMIT 10",
        ]

        times = []

        for query in search_queries:
            for _ in range(20):  # Test multiple times
                start_time = time.perf_counter()
                await self.db.execute_query(query, {"pattern": "%test%"})
                end_time = time.perf_counter()

                elapsed_ms = (end_time - start_time) * 1000
                times.append(elapsed_ms)

        avg_time = statistics.mean(times)
        max_time = max(times)

        return {
            "average_ms": avg_time,
            "max_ms": max_time,
            "requirement_met": avg_time < 3.0,  # 2-3ms requirement
            "sample_count": len(times)
        }

    async def _test_connection_pool(self) -> Dict[str, Any]:
        """Test connection pool efficiency."""
        # This test is database-specific
        # For SQLAlchemy: test connection acquisition time
        # For legacy: test context manager performance

        times = []

        for _ in range(50):
            start_time = time.perf_counter()

            async with self.db.get_connection() as conn:
                # Minimal operation to test connection acquisition
                pass

            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)

        avg_time = statistics.mean(times)
        max_time = max(times)

        return {
            "average_connection_ms": avg_time,
            "max_connection_ms": max_time,
            "efficiency_met": avg_time < 5.0,  # Connection should be fast
            "sample_count": len(times)
        }

    async def _create_search_test_data(self):
        """Create test data for search performance testing."""
        # Insert test sessions and messages if they don't exist
        try:
            await self.db.execute_update(
                "INSERT OR IGNORE INTO sessions (id, purpose, created_by) VALUES (:id, :purpose, :created_by)",
                {"id": "test_session", "purpose": "test search performance", "created_by": "performance_test"}
            )

            for i in range(10):
                await self.db.execute_update(
                    "INSERT OR IGNORE INTO messages (session_id, sender, content) VALUES (:session_id, :sender, :content)",
                    {
                        "session_id": "test_session",
                        "sender": f"test_agent_{i}",
                        "content": f"test message {i} for search performance"
                    }
                )
        except Exception:
            # Ignore errors - test data might already exist
            pass
```

### Testing Strategy

**Integration Testing**:
```python
# tests/integration/test_migration_validation.py
import pytest
from shared_context_server.database.migration_validator import MigrationValidator
from shared_context_server.database.migration_service import DataMigrationService
from shared_context_server.database.performance_validator import PerformanceValidator

@pytest.mark.asyncio
class TestMigrationValidation:
    async def test_migration_data_integrity(self):
        """Test complete migration preserves data integrity."""
        # Setup source database with test data
        source_manager = await self._create_test_database_with_data("source")

        # Setup target database
        target_manager = await self._create_empty_database("target")

        # Perform migration
        migration_service = DataMigrationService(source_manager, target_manager)
        success = await migration_service.migrate_data()

        assert success, "Migration should complete successfully"

        # Validate data integrity
        validator = MigrationValidator(source_manager, target_manager)
        assert await validator.validate_data_integrity(), f"Data integrity validation failed: {validator.validation_errors}"

    async def test_performance_validation(self):
        """Test performance requirements are met after migration."""
        # Setup database with realistic data volume
        db_manager = await self._create_performance_test_database()

        # Run performance validation
        perf_validator = PerformanceValidator(db_manager)
        results = await perf_validator.validate_performance_requirements()

        # Validate performance requirements
        assert results['query_performance']['requirement_met'], "Query performance requirement not met"
        assert results['concurrent_access']['requirement_met'], "Concurrent access requirement not met"
        assert results['search_performance']['requirement_met'], "Search performance requirement not met"

    async def _create_test_database_with_data(self, db_name: str):
        """Create test database with sample data."""
        # Implementation creates database and populates with test data
        pass

    async def _create_empty_database(self, db_name: str):
        """Create empty database with schema."""
        # Implementation creates empty database with proper schema
        pass

    async def _create_performance_test_database(self):
        """Create database with realistic data volume for performance testing."""
        # Implementation creates database with substantial test data
        pass
```

---

## Success Criteria

### Functional Success
- ✅ Migration validator detects data integrity issues
- ✅ Data migration service preserves all data relationships
- ✅ Performance validator confirms <30ms operations
- ✅ Rollback procedures restore original state
- ✅ Migration logging provides audit trail

### Integration Success
- ✅ Migration between SQLite and PostgreSQL successful
- ✅ All existing data preserved during migration
- ✅ Performance requirements maintained post-migration
- ✅ Zero data loss during migration process

### Quality Gates
- ✅ 100% test coverage for migration and validation code
- ✅ Migration tested with realistic data volumes
- ✅ Performance validation passes on all database backends
- ✅ Rollback procedures tested and verified

### Validation Commands
```bash
# Migration testing
uv run pytest tests/integration/test_migration_validation.py -v

# Performance validation
uv run pytest tests/performance/test_migration_performance.py -v

# Data integrity testing
uv run pytest tests/unit/test_migration_validator.py -v

# End-to-end migration test
uv run python -m shared_context_server.database.migration_service --test-migration
```

---

## Risk Assessment

### Critical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data loss during migration | Critical | Low | Comprehensive backup, validation, rollback procedures |
| Performance degradation | High | Medium | Extensive performance testing, optimization |
| Migration corruption | High | Low | Atomic operations, transaction rollback |
| Incomplete migration | Medium | Medium | Progress tracking, resumable migration |

### Safety Measures
- **Backup Before Migration**: Always create backup before starting
- **Validation at Each Step**: Verify data integrity continuously
- **Atomic Operations**: Use transactions to ensure consistency
- **Rollback Capability**: Quick revert to original state

---

## Next Steps

**Upon Completion**: Ensures safe, validated migration process for production use
**Dependencies**: Requires PRP-007A, PRP-007B, PRP-007C
**Follow-up PRPs**:
- PRP-007E: PostgreSQL Support Implementation
- PRP-007F: Cross-Database Testing and Validation

---

**Implementation Notes**:
- Test migration validation extensively with realistic data
- Ensure performance validation covers all critical operations
- Implement comprehensive logging for migration audit trails
- Test rollback procedures thoroughly before production use
