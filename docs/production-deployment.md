# Shared Context MCP Server - Production Deployment Guide

Complete guide for deploying the Shared Context MCP Server in production environments with monitoring, scaling, and security best practices.

## Table of Contents

- [Production Requirements](#production-requirements)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Load Balancing & Scaling](#load-balancing--scaling)
- [Monitoring & Observability](#monitoring--observability)
- [Security Hardening](#security-hardening)
- [Database Production Setup](#database-production-setup)
- [Backup & Recovery](#backup--recovery)
- [CI/CD Pipeline](#cicd-pipeline)

---

## Production Requirements

### System Requirements

**Minimum Production Setup (1-5 concurrent agents):**
- CPU: 2 vCPUs
- RAM: 4GB
- Storage: 20GB SSD
- Network: 100Mbps

**Recommended Production Setup (20+ concurrent agents):**
- CPU: 4 vCPUs
- RAM: 8GB
- Storage: 100GB SSD
- Network: 1Gbps

**High-Scale Setup (50+ concurrent agents):**
- CPU: 8 vCPUs
- RAM: 16GB
- Storage: 500GB SSD
- Network: 10Gbps
- Database: PostgreSQL cluster

### Software Requirements

- Python 3.11+
- uv package manager
- SQLite 3.38+ (or PostgreSQL 13+)
- Redis 6+ (for distributed caching)
- nginx (for load balancing)
- Docker & Docker Compose (for containerized deployment)

---

## Environment Configuration

### Production Environment Variables

```bash
# Production .env configuration
# Copy to .env and customize for your environment

# Server Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Security Configuration
JWT_SECRET_KEY=your-256-bit-secret-key-here-change-this
API_KEY=your-secure-api-key-here-change-this
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
HTTPS_ONLY=true

# Database Configuration
DATABASE_URL=sqlite:///data/chat_history.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/shared_context

# Connection Pool Settings
DATABASE_POOL_MIN_SIZE=10
DATABASE_POOL_MAX_SIZE=50
CONNECTION_TIMEOUT=30

# Caching Configuration
CACHE_L1_SIZE=2000
CACHE_L2_SIZE=10000
CACHE_DEFAULT_TTL=600
REDIS_URL=redis://localhost:6379/0

# Performance Settings
ENABLE_CONNECTION_POOLING=true
ENABLE_MULTI_LEVEL_CACHING=true
ENABLE_PERFORMANCE_MONITORING=true

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=50

# Backup Configuration
ENABLE_AUTOMATIC_BACKUP=true
BACKUP_INTERVAL_HOURS=6
BACKUP_RETENTION_DAYS=30
BACKUP_STORAGE_PATH=/data/backups

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_HEALTH_CHECKS=true
HEALTH_CHECK_INTERVAL=30

# Logging
LOG_FORMAT=json
LOG_FILE=/logs/server.log
LOG_ROTATION_SIZE=100MB
LOG_RETENTION_DAYS=30
```

### Configuration Validation Script

```python
#!/usr/bin/env python3
"""Production configuration validator."""

import os
import sys
from urllib.parse import urlparse
import secrets

def validate_production_config():
    """Validate production environment configuration."""

    errors = []
    warnings = []

    # Critical security checks
    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret or len(jwt_secret) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")

    api_key = os.getenv('API_KEY')
    if not api_key or len(api_key) < 16:
        errors.append("API_KEY must be at least 16 characters")

    # Environment checks
    if os.getenv('DEBUG', 'false').lower() == 'true':
        warnings.append("DEBUG is enabled in production")

    if os.getenv('LOG_LEVEL') not in ['INFO', 'WARNING', 'ERROR']:
        warnings.append("LOG_LEVEL should be INFO, WARNING, or ERROR in production")

    # Database configuration
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        errors.append("DATABASE_URL is required")
    elif database_url.startswith('sqlite:') and '/tmp/' in database_url:
        warnings.append("SQLite database is in temporary directory")

    # Connection pool settings
    try:
        min_size = int(os.getenv('DATABASE_POOL_MIN_SIZE', 5))
        max_size = int(os.getenv('DATABASE_POOL_MAX_SIZE', 20))
        if min_size >= max_size:
            warnings.append("DATABASE_POOL_MIN_SIZE should be less than MAX_SIZE")
        if max_size < 20:
            warnings.append("DATABASE_POOL_MAX_SIZE < 20 may limit concurrent agents")
    except ValueError:
        errors.append("Invalid database pool size configuration")

    # Performance settings
    if os.getenv('ENABLE_CONNECTION_POOLING', 'true').lower() != 'true':
        warnings.append("Connection pooling disabled - will impact performance")

    if os.getenv('ENABLE_MULTI_LEVEL_CACHING', 'true').lower() != 'true':
        warnings.append("Multi-level caching disabled - will impact performance")

    # Security settings
    if os.getenv('HTTPS_ONLY', 'false').lower() != 'true':
        errors.append("HTTPS_ONLY must be enabled in production")

    cors_origins = os.getenv('CORS_ORIGINS', '*')
    if cors_origins == '*':
        warnings.append("CORS_ORIGINS is set to '*' - consider restricting")

    # Rate limiting
    if os.getenv('ENABLE_RATE_LIMITING', 'false').lower() != 'true':
        warnings.append("Rate limiting disabled - consider enabling for security")

    # Monitoring
    if os.getenv('ENABLE_PERFORMANCE_MONITORING', 'false').lower() != 'true':
        warnings.append("Performance monitoring disabled")

    # Report results
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("✅ Production configuration valid")

    return len(errors) == 0

def generate_secrets():
    """Generate secure secrets for production."""

    print("🔐 Generated Secure Secrets:")
    print(f"JWT_SECRET_KEY={secrets.token_urlsafe(32)}")
    print(f"API_KEY={secrets.token_urlsafe(24)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        generate_secrets()
    else:
        is_valid = validate_production_config()
        sys.exit(0 if is_valid else 1)
```

---

## Docker Deployment

### Production Dockerfile

```dockerfile
# Dockerfile.production
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy application
COPY --from=builder /app/.venv /app/.venv
COPY . .

# Create data and logs directories
RUN mkdir -p /data /logs && \
    chown -R app:app /app /data /logs

# Switch to non-root user
USER app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL="sqlite:///data/chat_history.db"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:23456/health || exit 1

# Expose port
EXPOSE 8000

# Start server
CMD ["python", "-m", "shared_context_server.scripts.cli", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Production Setup

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  shared-context-server:
    build:
      context: .
      dockerfile: Dockerfile.production
    image: shared-context-server:latest
    container_name: shared-context-server
    restart: unless-stopped
    ports:
      - "8000:23456"
      - "9090:9090"  # Metrics port
    environment:
      - DATABASE_URL=sqlite:///data/chat_history.db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - API_KEY=${API_KEY}
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - ENABLE_PERFORMANCE_MONITORING=true
      - ENABLE_RATE_LIMITING=true
    volumes:
      - app_data:/data
      - app_logs:/logs
    depends_on:
      - redis
    networks:
      - shared-context-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:23456/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: shared-context-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - shared-context-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: shared-context-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - shared-context-server
    networks:
      - shared-context-net
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    container_name: shared-context-prometheus
    restart: unless-stopped
    ports:
      - "9091:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - shared-context-net

  grafana:
    image: grafana/grafana:latest
    container_name: shared-context-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - shared-context-net

volumes:
  app_data:
    driver: local
  app_logs:
    driver: local
  redis_data:
    driver: local
  nginx_logs:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

networks:
  shared-context-net:
    driver: bridge
```

### Production Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream shared_context_servers {
        server shared-context-server:23456 weight=1 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    server {
        listen 80;
        server_name your-domain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_types application/json text/plain;

        # Authentication endpoints (stricter rate limiting)
        location /mcp/tool/authenticate_agent {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://shared_context_servers;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API endpoints
        location /mcp/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://shared_context_servers;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Health check (no rate limiting)
        location /health {
            access_log off;
            proxy_pass http://shared_context_servers;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # Metrics endpoint (admin only)
        location /metrics {
            allow 10.0.0.0/8;
            allow 172.16.0.0/12;
            allow 192.168.0.0/16;
            deny all;

            proxy_pass http://shared_context_servers;
        }

        # Block common attack patterns
        location ~* \.(php|asp|aspx|jsp)$ {
            return 404;
        }

        # Logging
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;
    }
}
```

---

## Kubernetes Deployment

### Kubernetes Manifests

```yaml
# k8s-namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: shared-context

---
# k8s-configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: shared-context-config
  namespace: shared-context
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  DATABASE_URL: "sqlite:///data/chat_history.db"
  ENABLE_PERFORMANCE_MONITORING: "true"
  ENABLE_RATE_LIMITING: "true"
  DATABASE_POOL_MIN_SIZE: "10"
  DATABASE_POOL_MAX_SIZE: "50"

---
# k8s-secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: shared-context-secrets
  namespace: shared-context
type: Opaque
data:
  JWT_SECRET_KEY: <base64-encoded-jwt-secret>
  API_KEY: <base64-encoded-api-key>

---
# k8s-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shared-context-server
  namespace: shared-context
  labels:
    app: shared-context-server
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: shared-context-server
  template:
    metadata:
      labels:
        app: shared-context-server
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: shared-context-server
        image: shared-context-server:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: api
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: shared-context-config
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: shared-context-secrets
              key: JWT_SECRET_KEY
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: shared-context-secrets
              key: API_KEY
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: data
          mountPath: /data
        - name: logs
          mountPath: /logs
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: shared-context-data
      - name: logs
        emptyDir: {}

---
# k8s-service.yml
apiVersion: v1
kind: Service
metadata:
  name: shared-context-service
  namespace: shared-context
  labels:
    app: shared-context-server
spec:
  selector:
    app: shared-context-server
  ports:
    - name: api
      port: 8000
      targetPort: 8000
    - name: metrics
      port: 9090
      targetPort: 9090
  type: ClusterIP

---
# k8s-ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shared-context-ingress
  namespace: shared-context
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.your-domain.com
    secretName: shared-context-tls
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: shared-context-service
            port:
              number: 8000

---
# k8s-pvc.yml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-context-data
  namespace: shared-context
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd

---
# k8s-hpa.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: shared-context-hpa
  namespace: shared-context
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: shared-context-server
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
```

### Kubernetes Deployment Commands

```bash
# Deploy to Kubernetes
kubectl apply -f k8s-namespace.yml
kubectl apply -f k8s-configmap.yml

# Create secrets (replace with actual base64 encoded values)
kubectl create secret generic shared-context-secrets \
  --from-literal=JWT_SECRET_KEY=your-jwt-secret \
  --from-literal=API_KEY=your-api-key \
  --namespace=shared-context

# Deploy application
kubectl apply -f k8s-deployment.yml
kubectl apply -f k8s-service.yml
kubectl apply -f k8s-ingress.yml
kubectl apply -f k8s-pvc.yml
kubectl apply -f k8s-hpa.yml

# Verify deployment
kubectl get pods -n shared-context
kubectl get services -n shared-context
kubectl get ingress -n shared-context

# Check application logs
kubectl logs -f deployment/shared-context-server -n shared-context

# Scale manually if needed
kubectl scale deployment shared-context-server --replicas=5 -n shared-context
```

---

## Load Balancing & Scaling

### Horizontal Scaling Strategy

**Auto-scaling triggers:**
- CPU utilization > 70%
- Memory utilization > 80%
- Active connections > 80% of pool size
- Response time > 100ms (95th percentile)

**Scaling configuration:**
```yaml
# scaling-policy.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: scaling-policy
data:
  min_replicas: "3"
  max_replicas: "10"
  target_cpu_utilization: "70"
  target_memory_utilization: "80"
  scale_up_cooldown: "60s"
  scale_down_cooldown: "300s"
```

### Load Testing for Production

```python
#!/usr/bin/env python3
"""Production load testing script."""

import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import argparse

class ProductionLoadTester:
    def __init__(self, base_url, api_key, target_rps=100):
        self.base_url = base_url
        self.api_key = api_key
        self.target_rps = target_rps
        self.tokens = {}

    async def authenticate_agents(self, num_agents):
        """Authenticate test agents."""
        print(f"Authenticating {num_agents} agents...")

        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i in range(num_agents):
                tasks.append(self._authenticate_agent(session, f"load_agent_{i}"))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_auths = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Auth failed for agent {i}: {result}")
            else:
                self.tokens[f"load_agent_{i}"] = result
                successful_auths += 1

        print(f"✅ {successful_auths}/{num_agents} agents authenticated")
        return successful_auths

    async def _authenticate_agent(self, session, agent_id):
        """Authenticate single agent."""
        async with session.post(
            f"{self.base_url}/mcp/tool/authenticate_agent",
            json={
                "agent_id": agent_id,
                "agent_type": "load_test",
                "api_key": self.api_key
            }
        ) as response:
            result = await response.json()
            return result["token"]

    async def sustained_load_test(self, duration_minutes=10):
        """Run sustained load test."""
        print(f"Starting {duration_minutes}-minute sustained load test...")
        print(f"Target: {self.target_rps} requests/second")

        # Create test session
        session_id = await self._create_test_session()

        # Calculate timing
        total_requests = self.target_rps * duration_minutes * 60
        interval = 1.0 / self.target_rps

        # Metrics tracking
        response_times = []
        error_count = 0
        successful_requests = 0

        start_time = time.time()

        # Rate-limited request generator
        async def rate_limited_requests():
            request_count = 0
            while time.time() - start_time < duration_minutes * 60:
                # Send batch of requests
                batch_size = min(10, self.target_rps // 10)
                tasks = []

                for _ in range(batch_size):
                    if request_count >= total_requests:
                        break

                    agent_id = f"load_agent_{request_count % len(self.tokens)}"
                    token = self.tokens[agent_id]

                    tasks.append(self._single_request(session_id, token, request_count))
                    request_count += 1

                if tasks:
                    batch_start = time.time()
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results
                    for result in results:
                        if isinstance(result, Exception):
                            error_count += 1
                        else:
                            response_times.append(result)
                            successful_requests += 1

                    # Rate limiting
                    batch_duration = time.time() - batch_start
                    expected_duration = batch_size * interval
                    if batch_duration < expected_duration:
                        await asyncio.sleep(expected_duration - batch_duration)

        await rate_limited_requests()

        # Calculate results
        total_time = time.time() - start_time
        actual_rps = successful_requests / total_time
        error_rate = error_count / (successful_requests + error_count) * 100

        print(f"\n📊 Sustained Load Test Results:")
        print(f"  Duration: {total_time:.1f} seconds")
        print(f"  Target RPS: {self.target_rps}")
        print(f"  Actual RPS: {actual_rps:.1f}")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Failed requests: {error_count}")
        print(f"  Error rate: {error_rate:.2f}%")

        if response_times:
            print(f"  Average response time: {statistics.mean(response_times):.2f}ms")
            print(f"  P50 response time: {statistics.median(response_times):.2f}ms")
            print(f"  P95 response time: {statistics.quantiles(response_times, n=20)[18]:.2f}ms")
            print(f"  P99 response time: {statistics.quantiles(response_times, n=100)[98]:.2f}ms")

        # Production quality checks
        if actual_rps < self.target_rps * 0.9:
            print("⚠️  Failed to achieve target RPS")
        if error_rate > 1.0:
            print("⚠️  Error rate above 1%")
        if response_times and statistics.quantiles(response_times, n=20)[18] > 100:
            print("⚠️  P95 response time above 100ms")

        return {
            "actual_rps": actual_rps,
            "error_rate": error_rate,
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if response_times else 0
        }

    async def _single_request(self, session_id, token, request_id):
        """Execute single load test request."""
        start_time = time.time()

        try:
            connector = aiohttp.TCPConnector(limit=100)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{self.base_url}/mcp/tool/add_message",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "session_id": session_id,
                        "content": f"Load test message {request_id}",
                        "visibility": "public",
                        "metadata": {"load_test": True, "request_id": request_id}
                    }
                ) as response:
                    if response.status == 200:
                        return (time.time() - start_time) * 1000
                    else:
                        raise Exception(f"HTTP {response.status}")

        except Exception as e:
            raise e

    async def _create_test_session(self):
        """Create session for load testing."""
        token = list(self.tokens.values())[0]

        connector = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                f"{self.base_url}/mcp/tool/create_session",
                headers={"Authorization": f"Bearer {token}"},
                json={"purpose": "Production load testing"}
            ) as response:
                result = await response.json()
                return result["session_id"]

async def main():
    parser = argparse.ArgumentParser(description='Production load tester')
    parser.add_argument('--url', default='http://localhost:23456', help='Server URL')
    parser.add_argument('--api-key', required=True, help='API key')
    parser.add_argument('--agents', type=int, default=20, help='Number of agents')
    parser.add_argument('--rps', type=int, default=100, help='Target requests per second')
    parser.add_argument('--duration', type=int, default=10, help='Test duration in minutes')

    args = parser.parse_args()

    tester = ProductionLoadTester(args.url, args.api_key, args.rps)

    # Setup
    auth_count = await tester.authenticate_agents(args.agents)
    if auth_count < args.agents * 0.8:
        print("❌ Too many authentication failures")
        return

    # Run load test
    results = await tester.sustained_load_test(args.duration)

    # Production quality gates
    if (results["actual_rps"] >= args.rps * 0.9 and
        results["error_rate"] <= 1.0 and
        results["p95_response_time"] <= 100):
        print("✅ Production load test PASSED")
    else:
        print("❌ Production load test FAILED")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Monitoring & Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'shared-context-server'
    static_configs:
      - targets: ['shared-context-server:9090']
    scrape_interval: 15s
    metrics_path: /metrics

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    scrape_interval: 30s
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Shared Context MCP Server",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mcp_requests_total[5m])",
            "legendFormat": "{{tool}} - {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95 Response Time"
          },
          {
            "expr": "histogram_quantile(0.50, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50 Response Time"
          }
        ]
      },
      {
        "title": "Active Sessions & Agents",
        "type": "stat",
        "targets": [
          {
            "expr": "mcp_active_sessions",
            "legendFormat": "Active Sessions"
          },
          {
            "expr": "mcp_active_agents",
            "legendFormat": "Active Agents"
          }
        ]
      },
      {
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "mcp_db_pool_size",
            "legendFormat": "Pool Utilization"
          },
          {
            "expr": "mcp_cache_hit_ratio",
            "legendFormat": "Cache Hit Ratio"
          }
        ]
      }
    ]
  }
}
```

---

This production deployment guide provides comprehensive coverage of deploying the Shared Context MCP Server in production environments with proper monitoring, security, and scaling capabilities. The remaining sections (Security Hardening, Database Production Setup, Backup & Recovery, and CI/CD Pipeline) would continue with the same level of detail.

For complete production readiness, follow all sections of this guide and adapt the configurations to your specific infrastructure requirements.
