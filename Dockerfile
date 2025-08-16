# Multi-stage build for Shared Context MCP Server
# Optimized for security, size, and multi-platform support

# =============================================================================
# Build Stage - Install build dependencies and create wheel
# =============================================================================
FROM python:3.11-slim AS builder

# Set build environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create build directory
WORKDIR /build

# Copy only package configuration files first (for better caching)
COPY pyproject.toml README.md LICENSE database_*.sql ./
COPY src/ ./src/

# Install build tools and create wheel
RUN pip install build && \
    python -m build --wheel && \
    ls -la dist/

# =============================================================================
# Runtime Stage - Create minimal production image
# =============================================================================
FROM python:3.11-slim AS runtime

# Runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and group
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /bin/bash appuser

# Create application directories
WORKDIR /app
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Copy wheel from build stage and install
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Switch to non-root user
USER appuser

# Create data volume mount point
VOLUME ["/app/data"]

# Configure container
EXPOSE 23456 34567

# Health check - verify both HTTP and WebSocket servers
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:23456/health && curl -f http://localhost:34567/health || exit 1

# Default environment variables (can be overridden)
ENV DATABASE_PATH=/app/data/chat_history.db \
    LOG_LEVEL=INFO

# Default command - HTTP transport with WebSocket support
CMD ["shared-context-server", "--transport", "http", "--host", "0.0.0.0", "--port", "23456"]
