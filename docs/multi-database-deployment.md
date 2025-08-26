# Multi-Database Deployment Guide

This guide explains how to deploy the Shared Context Server with different database backends (SQLite, PostgreSQL, MySQL).

## Overview

The Shared Context Server supports three database backends:
- **SQLite** (default): Best for development and small deployments
- **PostgreSQL**: Recommended for production with advanced features (JSONB, GIN indexes)
- **MySQL**: Production-ready with InnoDB engine and JSON support

## Quick Start

### SQLite (Default)

```bash
# Development (default configuration)
export DATABASE_URL="sqlite+aiosqlite:///./chat_history.db"
```

### PostgreSQL

```bash
# Basic PostgreSQL setup
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/shared_context"

# With custom pool configuration
export POSTGRESQL_POOL_SIZE=25
export ENABLE_QUERY_LOGGING=true
```

### MySQL

```bash
# Basic MySQL setup
export DATABASE_URL="mysql+aiomysql://user:pass@localhost:3306/shared_context"

# With custom pool configuration
export MYSQL_POOL_SIZE=15
export ENABLE_QUERY_LOGGING=true
```

## Database-Specific Configuration

### PostgreSQL Configuration

PostgreSQL offers the best performance and features for production deployments:

```bash
# Environment Variables
export DATABASE_URL="postgresql+asyncpg://username:password@host:5432/database"

# Pool Configuration
export POSTGRESQL_POOL_SIZE=20          # Connection pool size
export DATABASE_MAX_CONNECTIONS=30      # Max overflow connections
export DATABASE_TIMEOUT=30              # Connection timeout

# Performance Tuning
export ENABLE_QUERY_LOGGING=false       # Disable in production
```

**PostgreSQL Features:**
- **JSONB**: Efficient JSON storage with indexing
- **GIN Indexes**: Fast metadata searches
- **Triggers**: Automatic timestamp updates
- **Prepared Statements**: Query performance optimization

### MySQL Configuration

MySQL provides reliable production performance with InnoDB:

```bash
# Environment Variables
export DATABASE_URL="mysql+aiomysql://username:password@host:3306/database"

# Pool Configuration
export MYSQL_POOL_SIZE=10               # Connection pool size
export DATABASE_MAX_CONNECTIONS=20      # Max overflow connections
export DATABASE_TIMEOUT=30              # Connection timeout

# MySQL-Specific Settings
export ENABLE_QUERY_LOGGING=false       # Disable in production
```

**MySQL Features:**
- **InnoDB Engine**: ACID compliance and crash recovery
- **JSON Type**: Native JSON storage and validation
- **UTF8MB4**: Full Unicode support
- **Reserved Keyword Handling**: Automatic `key` → `key_name` translation

### SQLite Configuration

SQLite is perfect for development and lightweight deployments:

```bash
# SQLite configuration
export DATABASE_URL="sqlite+aiosqlite:///./chat_history.db"

# Pool Configuration
export SQLITE_POOL_SIZE=5               # Connection pool size
export DATABASE_TIMEOUT=30              # Connection timeout
```

**SQLite Features:**
- **Zero Configuration**: No server setup required
- **PRAGMA Optimizations**: WAL mode, foreign keys, etc.
- **Single File**: Easy backup and deployment
- **ACID Compliance**: Reliable transactions

## Installation Requirements

### Base Installation

```bash
# Clone the repository and set up for development
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
uv sync
```

### PostgreSQL Support

```bash
# Add PostgreSQL driver to your local setup
uv add asyncpg>=0.29.0
```

### MySQL Support

```bash
# Add MySQL driver to your local setup
uv add aiomysql>=0.2.0
```

### All Database Support

```bash
# Add all database drivers for comprehensive support
uv add asyncpg>=0.29.0 aiomysql>=0.2.0
```

## Production Deployment Examples

### Docker with PostgreSQL

```dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Environment variables
# SQLAlchemy is the unified backend
ENV DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/shared_context
ENV POSTGRESQL_POOL_SIZE=20
ENV ENVIRONMENT=production

CMD ["python", "-m", "shared_context_server.scripts.cli"]
```

### Docker Compose with MySQL

