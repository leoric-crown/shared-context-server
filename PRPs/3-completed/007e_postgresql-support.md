# PRP-007E: PostgreSQL Production Support

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-12
**Parent PRP**: PRP-007 SQLAlchemy Core Database Migration
**Prerequisites**: PRP-007A through PRP-007D completed
**Status**: Implementation Ready
**Priority**: High - Production Database Backend
**Estimated Effort**: 2-3 days
**Complexity Level**: Medium - Database-Specific Implementation

---

## Executive Summary

Implement production-ready PostgreSQL support with database-specific optimizations, connection pooling, and performance tuning for multi-agent concurrent access patterns.

**Scope**: PostgreSQL backend configuration, optimization, production deployment
**Goal**: Production-ready PostgreSQL support with performance parity to SQLite

---

## Implementation Specification

### Core Requirements

**PostgreSQL Connection Manager**:
```python
# src/shared_context_server/database/postgresql_manager.py
import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)

class PostgreSQLManager:
    """Optimized PostgreSQL connection manager for multi-agent workloads."""

    def __init__(self, database_url: str, **kwargs):
        self.database_url = database_url
        self.engine_kwargs = self._get_postgresql_config(**kwargs)
        self.engine = create_async_engine(database_url, **self.engine_kwargs)
        self._connection_pool = None

    def _get_postgresql_config(self, **kwargs) -> Dict[str, Any]:
        """Get PostgreSQL-specific engine configuration."""
        config = {
            # Connection pooling for multi-agent access
            'pool_size': kwargs.get('pool_size', 20),
            'max_overflow': kwargs.get('max_overflow', 10),
            'pool_timeout': kwargs.get('pool_timeout', 30.0),
            'pool_recycle': kwargs.get('pool_recycle', 3600),  # 1 hour
            'pool_pre_ping': True,

            # Performance optimizations
            'echo': kwargs.get('enable_query_logging', False),
            'echo_pool': kwargs.get('enable_pool_logging', False),

            # PostgreSQL-specific connection args
            'connect_args': {
                'server_settings': {
                    # Connection-level optimizations
                    'application_name': 'shared_context_server',
                    'search_path': 'shared_context,public',

                    # Performance settings
                    'statement_timeout': '30s',
                    'idle_in_transaction_session_timeout': '60s',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3',
                },
                # Connection timeout
                'timeout': 30,
            },

            # Async-specific settings
            'isolation_level': 'AUTOCOMMIT',  # For better performance with SQLAlchemy Core
        }

        return config

    async def initialize(self):
        """Initialize PostgreSQL connection and apply optimizations."""
        try:
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            # Apply PostgreSQL-specific optimizations
            await self._apply_postgresql_optimizations()

            logger.info("PostgreSQL connection initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {e}")
            raise

    async def _apply_postgresql_optimizations(self):
        """Apply PostgreSQL-specific optimizations."""
        optimizations = [
            # Memory settings (session-level where possible)
            "SET work_mem = '16MB'",  # For complex queries
            "SET maintenance_work_mem = '64MB',  # For maintenance operations

            # Query planning optimizations
            "SET random_page_cost = 1.1",  # Assume SSD storage
            "SET effective_cache_size = '1GB'",  # Adjust based on system

            # Connection-specific settings
            "SET synchronous_commit = 'on'",  # Data safety
            "SET wal_buffers = '16MB'",

            # Concurrency settings for multi-agent access
            "SET max_connections = 100",  # Adjust based on expected load
            "SET shared_buffers = '256MB'",  # Adjust based on system memory
        ]

        try:
            async with self.engine.begin() as conn:
                for setting in optimizations:
                    try:
                        await conn.execute(text(setting))
                    except Exception as e:
                        # Some settings may require superuser or server restart
                        logger.warning(f"Could not apply PostgreSQL setting '{setting}': {e}")

            logger.info("PostgreSQL optimizations applied")

        except Exception as e:
            logger.error(f"Failed to apply PostgreSQL optimizations: {e}")

    @asynccontextmanager
    async def get_connection(self):
        """Get PostgreSQL connection with automatic cleanup."""
        async with self.engine.begin() as conn:
            # Apply session-specific optimizations
            await conn.execute(text("SET statement_timeout = '30s'"))
            await conn.execute(text("SET idle_in_transaction_session_timeout = '60s'"))
            yield conn

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query with PostgreSQL optimizations."""
        async with self.get_connection() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    async def execute_update(self, query: str, params: Optional[Dict] = None) -> int:
        """Execute INSERT/UPDATE/DELETE with PostgreSQL optimizations."""
        async with self.get_connection() as conn:
            result = await conn.execute(text(query), params or {})
            return result.rowcount

    async def execute_batch(self, query: str, params_list: List[Dict]) -> int:
        """Execute batch operations efficiently."""
        total_affected = 0

        async with self.get_connection() as conn:
            # Use PostgreSQL's efficient batch processing
            for params in params_list:
                result = await conn.execute(text(query), params)
                total_affected += result.rowcount

        return total_affected

    async def health_check(self) -> Dict[str, Any]:
        """PostgreSQL-specific health check."""
        try:
            async with self.get_connection() as conn:
                # Basic connectivity
                result = await conn.execute(text("SELECT 1 as test"))
                basic_check = list(result)[0][0] == 1

                # Connection pool status
                pool_status = {
                    "pool_size": self.engine.pool.size(),
                    "checked_in": self.engine.pool.checkedin(),
                    "checked_out": self.engine.pool.checkedout(),
                    "overflow": self.engine.pool.overflow(),
                }

                # Database-specific metrics
                db_metrics = await self._get_database_metrics(conn)

                return {
                    "status": "healthy" if basic_check else "unhealthy",
                    "backend": "postgresql",
                    "database_url": self.database_url.replace(
                        self.database_url.split('@')[0].split('://')[-1] + '@',
                        '***@'
                    ),  # Hide credentials
                    "connection_pool": pool_status,
                    "database_metrics": db_metrics,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "postgresql",
                "error": str(e)
            }

    async def _get_database_metrics(self, conn) -> Dict[str, Any]:
        """Get PostgreSQL-specific database metrics."""
        try:
            # Connection count
            conn_result = await conn.execute(text(
                "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active'"
            ))
            active_connections = list(conn_result)[0][0]

            # Database size
            size_result = await conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database())) as db_size"
            ))
            db_size = list(size_result)[0][0]

            # Table sizes for monitoring
            table_sizes_result = await conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 5
            """))
            table_sizes = [dict(row._mapping) for row in table_sizes_result]

            return {
                "active_connections": active_connections,
                "database_size": db_size,
                "largest_tables": table_sizes,
            }

        except Exception as e:
            logger.warning(f"Could not fetch PostgreSQL metrics: {e}")
            return {"error": str(e)}

    async def cleanup(self):
        """Cleanup PostgreSQL connections."""
        if self.engine:
            await self.engine.dispose()
        logger.info("PostgreSQL connections cleaned up")
```

