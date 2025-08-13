# PRP-007C: Alembic Setup and Schema Definition

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-12
**Parent PRP**: PRP-007 SQLAlchemy Core Database Migration
**Prerequisites**: PRP-007A Foundation, PRP-007B Database Manager Integration
**Status**: Implementation Ready
**Priority**: High - Schema Management Foundation
**Estimated Effort**: 2-3 days
**Complexity Level**: Medium - Schema Management Setup

---

## Executive Summary

Establish Alembic migration framework and convert existing database schema to SQLAlchemy Table definitions, enabling version-controlled schema management and cross-database compatibility.

**Scope**: Alembic setup, schema definition, initial migration creation
**Goal**: Production-ready schema migration system with cross-database support

---

## Implementation Specification

### Core Requirements

**Alembic Configuration Setup**:
```ini
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = sqlite:///./chat_history.db

[post_write_hooks]
# Hooks for code formatting (optional)
hooks = ruff
ruff.type = console_scripts
ruff.entrypoint = ruff
ruff.options = format REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Alembic Environment Configuration**:
```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared_context_server.database.schema import metadata
from shared_context_server.config import get_database_config

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = metadata

def get_database_url():
    """Get database URL from configuration or environment."""
    # Check for command line override
    cmd_line_url = context.get_x_argument(as_dictionary=True).get('database_url')
    if cmd_line_url:
        return cmd_line_url

    # Check environment variable
    env_url = os.environ.get('DATABASE_URL')
    if env_url:
        return env_url

    # Use application configuration
    try:
        db_config = get_database_config()
        return db_config.effective_database_url
    except Exception:
        # Fallback to default SQLite
        return "sqlite:///./chat_history.db"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**SQLAlchemy Schema Definition**:
