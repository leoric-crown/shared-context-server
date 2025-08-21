# Shared Context Server - Simple Makefile
# Essential development commands

.PHONY: help install dev test test-quick test-simplified test-backend test-all format lint type pre-commit quality clean docker

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
	@echo "🧪 Running tests with coverage..."
	@start=$$(date +%s); \
	if USE_SQLALCHEMY=true uv run pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml --timeout=30 --dist=loadscope; then \
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
	if uv run pytest -x --tb=short --timeout=30 --dist=loadscope; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "✅ Quick tests completed ($${duration}s)"; \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "❌ Quick tests failed ($${duration}s)"; \
		exit 1; \
	fi

test-simplified: ## Run simplified backend tests (covers both backends)
	@echo "🚀 Running simplified backend tests..."
	@start=$$(date +%s); \
	if uv run pytest tests/test_simplified_backend_switching.py -n 0 -v; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "✅ Simplified backend tests completed ($${duration}s)"; \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "❌ Simplified backend tests failed ($${duration}s)"; \
		exit 1; \
	fi

test-backend: ## Test both database backends
	@echo "🔧 Testing both database backends..."
	@start=$$(date +%s); \
	aio_status="❌"; sql_status="❌"; \
	echo "  → Testing aiosqlite backend..."; \
	if USE_SQLALCHEMY=false uv run pytest -q --maxfail=3 --timeout=30 --dist=loadscope; then \
		aio_status="✅"; \
	fi; \
	echo "  → Testing SQLAlchemy backend..."; \
	if USE_SQLALCHEMY=true uv run pytest -q --maxfail=3 --timeout=30 --dist=loadscope; then \
		sql_status="✅"; \
	fi; \
	end=$$(date +%s); \
	duration=$$((end - start)); \
	echo "📊 Backend test results ($${duration}s):"; \
	echo "   • aiosqlite: $$aio_status"; \
	echo "   • SQLAlchemy: $$sql_status"; \
	if [ "$$aio_status" = "✅" ] && [ "$$sql_status" = "✅" ]; then \
		echo "✅ Both backends passed"; \
	else \
		echo "❌ Some backends failed"; \
		exit 1; \
	fi

test-all: ## Run comprehensive test matrix with detailed status
	@echo "🧪 Running comprehensive test matrix..."
	@echo "================================================"
	@total_start=$$(date +%s); \
	passed=0; failed=0; \
	echo "1/5 Simplified backend tests (both backends)..."; \
	start=$$(date +%s); \
	if uv run pytest tests/test_simplified_backend_switching.py -n 0 -q; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ✅ Simplified tests passed ($${duration}s)"; \
		passed=$$((passed + 1)); \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ❌ Simplified tests failed ($${duration}s)"; \
		failed=$$((failed + 1)); \
	fi; \
	echo; \
	echo "2/5 Smoke tests (both backends)..."; \
	start=$$(date +%s); \
	smoke_passed=0; smoke_failed=0; \
	if USE_SQLALCHEMY=false uv run pytest tests/test_smoke.py -n 0 -q; then \
		smoke_passed=$$((smoke_passed + 1)); \
	else \
		smoke_failed=$$((smoke_failed + 1)); \
	fi; \
	if USE_SQLALCHEMY=true uv run pytest tests/test_smoke.py -n 0 -q; then \
		smoke_passed=$$((smoke_passed + 1)); \
	else \
		smoke_failed=$$((smoke_failed + 1)); \
	fi; \
	end=$$(date +%s); \
	duration=$$((end - start)); \
	if [ $$smoke_failed -eq 0 ]; then \
		echo "  ✅ Smoke tests passed ($$smoke_passed/$$((smoke_passed + smoke_failed))) ($${duration}s)"; \
		passed=$$((passed + 1)); \
	else \
		echo "  ❌ Smoke tests failed ($$smoke_passed/$$((smoke_passed + smoke_failed))) ($${duration}s)"; \
		failed=$$((failed + 1)); \
	fi; \
	echo; \
	echo "3/5 Integration & behavioral tests..."; \
	start=$$(date +%s); \
	if uv run pytest tests/integration/ tests/behavioral/ -q; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ✅ Integration tests passed ($${duration}s)"; \
		passed=$$((passed + 1)); \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ❌ Integration tests failed ($${duration}s)"; \
		failed=$$((failed + 1)); \
	fi; \
	echo; \
	echo "4/5 aiosqlite backend comprehensive..."; \
	start=$$(date +%s); \
	if USE_SQLALCHEMY=false uv run pytest tests/ --ignore=tests/test_simplified_backend_switching.py -q --maxfail=3; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ✅ aiosqlite backend passed ($${duration}s)"; \
		passed=$$((passed + 1)); \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ❌ aiosqlite backend failed ($${duration}s)"; \
		failed=$$((failed + 1)); \
	fi; \
	echo; \
	echo "5/5 SQLAlchemy backend comprehensive..."; \
	start=$$(date +%s); \
	if USE_SQLALCHEMY=true uv run pytest tests/ --ignore=tests/test_simplified_backend_switching.py -q --maxfail=3; then \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ✅ SQLAlchemy backend passed ($${duration}s)"; \
		passed=$$((passed + 1)); \
	else \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		echo "  ❌ SQLAlchemy backend failed ($${duration}s)"; \
		failed=$$((failed + 1)); \
	fi; \
	echo; \
	total_end=$$(date +%s); \
	total_duration=$$((total_end - total_start)); \
	echo "================================================"; \
	echo "📊 Test matrix summary (Total: $${total_duration}s):"; \
	echo "   • Passed: $$passed"; \
	echo "   • Failed: $$failed"; \
	echo "   • Total: $$((passed + failed))"; \
	if [ $$failed -eq 0 ]; then \
		echo "✅ All test variations passed! 🎉"; \
	else \
		echo "❌ Some test variations failed"; \
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