**PostgreSQL Schema Optimizations**:
```python
# src/shared_context_server/database/postgresql_schema.py
from sqlalchemy import Table, Column, Integer, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .schema import metadata

def create_postgresql_optimized_schema():
    """Create PostgreSQL-optimized schema with native features."""

    # Use PostgreSQL-specific types for better performance
    sessions_pg = Table(
        'sessions',
        metadata,
        Column('id', Text, primary_key=True),  # Could use UUID type
        Column('purpose', Text, nullable=False),
        Column('created_at', DateTime(timezone=True), server_default=func.now()),
        Column('updated_at', DateTime(timezone=True), server_default=func.now()),
        Column('is_active', Boolean, server_default='true'),
        Column('created_by', Text, nullable=False),
        Column('metadata', JSONB),  # Native JSON support
    )

    messages_pg = Table(
        'messages',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('session_id', Text, nullable=False),
        Column('sender', Text, nullable=False),
        Column('sender_type', Text, server_default='generic'),
        Column('content', Text, nullable=False),
        Column('visibility', Text, server_default='public'),
        Column('message_type', Text, server_default='agent_response'),
        Column('metadata', JSONB),  # Native JSON support
        Column('timestamp', DateTime(timezone=True), server_default=func.now()),
        Column('parent_message_id', Integer),
    )

    # PostgreSQL-specific indexes for better performance
    # GIN indexes for JSON searching
    Index('idx_sessions_metadata_gin', sessions_pg.c.metadata, postgresql_using='gin')
    Index('idx_messages_metadata_gin', messages_pg.c.metadata, postgresql_using='gin')

    # Partial indexes for active sessions
    Index('idx_sessions_active_partial', sessions_pg.c.id,
          postgresql_where=sessions_pg.c.is_active == True)

    # Covering indexes for common queries
    Index('idx_messages_session_timestamp_covering',
          messages_pg.c.session_id, messages_pg.c.timestamp, messages_pg.c.id)

    return metadata
```