```python
# src/shared_context_server/database/schema.py
from sqlalchemy import (
    MetaData, Table, Column, Integer, Text, Boolean,
    DateTime, ForeignKey, Index, text
)
from sqlalchemy.sql import func

metadata = MetaData()

# Sessions table
sessions = Table(
    'sessions',
    metadata,
    Column('id', Text, primary_key=True),
    Column('purpose', Text, nullable=False),
    Column('created_at', DateTime, server_default=func.current_timestamp()),
    Column('updated_at', DateTime, server_default=func.current_timestamp()),
    Column('is_active', Boolean, server_default=text('TRUE')),
    Column('created_by', Text, nullable=False),
    Column('metadata', Text),  # JSON validation handled at application level
)

# Messages table
messages = Table(
    'messages',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('session_id', Text, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
    Column('sender', Text, nullable=False),
    Column('sender_type', Text, server_default=text("'generic'")),
    Column('content', Text, nullable=False),
    Column('visibility', Text, server_default=text("'public'")),
    Column('message_type', Text, server_default=text("'agent_response'")),
    Column('metadata', Text),  # JSON validation handled at application level
    Column('timestamp', DateTime, server_default=func.current_timestamp()),
    Column('parent_message_id', Integer, ForeignKey('messages.id', ondelete='SET NULL')),
)

# Agent memory table
agent_memory = Table(
    'agent_memory',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('agent_id', Text, nullable=False),
    Column('session_id', Text, ForeignKey('sessions.id', ondelete='CASCADE')),
    Column('key', Text, nullable=False),
    Column('value', Text, nullable=False),
    Column('metadata', Text),  # JSON validation handled at application level
    Column('created_at', DateTime, server_default=func.current_timestamp()),
    Column('updated_at', DateTime, server_default=func.current_timestamp()),
    Column('expires_at', DateTime),
)

# Audit log table
audit_log = Table(
    'audit_log',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('timestamp', DateTime, server_default=func.current_timestamp()),
    Column('event_type', Text, nullable=False),
    Column('agent_id', Text, nullable=False),
    Column('session_id', Text, ForeignKey('sessions.id', ondelete='SET NULL')),
    Column('resource', Text),
    Column('action', Text),
    Column('result', Text),
    Column('metadata', Text),  # JSON validation handled at application level
)

# Secure tokens table (PRP-006)
secure_tokens = Table(
    'secure_tokens',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('token_id', Text, unique=True, nullable=False),
    Column('encrypted_jwt', Text, nullable=False),  # BLOB in SQLite, TEXT in others
    Column('agent_id', Text, nullable=False),
    Column('expires_at', DateTime, nullable=False),
    Column('created_at', DateTime, server_default=func.current_timestamp()),
)

# Schema version table
schema_version = Table(
    'schema_version',
    metadata,
    Column('version', Integer, primary_key=True),
    Column('applied_at', DateTime, server_default=func.current_timestamp()),
    Column('description', Text),
)

# Performance indexes
Index('idx_messages_session_id', messages.c.session_id)
Index('idx_messages_session_time', messages.c.session_id, messages.c.timestamp)
Index('idx_messages_sender_timestamp', messages.c.sender, messages.c.timestamp)
Index('idx_messages_visibility_session', messages.c.visibility, messages.c.session_id)
Index('idx_messages_parent_id', messages.c.parent_message_id)
Index('idx_messages_sender_type', messages.c.sender_type, messages.c.timestamp)

Index('idx_agent_memory_lookup', agent_memory.c.agent_id, agent_memory.c.session_id, agent_memory.c.key)
Index('idx_agent_memory_agent_global', agent_memory.c.agent_id)
Index('idx_agent_memory_expiry', agent_memory.c.expires_at)
Index('idx_agent_memory_session', agent_memory.c.session_id)

Index('idx_audit_log_timestamp', audit_log.c.timestamp)
Index('idx_audit_log_agent_time', audit_log.c.agent_id, audit_log.c.timestamp)
Index('idx_audit_log_session_time', audit_log.c.session_id, audit_log.c.timestamp)
Index('idx_audit_log_event_type', audit_log.c.event_type, audit_log.c.timestamp)

Index('idx_sessions_created_by', sessions.c.created_by)
Index('idx_sessions_active', sessions.c.is_active)
Index('idx_sessions_updated_at', sessions.c.updated_at)

Index('idx_token_id', secure_tokens.c.token_id)
Index('idx_agent_expires', secure_tokens.c.agent_id, secure_tokens.c.expires_at)
Index('idx_expires_cleanup', secure_tokens.c.expires_at)
```

**Database-Specific Schema Variations**:
```python
# src/shared_context_server/database/schema_variants.py
from sqlalchemy import Table, Column, JSON, Text
from .schema import metadata

def apply_database_specific_schema(engine_url: str):
    """Apply database-specific schema modifications."""

    if 'postgresql' in engine_url:
        # PostgreSQL can use native JSON type
        # Recreate tables with JSON columns instead of Text
        # This would be handled in migration scripts
        pass

    elif 'mysql' in engine_url:
        # MySQL specific optimizations
        # Use appropriate storage engines, charset settings
        pass

    # SQLite uses the base schema as-is
```

