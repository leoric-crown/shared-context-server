# Coverage Tracking Scripts

This directory contains scripts for monitoring and tracking test coverage progress toward the Phase 4 completion target of 85% overall coverage.

## Scripts Overview

### 1. `coverage_dashboard.py` - Real-time Coverage Dashboard
The main dashboard showing comprehensive coverage status and progress.

```bash
# Run full dashboard
python scripts/coverage_dashboard.py

# Watch mode (auto-refresh every 30 seconds)
python scripts/coverage_dashboard.py --watch

# Custom refresh interval
python scripts/coverage_dashboard.py --watch --interval 60
```

**Features:**
- Overall coverage status with progress bars
- Module-specific coverage targets and gaps
- Priority actions and recommendations
- Quick commands for common tasks

### 2. `coverage_tracker.py` - Coverage Progress Tracker
Focused tracker showing current vs target coverage for key modules.

```bash
# Show full coverage dashboard
python scripts/coverage_tracker.py

# Show specific module coverage
python scripts/coverage_tracker.py models.py
python scripts/coverage_tracker.py utils/performance.py
```

**Features:**
- Module coverage gaps and progress
- Priority module recommendations
- Module-specific test commands

### 3. `module_coverage.py` - Module-Specific Coverage Analysis
Detailed coverage analysis for individual modules.

```bash
# Analyze specific module
python scripts/module_coverage.py utils/performance.py --verbose --html

# List available modules
python scripts/module_coverage.py --list

# Run priority modules
python scripts/module_coverage.py --priority

# Use custom test file
python scripts/module_coverage.py models.py --test-file tests/unit/test_models_custom.py

# Create test template for module
python scripts/module_coverage.py models.py --create-template
```

**Features:**
- Module-specific coverage analysis
- HTML report generation
- Test file template creation
- Priority module batch processing

## Phase 4 Coverage Targets

| Module | Current | Target | Gap |
|--------|---------|--------|-----|
| `utils/performance.py` | ~80% | 85% | 5% |
| `utils/caching.py` | ~91% | 85% | ✓ |
| `models.py` | ~60% | 85% | 25% |
| `config.py` | ~77% | 85% | 8% |
| `database.py` | ~81% | 85% | 4% |
| `server.py` | ~87% | 85% | ✓ |
| `auth.py` | ~98% | 85% | ✓ |
| `scripts/cli.py` | ~62% | 85% | 23% |
| `tools.py` | ~0% | 85% | 85% |
| `scripts/dev.py` | ~0% | 85% | 85% |

## Quick Commands

```bash
# Full dashboard with real-time updates
python scripts/coverage_dashboard.py --watch

# Check specific module progress
python scripts/coverage_tracker.py models.py

# Analyze priority modules
python scripts/module_coverage.py --priority --html

# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html -n 0

# View HTML report
open htmlcov/index.html
```

## Configuration

The scripts use the following configuration from `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "*/conftest.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
fail_under = 85
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"
show_contexts = true
```

## Usage Tips

1. **Start with the dashboard**: `python scripts/coverage_dashboard.py` gives you the full picture
2. **Focus on priority modules**: Use the dashboard's recommendations to tackle the biggest gaps first
3. **Use HTML reports**: Add `--html` flag to get detailed line-by-line coverage analysis
4. **Watch mode for development**: Use `--watch` to monitor progress in real-time
5. **Module-specific analysis**: Use `module_coverage.py` when working on specific modules

## Integration with Development Workflow

These scripts are designed to integrate with the Phase 4 test development workflow:

1. **Assessment**: Use dashboard to identify priority modules
2. **Development**: Use module-specific analysis while writing tests
3. **Monitoring**: Use watch mode to track progress in real-time
4. **Validation**: Use full coverage runs to verify targets are met

The scripts automatically handle:
- Parallel execution conflicts with coverage
- Module path resolution
- HTML report generation
- Progress visualization
- Actionable recommendations