**PostgreSQL-Specific Configuration**:
```python
# src/shared_context_server/config.py (additions)
class PostgreSQLConfig(BaseModel):
    """PostgreSQL-specific configuration."""

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="shared_context", description="Database name")
    username: str = Field(description="Database username")
    password: str = Field(description="Database password")

    # Connection pool settings
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    pool_timeout: float = Field(default=30.0, description="Pool timeout seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time seconds")

    # SSL settings
    ssl_mode: str = Field(default="prefer", description="SSL mode (disable, allow, prefer, require)")
    ssl_cert: Optional[str] = Field(default=None, description="SSL certificate file")
    ssl_key: Optional[str] = Field(default=None, description="SSL key file")
    ssl_ca: Optional[str] = Field(default=None, description="SSL CA file")

    # Performance settings
    application_name: str = Field(default="shared_context_server", description="Application name")
    search_path: str = Field(default="shared_context,public", description="Schema search path")

    @property
    def connection_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        auth = f"{self.username}:{self.password}"
        ssl_params = ""

        if self.ssl_mode != "disable":
            ssl_params = f"?sslmode={self.ssl_mode}"
            if self.ssl_cert:
                ssl_params += f"&sslcert={self.ssl_cert}"
            if self.ssl_key:
                ssl_params += f"&sslkey={self.ssl_key}"
            if self.ssl_ca:
                ssl_params += f"&sslrootcert={self.ssl_ca}"

        return f"postgresql+asyncpg://{auth}@{self.host}:{self.port}/{self.database}{ssl_params}"
```

**Production Deployment Configuration**:
```yaml
# docker-compose.postgresql.yml
version: '3.8'

services:
  postgresql:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: shared_context
      POSTGRES_USER: shared_context_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      # Performance tuning
      POSTGRES_INITDB_ARGS: "--data-checksums"
    volumes:
      - postgresql_data:/var/lib/postgresql/data
      - ./postgresql/postgresql.conf:/etc/postgresql/postgresql.conf
      - ./postgresql/pg_hba.conf:/etc/postgresql/pg_hba.conf
    ports:
      - "5432:5432"
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
      -c hba_file=/etc/postgresql/pg_hba.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shared_context_user -d shared_context"]
      interval: 10s
      timeout: 5s
      retries: 5

  shared-context-server:
    build: .
    environment:
      - ENABLE_SQLALCHEMY=true
      - DATABASE_URL=postgresql+asyncpg://shared_context_user:${POSTGRES_PASSWORD}@postgresql:5432/shared_context
      - POSTGRES_POOL_SIZE=25
      - POSTGRES_MAX_OVERFLOW=15
    depends_on:
      postgresql:
        condition: service_healthy
    ports:
      - "23456:23456"
    restart: unless-stopped

volumes:
  postgresql_data:
```

**PostgreSQL Tuning Configuration**:
```conf
# postgresql/postgresql.conf
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 64MB

# Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Connection settings
max_connections = 100
superuser_reserved_connections = 3

# Query planning
random_page_cost = 1.1  # Assuming SSD storage
effective_io_concurrency = 200

# Logging for monitoring
log_destination = 'stderr'
logging_collector = on
log_directory = 'logs'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_min_duration_statement = 1000  # Log slow queries (>1s)
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Replication (for future HA setup)
wal_level = replica
archive_mode = on
max_wal_senders = 3
max_replication_slots = 3
```

### Testing Strategy

**PostgreSQL-Specific Testing**:
```python
# tests/unit/test_postgresql_manager.py
import pytest
import asyncio
from shared_context_server.database.postgresql_manager import PostgreSQLManager
from shared_context_server.config import PostgreSQLConfig

@pytest.mark.postgresql
@pytest.mark.asyncio
class TestPostgreSQLManager:
    async def test_postgresql_connection(self):
        """Test PostgreSQL connection and basic operations."""
        config = PostgreSQLConfig(
            username="test",
            password="test",
            database="test_db"
        )

        manager = PostgreSQLManager(config.connection_url)
        await manager.initialize()

        # Test basic query
        result = await manager.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1

        await manager.cleanup()

    async def test_postgresql_performance(self):
        """Test PostgreSQL performance with concurrent operations."""
        config = PostgreSQLConfig(
            username="test",
            password="test",
            database="test_db"
        )

        manager = PostgreSQLManager(config.connection_url)
        await manager.initialize()

        # Test concurrent queries
        async def query_task():
            return await manager.execute_query("SELECT pg_backend_pid() as pid")

        # Run 20 concurrent queries
        tasks = [query_task() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all queries completed
        assert len(results) == 20

        # Verify different backend processes (connection pooling working)
        pids = [result[0]['pid'] for result in results]
        unique_pids = set(pids)
        assert len(unique_pids) > 1, "Connection pooling should use multiple connections"

        await manager.cleanup()

    async def test_postgresql_json_operations(self):
        """Test PostgreSQL JSON operations."""
        config = PostgreSQLConfig(
            username="test",
            password="test",
            database="test_db"
        )

        manager = PostgreSQLManager(config.connection_url)
        await manager.initialize()

        # Create test table with JSON column
        await manager.execute_update("""
            CREATE TEMP TABLE test_json (
                id SERIAL PRIMARY KEY,
                data JSONB
            )
        """)

        # Insert JSON data
        test_data = {"agent_id": "test_agent", "capabilities": ["search", "memory"]}
        await manager.execute_update(
            "INSERT INTO test_json (data) VALUES (:data)",
            {"data": test_data}
        )

        # Query JSON data
        result = await manager.execute_query(
            "SELECT data->>'agent_id' as agent_id FROM test_json WHERE data ? 'capabilities'"
        )

        assert result[0]['agent_id'] == "test_agent"

        await manager.cleanup()
```