**Initial Migration Script**:
```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create initial schema."""
    # Sessions table
    op.create_table('sessions',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE')),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.Column('metadata', sa.Text()),
        sa.PrimaryKeyConstraint('id')
    )

    # Messages table
    op.create_table('messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('sender', sa.Text(), nullable=False),
        sa.Column('sender_type', sa.Text(), server_default=sa.text("'generic'")),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('visibility', sa.Text(), server_default=sa.text("'public'")),
        sa.Column('message_type', sa.Text(), server_default=sa.text("'agent_response'")),
        sa.Column('metadata', sa.Text()),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('parent_message_id', sa.Integer()),
        sa.ForeignKeyConstraint(['parent_message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Agent memory table
    op.create_table('agent_memory',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent_id', sa.Text(), nullable=False),
        sa.Column('session_id', sa.Text()),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('metadata', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'session_id', 'key')
    )

    # Audit log table
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('agent_id', sa.Text(), nullable=False),
        sa.Column('session_id', sa.Text()),
        sa.Column('resource', sa.Text()),
        sa.Column('action', sa.Text()),
        sa.Column('result', sa.Text()),
        sa.Column('metadata', sa.Text()),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Secure tokens table
    op.create_table('secure_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token_id', sa.Text(), nullable=False),
        sa.Column('encrypted_jwt', sa.Text(), nullable=False),
        sa.Column('agent_id', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id')
    )

    # Schema version table
    op.create_table('schema_version',
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('applied_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('description', sa.Text()),
        sa.PrimaryKeyConstraint('version')
    )

    # Create all indexes
    op.create_index('idx_messages_session_id', 'messages', ['session_id'])
    op.create_index('idx_messages_session_time', 'messages', ['session_id', 'timestamp'])
    op.create_index('idx_messages_sender_timestamp', 'messages', ['sender', 'timestamp'])
    op.create_index('idx_messages_visibility_session', 'messages', ['visibility', 'session_id'])
    op.create_index('idx_messages_parent_id', 'messages', ['parent_message_id'])
    op.create_index('idx_messages_sender_type', 'messages', ['sender_type', 'timestamp'])

    op.create_index('idx_agent_memory_lookup', 'agent_memory', ['agent_id', 'session_id', 'key'])
    op.create_index('idx_agent_memory_agent_global', 'agent_memory', ['agent_id'])
    op.create_index('idx_agent_memory_expiry', 'agent_memory', ['expires_at'])
    op.create_index('idx_agent_memory_session', 'agent_memory', ['session_id'])

    op.create_index('idx_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('idx_audit_log_agent_time', 'audit_log', ['agent_id', 'timestamp'])
    op.create_index('idx_audit_log_session_time', 'audit_log', ['session_id', 'timestamp'])
    op.create_index('idx_audit_log_event_type', 'audit_log', ['event_type', 'timestamp'])

    op.create_index('idx_sessions_created_by', 'sessions', ['created_by'])
    op.create_index('idx_sessions_active', 'sessions', ['is_active'])
    op.create_index('idx_sessions_updated_at', 'sessions', ['updated_at'])

    op.create_index('idx_token_id', 'secure_tokens', ['token_id'])
    op.create_index('idx_agent_expires', 'secure_tokens', ['agent_id', 'expires_at'])
    op.create_index('idx_expires_cleanup', 'secure_tokens', ['expires_at'])

    # Insert initial schema version
    op.execute("INSERT INTO schema_version (version, description) VALUES (1, 'Initial SQLAlchemy schema')")

def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('secure_tokens')
    op.drop_table('audit_log')
    op.drop_table('agent_memory')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('schema_version')
```

### Integration Points

**Schema Integration with Database Manager**:
```python
# src/shared_context_server/database/manager.py (additions)
from .schema import metadata

class UnifiedDatabaseManager:
    # ... existing code ...

    async def create_schema(self):
        """Create database schema using SQLAlchemy metadata."""
        if self.use_sqlalchemy:
            async with self.backend.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
        else:
            # Legacy schema creation remains unchanged
            await self.backend.initialize()

    async def get_schema_version(self) -> int:
        """Get current schema version."""
        try:
            result = await self.execute_query("SELECT MAX(version) FROM schema_version")
            return result[0]['max'] if result and result[0]['max'] else 0
        except Exception:
            return 0
```

### Testing Strategy

