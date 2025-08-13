# Shared Context Server - Simple Makefile
# Essential development commands

.PHONY: help install dev test test-aiosqlite test-sqlalchemy ci format lint type pre-commit quality clean docker

help: ## Show this help message
	uv run python -m scripts.makefile_help

install: ## Install dependencies
	uv sync --dev

validate: ## Validate development environment
	uv run python -m shared_context_server.scripts.dev --validate

dev: ## Start development server with hot reload
	@echo "Starting development server with hot reload..."
	uv run python -m shared_context_server.scripts.dev

test: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml

test-aiosqlite: ## Run tests with aiosqlite backend (mirrors CI)
	@echo "🔧 Testing aiosqlite backend..."
	@echo "  ✓ Creating backend-specific coverage config"
	@printf '[run]\nsource = src\nbranch = true\nomit =\n    */tests/*\n    */conftest.py\n    */__pycache__/*\n    src/shared_context_server/scripts/dev.py\n    src/shared_context_server/scripts/dev_with_websocket.py\n    src/shared_context_server/websocket_server.py\n    src/shared_context_server/database_sqlalchemy.py\n\n[report]\nfail_under = 85\n' > .coveragerc.backend
	@start_time=$$(date +%s); \
	USE_SQLALCHEMY=false uv run pytest --cov=src --cov-config=.coveragerc.backend -q --maxfail=3 --tb=short; \
	end_time=$$(date +%s); \
	duration=$$((end_time - start_time)); \
	echo "✅ aiosqlite backend tests complete ($${duration}s)"
	@rm -f .coveragerc.backend

test-sqlalchemy: ## Run tests with SQLAlchemy backend (mirrors CI)
	@echo "🔧 Testing SQLAlchemy backend..."
	@start_time=$$(date +%s); \
	USE_SQLALCHEMY=true uv run pytest --cov=src -q --maxfail=3 --tb=short; \
	end_time=$$(date +%s); \
	duration=$$((end_time - start_time)); \
	echo "✅ SQLAlchemy backend tests complete ($${duration}s)"

ci: ## Run full CI matrix locally (both backends + quality checks)
	@echo "🚀 Running complete CI matrix locally..."
	@echo "================================================"
	@ci_start=$$(date +%s); \
	echo "1/5 Pre-commit hooks (linting, formatting, type checking)..."; \
	make pre-commit || (echo "❌ Pre-commit failed" && exit 1); \
	echo "  ✓ Pre-commit passed"; \
	echo; \
	echo "2/5 Security audit..."; \
	uv run pip-audit || (echo "❌ Security audit failed" && exit 1); \
	echo "  ✓ Security audit passed"; \
	echo; \
	echo "3/5 Smoke tests..."; \
	echo "  → aiosqlite smoke test..."; \
	USE_SQLALCHEMY=false API_KEY="test-api-key" DATABASE_URL="sqlite:///./test_smoke.db" ENVIRONMENT="development" JWT_SECRET_KEY="test-jwt-secret-key" uv run pytest tests/test_smoke.py -qq --tb=no --durations-min=1 || (echo "❌ aiosqlite smoke test failed" && exit 1); \
	echo "  → SQLAlchemy smoke test..."; \
	USE_SQLALCHEMY=true API_KEY="test-api-key" DATABASE_URL="sqlite:///./test_smoke.db" ENVIRONMENT="development" JWT_SECRET_KEY="test-jwt-secret-key" uv run pytest tests/test_smoke.py -qq --tb=no --durations-min=1 || (echo "❌ SQLAlchemy smoke test failed" && exit 1); \
	rm -f test_smoke.db; \
	echo "  ✓ Smoke tests passed"; \
	echo; \
	echo "4/5 aiosqlite backend..."; \
	make test-aiosqlite || (echo "❌ aiosqlite backend tests failed" && exit 1); \
	echo; \
	echo "5/5 SQLAlchemy backend..."; \
	make test-sqlalchemy || (echo "❌ SQLAlchemy backend tests failed" && exit 1); \
	echo; \
	ci_end=$$(date +%s); \
	ci_duration=$$((ci_end - ci_start)); \
	echo "================================================"; \
	echo "✅ All CI matrix checks passed! 🎉 (Total: $${ci_duration}s)"; \
	echo "   • Pre-commit hooks: ✓"; \
	echo "   • Security audit: ✓"; \
	echo "   • Smoke tests: ✓"; \
	echo "   • aiosqlite backend: ✓"; \
	echo "   • SQLAlchemy backend: ✓"; \
	echo "Ready for CI! 🚀"

format: ## Format files using ruff
	uv run ruff format

lint: ## Run linting checks
	uv run ruff check --fix

type: ## Run type checking
	uv run mypy src

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files --show-diff-on-failure

quality: format lint type ## Run all quality checks (mirrors CI)
	uv run pip-audit

clean: ## Clean caches and temporary files
	@echo "⚠️  This will delete:"
	@echo "   • All cache directories (__pycache__, .pytest_cache, etc.)"
	@echo "   • All .db files including chat_history.db"
	@echo "   • Coverage reports and logs"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || exit 1
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
	rm -rf htmlcov/ coverage.xml .coverage
	rm -rf *.db test_*.db
	rm -rf logs/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

docker: ## Full Docker lifecycle: stop → pull/build → up → logs
	@echo "🐳 Starting Docker lifecycle..."
	@echo "1/4 Stopping containers..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") down || true
	@echo "2/4 Pulling/building images..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") pull || $(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") build --no-cache
	@echo "3/4 Starting containers..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") up -d
	@echo "4/4 Following logs (Ctrl+C to exit)..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") logs -f