**Load Testing**:
```python
# tests/performance/test_postgresql_load.py
import pytest
import asyncio
import time
from shared_context_server.database.postgresql_manager import PostgreSQLManager

@pytest.mark.postgresql
@pytest.mark.performance
@pytest.mark.asyncio
class TestPostgreSQLLoad:
    async def test_high_concurrency_load(self):
        """Test PostgreSQL under high concurrency load."""
        manager = PostgreSQLManager("postgresql+asyncpg://test:test@localhost/test_db")
        await manager.initialize()

        # Simulate 50 concurrent agents
        concurrent_agents = 50
        operations_per_agent = 20

        async def agent_workload(agent_id: int):
            """Simulate realistic agent database operations."""
            for i in range(operations_per_agent):
                # Simulate typical operations
                await manager.execute_query("SELECT COUNT(*) FROM pg_stat_activity")
                await manager.execute_update(
                    "INSERT INTO test_log (agent_id, operation) VALUES (:agent_id, :operation)",
                    {"agent_id": agent_id, "operation": f"op_{i}"}
                )

        # Setup test table
        await manager.execute_update("""
            CREATE TEMP TABLE test_log (
                id SERIAL PRIMARY KEY,
                agent_id INTEGER,
                operation TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Run load test
        start_time = time.perf_counter()
        tasks = [agent_workload(i) for i in range(concurrent_agents)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # Verify results
        total_operations = concurrent_agents * operations_per_agent * 2  # 2 ops per iteration
        ops_per_second = total_operations / total_time

        print(f"PostgreSQL Load Test: {ops_per_second:.2f} ops/sec with {concurrent_agents} concurrent agents")

        # Performance requirement: should handle high load efficiently
        assert ops_per_second > 100, f"Performance too low: {ops_per_second} ops/sec"

        await manager.cleanup()
```

---

## Success Criteria

### Functional Success
- ✅ PostgreSQL connection manager handles 20+ concurrent agents
- ✅ Connection pooling operates efficiently under load
- ✅ PostgreSQL-specific optimizations applied correctly
- ✅ JSON operations work with native JSONB support
- ✅ Health checks provide comprehensive PostgreSQL metrics

### Performance Success
- ✅ Query performance <30ms maintained on PostgreSQL
- ✅ Connection acquisition <5ms average
- ✅ Concurrent access supports 50+ simultaneous operations
- ✅ Memory usage optimized for multi-agent workloads

### Production Readiness
- ✅ Docker Compose production configuration
- ✅ PostgreSQL tuning for shared context workloads
- ✅ SSL/TLS support for secure connections
- ✅ Monitoring and health check endpoints
- ✅ Backup and recovery procedures documented

### Validation Commands
```bash
# PostgreSQL connection testing
uv run pytest tests/unit/test_postgresql_manager.py -v -m postgresql

# Performance testing
uv run pytest tests/performance/test_postgresql_load.py -v -m postgresql

# Production configuration testing
docker-compose -f docker-compose.postgresql.yml up -d
uv run pytest tests/integration/test_postgresql_production.py -v

# Health check validation
curl http://localhost:23456/health | jq '.database_metrics'
```

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Connection pool exhaustion | High | Medium | Pool monitoring, overflow configuration |
| PostgreSQL version compatibility | Medium | Low | Version testing, compatibility matrix |
| Performance degradation under load | High | Medium | Load testing, performance optimization |
| Configuration complexity | Medium | Medium | Comprehensive documentation, examples |

### Production Considerations
- **Connection Monitoring**: Track pool usage and connection health
- **Performance Tuning**: Database-specific optimization for workload
- **Backup Strategy**: Regular automated backups
- **High Availability**: Future consideration for multi-master setup

---

## Next Steps

**Upon Completion**: Production-ready PostgreSQL backend for scaling beyond SQLite limitations
**Dependencies**: Requires all previous PRPs (007A-007D)
**Follow-up PRPs**:
- PRP-007F: Cross-Database Testing and Validation
- Optional: PRP-007G: MySQL Support (if needed)

---

**Implementation Notes**:
- Test PostgreSQL configuration thoroughly in development environment
- Validate connection pooling behavior under realistic load
- Ensure PostgreSQL-specific features don't break SQLite compatibility
- Document production deployment procedures comprehensively
