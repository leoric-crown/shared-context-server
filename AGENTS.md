# Repository Guidelines

## Project Structure & Module Organization
- `src/shared_context_server/`: Core server (auth, database, HTTP/WebSocket, CLI, tools). Entrypoints in `scripts/cli.py` and `server.py`.
- `tests/`: Pytest suite grouped by unit/integration/behavioral; add new tests near related modules.
- `docs/`: Project docs; update when changing public behavior.
- `scripts/` (repo root): Utility scripts for versioning and CI tasks.
- Assets: `templates/`, `static/`; database SQL in repo root (`database_*.sql`).

## Build, Test, and Development Commands
- `make install`: Sync dev deps and install pre-commit hooks (uses `uv`).
- `make dev`: Start dev server with hot reload.
- `make run`: Run production CLI locally (`shared-context-server --transport http`).
- `make test`: Pytest with coverage reports (HTML/XML).
- `make test-quick`: Faster pytest run without coverage.
- `make format` / `make lint` / `make type`: Format (Ruff), lint (Ruff), type-check (mypy).
- `make pre-commit`: Run make format lint type and pre-commit hooks with basic file hygiene.
- `make quality`: Format + lint + types + `pip-audit`.
- Docker: `make docker-dev` (hot reload), `make docker` (GHCR image).

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indents, line length ~88 (Ruff/Black style, double quotes).
- Type hints required for public functions; mypy strict settings enabled.
- Names: modules/files `snake_case`, classes `PascalCase`, functions/vars `snake_case`.
- Run `make format && make lint` before committing.

## Testing Guidelines
- Framework: Pytest with asyncio and xdist; markers: `unit`, `integration`, `behavioral`, `performance`.
- Coverage gate: configured in `pyproject.toml` (fail_under=70). Aim higher for new code.
- Naming: place files under `tests/<area>/test_*.py` and mirror source structure.
- Quick checks: `make test-quick`; full CI parity: `make test`.

## Commit & Pull Request Guidelines
- Conventional Commits, e.g.: `feat(auth): add token refresh`, `fix(db): handle pool exhaustion`, `docs(api): update examples`.
- Branches: `feature/*`, `fix/*`, `chore/*`.
- PRs: clear description, link issues, include rationale and risk notes; ensure `make quality && make test` pass. Add doc updates if behavior changes.

## Security & Configuration Tips
- Run `uv run scs setup` to generate an .env file with fresh keys.
- Generate MCP client config via CLI, e.g.: `uv run scs client-config claude -s user --copy`.
- Prefer `docker-compose.dev.yml` for isolated local runs.