**Schema Validation Testing**:
```python
# tests/unit/test_schema_definition.py
import pytest
from sqlalchemy import create_engine
from shared_context_server.database.schema import metadata

class TestSchemaDefinition:
    def test_schema_table_creation(self):
        """Test schema tables can be created."""
        engine = create_engine("sqlite:///:memory:")
        metadata.create_all(engine)

        # Verify all tables exist
        inspector = engine.inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            'sessions', 'messages', 'agent_memory',
            'audit_log', 'secure_tokens', 'schema_version'
        ]

        for table in expected_tables:
            assert table in tables

    def test_schema_indexes_created(self):
        """Test all required indexes are created."""
        engine = create_engine("sqlite:///:memory:")
        metadata.create_all(engine)

        inspector = engine.inspect(engine)

        # Check critical indexes exist
        messages_indexes = inspector.get_indexes('messages')
        index_names = [idx['name'] for idx in messages_indexes]

        assert 'idx_messages_session_id' in index_names
        assert 'idx_messages_session_time' in index_names

    def test_foreign_key_constraints(self):
        """Test foreign key relationships are properly defined."""
        engine = create_engine("sqlite:///:memory:")
        metadata.create_all(engine)

        inspector = engine.inspect(engine)

        # Check messages foreign keys
        messages_fks = inspector.get_foreign_keys('messages')
        fk_tables = [fk['referred_table'] for fk in messages_fks]

        assert 'sessions' in fk_tables
        assert 'messages' in fk_tables  # self-reference for parent_message_id
```

**Alembic Migration Testing**:
```python
# tests/unit/test_alembic_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
import tempfile
import os

class TestAlembicMigrations:
    def test_migration_upgrade_downgrade(self):
        """Test migration upgrade and downgrade cycle."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            # Configure Alembic for test database
            alembic_cfg = Config()
            alembic_cfg.set_main_option('script_location', 'alembic')
            alembic_cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')

            # Run upgrade
            command.upgrade(alembic_cfg, 'head')

            # Verify schema exists
            engine = create_engine(f'sqlite:///{db_path}')
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
                assert 'sessions' in tables
                assert 'messages' in tables

            # Run downgrade
            command.downgrade(alembic_cfg, 'base')

            # Verify tables removed
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
                assert 'sessions' not in tables

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
```

---

## Success Criteria

### Functional Success
- ✅ Alembic configuration functional with SQLite, PostgreSQL, MySQL
- ✅ Schema definition creates all required tables and indexes
- ✅ Migration scripts run successfully forward and backward
- ✅ Schema version tracking operational
- ✅ Database-specific optimizations applied correctly

### Integration Success
- ✅ Schema integrates with UnifiedDatabaseManager
- ✅ Existing data preserved during migration testing
- ✅ Cross-database schema compatibility validated
- ✅ Performance indexes optimize query performance

### Quality Gates
- ✅ 100% test coverage for schema definition and migrations
- ✅ Migration scripts tested on all target databases
- ✅ Schema validation passes for all database types
- ✅ Performance benchmarks maintained

### Validation Commands
```bash
# Alembic setup verification
uv run alembic check
uv run alembic current
uv run alembic history

# Schema migration testing
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head

# Cross-database testing
DATABASE_URL="postgresql://test:test@localhost/test" uv run alembic upgrade head
DATABASE_URL="mysql://test:test@localhost/test" uv run alembic upgrade head

# Schema validation testing
uv run pytest tests/unit/test_schema_definition.py -v
uv run pytest tests/unit/test_alembic_migrations.py -v
```

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Schema incompatibility across databases | High | Medium | Extensive cross-database testing |
| Migration script bugs | High | Medium | Comprehensive test coverage, rollback testing |
| Data loss during migration | Critical | Low | Backup procedures, migration validation |
| Performance degradation | Medium | Low | Index optimization, performance testing |

### Migration Safety
- **Backup Strategy**: Always backup before migration
- **Rollback Testing**: Test downgrade paths thoroughly
- **Validation Steps**: Verify data integrity after migration
- **Staged Rollout**: Test in development, staging before production

---

## Next Steps

**Upon Completion**: Enables version-controlled schema management across database backends
**Dependencies**: Requires PRP-007A and PRP-007B
**Follow-up PRPs**:
- PRP-007D: Migration Testing and Validation
- PRP-007E: PostgreSQL Support Implementation

---

**Implementation Notes**:
- Start with SQLite schema definition and migration
- Test migration forward/backward thoroughly before multi-database support
- Ensure schema compatibility across all target databases
- Validate performance impact of schema changes
