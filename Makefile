# Shared Context Server - Simple Makefile
# Essential development commands

.PHONY: help install dev test lint type quality clean

# Default target - show help
help:
	@echo "Available commands:"
	@echo "  install  - Install dependencies (uv sync --dev)"
	@echo "  dev      - Start development server with hot reload"
	@echo "  test     - Run tests with coverage"
	@echo "  lint     - Run ruff linting and format checks"
	@echo "  type     - Run mypy type checking"
	@echo "  quality  - Run all quality checks (lint + type + security)"
	@echo "  clean    - Clean caches and temporary files"
	@echo "  help     - Show this help message"

# Install dependencies
install:
	uv sync --dev

# Start development server
dev:
	@echo "Starting development server with hot reload..."
	uv run python -m shared_context_server.scripts.dev

# Run tests with coverage
test:
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# Format files
format:
	uv run ruff format

# Run linting checks
lint:
	uv run ruff check --fix

# Run type checking
type:
	uv run mypy src

# Run pre-commit hooks
pre-commit:
	uv run pre-commit run

# Run all quality checks (mirrors CI)
quality: format lint type
	uv run pip-audit

# Clean caches and temporary files
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
	rm -rf htmlcov/ coverage.xml .coverage
	rm -rf *.db test_*.db
	rm -rf logs/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
