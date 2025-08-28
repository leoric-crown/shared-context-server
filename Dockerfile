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

# Extract version from pyproject.toml for build metadata
RUN VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2) && \
    echo "Building version: $VERSION" && echo "$VERSION" > /tmp/app_version

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

# Copy wheel and version from build stage and install
COPY --from=builder /build/dist/*.whl /tmp/
COPY --from=builder /tmp/app_version /app/version
RUN pip install /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Switch to non-root user
USER appuser

# Create data volume mount point
VOLUME ["/app/data"]

# Configure container - expose standard internal ports
EXPOSE 23456 34567

# Health check - verify both HTTP and WebSocket servers using dynamic ports
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD HTTP_PORT=${HTTP_PORT:-23456} WEBSOCKET_PORT=${WEBSOCKET_PORT:-34567} && \
        curl -f "http://localhost:${HTTP_PORT}/health" && \
        curl -f "http://localhost:${WEBSOCKET_PORT}/health" || exit 1

# Default environment variables (can be overridden)
ENV DATABASE_PATH=/app/data/chat_history.db \
    LOG_LEVEL=INFO \
    HTTP_PORT=23456 \
    WEBSOCKET_PORT=34567

# Default command - HTTP transport with WebSocket support using environment variable
CMD sh -c "shared-context-server --transport http --host 0.0.0.0 --port ${HTTP_PORT:-23456}"
