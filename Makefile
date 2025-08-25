# Shared Context Server - Simple Makefile
# Essential development commands

.PHONY: help install dev test test-quick format lint type pre-commit quality clean docker

help: ## Show this help message
	uv run python -m scripts.makefile_help

install: ## Install dependencies
	uv sync --dev

validate: ## Validate development environment
	uv run python -m shared_context_server.scripts.dev --validate

dev: ## Start development server with hot reload
	@echo "Starting development server with hot reload..."
	uv run python -m shared_context_server.scripts.dev

test: ## Run tests with coverage (target: 70%+)
	@echo "🧪 Running tests with coverage..."
	@start=$$(date +%s); \
	if uv run pytest -qq --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=70 --timeout=30; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "✅ Tests with coverage completed ($${duration}s)"; \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "❌ Tests with coverage failed ($${duration}s)"; \
		exit 1; \
	fi

test-quick: ## Run tests without coverage (faster)
	@echo "⚡ Running tests without coverage tracking..."
	@start=$$(date +%s); \
	if uv run pytest -x -qq  --tb=short --timeout=30; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "✅ Quick tests completed ($${duration}s)"; \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "❌ Quick tests failed ($${duration}s)"; \
		exit 1; \
	fi



format: ## Format files using ruff
	@echo "Running: uv run ruff format"
	uv run ruff format

lint: ## Run linting checks
	@echo "Running: uv run ruff check --fix"
	uv run ruff check --fix

type: ## Run type checking
	@echo "Running: uv run mypy src"
	uv run mypy src

pre-commit: ## Run pre-commit hooks on all files
	@echo "Running: uv run pre-commit run --show-diff-on-failure"
	uv run pre-commit run --show-diff-on-failure

quality: format lint type ## Run all quality checks (use with test-all for complete CI)
	@echo "Running: uv run pip-audit"
	uv run pip-audit

clean: ## Clean caches and temporary files
	@echo "⚠️  This will delete:"
	@echo "   • All cache directories (__pycache__, .pytest_cache, etc.)"
	@echo "   • Coverage reports and logs"
	@echo "   • Test database files (test_*.db)"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || exit 1
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
	rm -rf htmlcov/ coverage.xml .coverage
	rm -rf test_*.db
	rm -rf logs/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

docker: ## Full Docker development lifecycle with hot reload
	@echo "🐳 Starting Docker development environment..."
	@echo "🔥 Hot reload enabled - server will restart on file changes"
	@echo "1/4 Stopping containers..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") -f docker-compose.dev.yml down || true
	@echo "2/4 Building development image..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") -f docker-compose.dev.yml build --no-cache
	@echo "3/4 Starting development container..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") -f docker-compose.dev.yml up -d --build
	@echo "4/4 Following logs (Ctrl+C to exit)..."
	@$(shell command -v docker-compose >/dev/null 2>&1 && echo "docker-compose" || echo "docker compose") -f docker-compose.dev.yml logs -f