```yaml
version: '3.8'
services:
  app:
    build: .
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@db:3306/shared_context
      - MYSQL_POOL_SIZE=15
      - ENVIRONMENT=production
    depends_on:
      - db

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: shared_context
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

### AWS RDS PostgreSQL

```bash
# Environment configuration for AWS RDS
export DATABASE_URL="postgresql+asyncpg://username:password@rds-instance.region.rds.amazonaws.com:5432/shared_context"
export POSTGRESQL_POOL_SIZE=25
export DATABASE_TIMEOUT=60
export ENVIRONMENT=production
```

### Google Cloud SQL MySQL

```bash
# Environment configuration for Google Cloud SQL
export DATABASE_URL="mysql+aiomysql://username:password@cloud-sql-proxy:3306/shared_context"
export MYSQL_POOL_SIZE=20
export DATABASE_TIMEOUT=45
export ENVIRONMENT=production
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | Full database connection URL |
| `DATABASE_PATH` | `./chat_history.db` | SQLite database file path |
| `POSTGRESQL_POOL_SIZE` | `20` | PostgreSQL connection pool size |
| `MYSQL_POOL_SIZE` | `10` | MySQL connection pool size |
| `SQLITE_POOL_SIZE` | `5` | SQLite connection pool size |
| `DATABASE_TIMEOUT` | `30` | Connection timeout in seconds |
| `ENABLE_QUERY_LOGGING` | `false` | Enable SQL query logging |

### Database URL Formats

```bash
# SQLite
sqlite+aiosqlite:///./database.db          # Relative path
sqlite+aiosqlite:////tmp/database.db       # Absolute path
sqlite+aiosqlite:///:memory:                # In-memory database

# PostgreSQL
postgresql+asyncpg://user:pass@host:5432/db
postgresql+asyncpg://user@host/db           # No password
postgresql+asyncpg://host/db                # Local connection

# MySQL
mysql+aiomysql://user:pass@host:3306/db
mysql+aiomysql://user@host/db               # No password
mysql+aiomysql://host/db                    # Local connection
```

## Performance Tuning

### PostgreSQL Optimization

```bash
# Connection tuning
export POSTGRESQL_POOL_SIZE=30              # Higher for busy servers
export DATABASE_MAX_CONNECTIONS=50          # Allow burst connections

# Query optimization
export ENABLE_QUERY_LOGGING=false           # Disable in production
```

### MySQL Optimization

```bash
# Connection tuning
export MYSQL_POOL_SIZE=20                   # Moderate pool size
export DATABASE_MAX_CONNECTIONS=40          # Handle connection spikes

# MySQL-specific tuning
export ENABLE_QUERY_LOGGING=false           # Disable in production
```

## Troubleshooting

### Common Issues

#### Missing Database Drivers

```bash
# Error: ModuleNotFoundError: No module named 'asyncpg'
pip install asyncpg>=0.29.0

# Error: ModuleNotFoundError: No module named 'aiomysql'
pip install aiomysql>=0.2.0
```

#### Connection Issues

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export ENABLE_QUERY_LOGGING=true

# Check connection strings
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db?sslmode=require"
```

#### Schema Issues

```bash
# Verify schema files are included
python -c "import shared_context_server; print(shared_context_server.__file__)"

# Check for schema initialization errors in logs
tail -f logs/server.log
```

### Health Checks

```bash
# Test database connection
python -c "
from shared_context_server.database import get_db_connection
import asyncio

async def test():
    async with get_db_connection() as conn:
        cursor = await conn.execute('SELECT 1')
        result = await cursor.fetchone()
        print(f'Database connection: OK, result: {result}')

asyncio.run(test())
"
```

## Migration Between Databases

### SQLite to PostgreSQL

```bash
# 1. Export SQLite data
sqlite3 chat_history.db ".dump" > backup.sql

# 2. Convert to PostgreSQL format (manual process)
# 3. Import to PostgreSQL
psql -d shared_context -f converted_backup.sql

# 4. Update environment
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/shared_context"
```

### Database Schema Updates

The server automatically initializes the correct schema based on the database URL. Each database type uses optimized schema files:

- **SQLite**: `database_sqlite.sql` (AUTOINCREMENT, PRAGMA settings)
- **PostgreSQL**: `database_postgresql.sql` (SERIAL, JSONB, GIN indexes)
- **MySQL**: `database_mysql.sql` (AUTO_INCREMENT, InnoDB, JSON type)

## Best Practices

### Security

```bash
# Use strong connection strings
export DATABASE_URL="postgresql+asyncpg://user:$(cat /secrets/db-password)@host:5432/db?sslmode=require"

# Separate read/write permissions
export DATABASE_URL="postgresql+asyncpg://app_user:pass@host:5432/shared_context"
```

### Monitoring

```bash
# Enable performance monitoring
export ENABLE_PERFORMANCE_MONITORING=true
export PERFORMANCE_LOG_INTERVAL=300

# Database-specific monitoring
export DATABASE_LOG_LEVEL=INFO
export ENABLE_QUERY_LOGGING=true  # Only in development
```

### Backup

```bash
# PostgreSQL
pg_dump -h host -U user shared_context > backup.sql

# MySQL
mysqldump -h host -u user -p shared_context > backup.sql

# SQLite
cp chat_history.db backup_$(date +%Y%m%d).db
```

For more information, see the [Production Deployment Guide](production-deployment.md) and [Performance Guide](performance-guide.md).
