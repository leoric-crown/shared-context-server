# Shared Context Server - Simple Makefile
# Essential development commands

.PHONY: help install dev test format lint type pre-commit quality clean docker

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

format: ## Format files using ruff
	uv run ruff format

lint: ## Run linting checks
	uv run ruff check --fix

type: ## Run type checking
	uv run mypy src

pre-commit: ## Run pre-commit hooks
	uv run pre-commit run

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
