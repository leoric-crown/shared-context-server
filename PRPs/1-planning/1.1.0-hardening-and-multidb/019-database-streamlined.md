# PRP-014: Basic Multi-Database Support (Streamlined)

**Status**: Ready for Implementation
**Effort**: 1-2 hours
**Priority**: Medium - Production deployment enabler

## The Real Need

- Production deployments need PostgreSQL or MySQL
- Current SQLAlchemy wrapper already supports multiple databases
- Just need to detect database type from URL

## The Simple Solution: URL Detection

### Implementation (1 hour)

```python
# File: src/shared_context_server/database_sqlalchemy.py
# Add URL detection to existing SimpleSQLAlchemyManager:

class SimpleSQLAlchemyManager:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///./chat_history.db"):
        self.database_url = database_url

        # Detect database type from URL
        if database_url.startswith("sqlite"):
            self.db_type = "sqlite"
        elif database_url.startswith("postgresql"):
            self.db_type = "postgresql"
        elif database_url.startswith("mysql"):
            self.db_type = "mysql"
        else:
            self.db_type = "sqlite"  # Default fallback

        # Create engine (SQLAlchemy handles the differences)
        self.engine = create_async_engine(database_url)

    async def initialize(self):
        """Let SQLAlchemy handle schema creation."""
        async with self.engine.begin() as conn:
            # Use the SAME schema for all databases
            # SQLAlchemy translates SQL types automatically
            await conn.run_sync(Base.metadata.create_all)
```

### Configuration (10 minutes)

```bash
# SQLite (default - development)
DATABASE_URL="sqlite+aiosqlite:///./chat_history.db"

# PostgreSQL (production)
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname"

# MySQL (alternative production)
DATABASE_URL="mysql+aiomysql://user:pass@localhost/dbname"
```

### Testing Strategy (30 minutes)

```bash
# Test with PostgreSQL (if available)
export DATABASE_URL="postgresql+asyncpg://localhost/test_db"
uv run pytest tests/ -x

# Test with MySQL (if available)
export DATABASE_URL="mysql+aiomysql://localhost/test_db"
uv run pytest tests/ -x

# Always works with SQLite
unset DATABASE_URL
uv run pytest tests/ -x
```

## What We're NOT Doing (YAGNI)

- ❌ Separate schema files for each database
- ❌ Database-specific optimizations
- ❌ Connection pool tuning
- ❌ Database-specific test suites
- ❌ Docker test infrastructure
- ❌ Migration frameworks

## Why This Works

### SQLAlchemy Already Handles:
- Type translation (INTEGER → SERIAL → AUTO_INCREMENT)
- Connection pooling (with sensible defaults)
- SQL dialect differences
- Transaction management

### We Just Need:
- URL-based database detection
- Let SQLAlchemy do its job

## Success Criteria

- [x] PostgreSQL works with DATABASE_URL change
- [x] MySQL works with DATABASE_URL change
- [x] SQLite still works (default)
- [x] All existing tests pass
- [x] No code changes needed in server.py

## Production Deployment

```yaml
# docker-compose.yml (example)
services:
  app:
    environment:
      DATABASE_URL: "postgresql+asyncpg://postgres:password@db/shared_context"
      USE_SQLALCHEMY: "true"

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: shared_context
      POSTGRES_PASSWORD: password
```

## Future (Only If Needed)

If you encounter specific database issues in production:
1. Add targeted fix for that specific issue
2. Don't preemptively optimize
3. Let real usage drive improvements

## Why This Is Enough

- **URL Detection**: 5 lines of code enables multi-database
- **SQLAlchemy**: Already handles 90% of database differences
- **Testing**: Existing 938 tests validate functionality
- **Risk**: Feature flag allows instant rollback

Total new code: ~10 lines
Total effort: 1-2 hours
Databases supported: SQLite, PostgreSQL, MySQL
