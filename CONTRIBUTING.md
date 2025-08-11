# Contributing to Shared Context MCP Server

Thank you for your interest in contributing! This guide will help you get started with contributing to the Shared Context MCP Server project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Contributions](#making-contributions)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:
- Be respectful and constructive in discussions
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- SQLite 3.38+

### First Time Contributors
Look for issues labeled with:
- `good first issue` - Simple issues perfect for beginners
- `help wanted` - Issues where we need community help
- `documentation` - Documentation improvements

## Development Setup

### 1. Fork and Clone
```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/shared-context-server.git
cd shared-context-server
git remote add upstream https://github.com/ORIGINAL/shared-context-server.git
```

### 2. Install Dependencies
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync --all-extras

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration
```

### 3. Set Up Pre-commit Hooks
```bash
uv run pre-commit install
```

### 4. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

## Making Contributions

### Types of Contributions

#### 🐛 Bug Fixes
1. Check if the bug is already reported in Issues
2. If not, create a new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information
3. Reference the issue in your PR

#### ✨ New Features
1. Discuss the feature in an issue first
2. Get consensus on the approach
3. Implement following our architecture patterns
4. Add comprehensive tests
5. Update documentation

#### 📚 Documentation
- Fix typos or clarify existing docs
- Add examples and use cases
- Improve API documentation
- Translate documentation

#### 🧪 Tests
- Increase test coverage
- Add edge case tests
- Improve test performance
- Add integration tests

## Coding Standards

### Python Style Guide
We follow PEP 8 with these additions:
- Maximum line length: 100 characters
- Use type hints for all functions
- Docstrings for all public functions/classes

### Code Quality Tools
```bash
# Use Makefile for common tasks (recommended)
make quality                # Run all quality checks
make test                   # Run tests with coverage
make lint                   # Linting and formatting
make type                   # Type checking

# Or run tools directly
uv run ruff check .          # Linting
uv run ruff format .         # Formatting
uv run mypy src/            # Type checking
uv run pytest tests/        # Tests
```

### File Structure
```python
"""
Module docstring explaining purpose.
"""

from __future__ import annotations  # Always use future annotations

import standard_library_imports
import third_party_imports

from local_imports import specific_items


class ExampleClass:
    """Class docstring with description."""

    def __init__(self, param: str) -> None:
        """Initialize with parameter."""
        self.param = param

    async def async_method(self) -> dict[str, Any]:
        """Async method with type hints."""
        return {"result": "value"}
```

### Commit Messages
Follow conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(auth): add JWT token refresh endpoint
fix(db): resolve connection pool exhaustion issue
docs(api): update authentication examples
test(security): add auth bypass test cases
```

## Testing Requirements

### Test Coverage
- Minimum 85% line coverage required
- New features must include tests
- Bug fixes must include regression tests

### Running Tests
```bash
# Use Makefile (recommended)
make test                    # Run all tests with coverage

# Or run directly
uv run pytest tests/         # Run all tests
uv run pytest tests/test_specific.py  # Run specific test file
uv run pytest tests/ --cov=src --cov-report=html  # With coverage
uv run pytest tests/ -m "not slow"    # Run only fast tests
```

### Writing Tests

### Test Categories
- `tests/unit/` - Unit tests for individual functions
- `tests/integration/` - Integration tests for components
- `tests/behavioral/` - End-to-end behavioral tests
- `tests/security/` - Security-specific tests
- `tests/performance/` - Performance benchmarks

## Documentation

### Docstring Format
```python
def function_name(param1: str, param2: int = 0) -> dict[str, Any]:
    """
    Brief description of function purpose.

    Longer description if needed, explaining behavior,
    edge cases, or important notes.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter with default

    Returns:
        Description of return value structure

    Raises:
        ValueError: When validation fails
        DatabaseError: When database operation fails

    Example:
        >>> result = function_name("test", 42)
        >>> print(result["status"])
        "success"
    """
```

### API Documentation
- Update `docs/api-reference.md` for new endpoints
- Include request/response examples
- Document error codes and meanings
- Add integration examples

### README Updates
Update README.md when:
- Adding new features
- Changing installation process
- Modifying configuration
- Adding new dependencies

## Pull Request Process

### Before Submitting
1. **Test Locally**
   ```bash
   # Use Makefile for all quality checks
   make quality
   make test

   # Or run individual tools
   uv run ruff check .
   uv run mypy src/
   uv run pytest tests/
   ```

2. **Update Documentation**
   - API changes → Update API docs
   - New features → Update README
   - Configuration → Update .env.example

3. **Self Review**
   - Check diff for unintended changes
   - Verify all tests pass
   - Ensure commits are clean

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Coverage maintained/improved

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
```

### Review Process
1. Automated checks run (CI/CD)
2. Code review by maintainers
3. Address feedback
4. Approval from 1+ maintainers
5. Merge when all checks pass

### After Merge
- Delete your feature branch
- Pull latest main
- Thank reviewers!

## Release Process

### Version Numbering
We use Semantic Versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes

### Release Checklist
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release PR
5. Tag release after merge
6. Publish to PyPI (maintainers only)

## Development Tips

### Hot Reload Development
```bash
# Use Makefile (recommended)
make dev

# Or run directly
MCP_TRANSPORT=http HTTP_PORT=8000 uv run python -m shared_context_server.scripts.dev
```

### Database Migrations
```bash
# Create new migration
uv run python migrations/create_migration.py "description"

# Run migrations
uv run python migrations/run_migrations.py
```

### Performance Testing
```bash
# Run benchmarks
uv run pytest tests/performance/ -v --benchmark-only

# Profile specific operation
uv run python -m cProfile -s cumulative src/profile_script.py
```

## Getting Help

### Resources
- [Documentation](./docs/)
- [API Reference](./docs/api-reference.md)
- [Architecture Guide](./docs/architecture.md)
- [GitHub Issues](https://github.com/shared-context-server/issues)

### Communication Channels
- GitHub Issues - Bug reports, feature requests
- GitHub Discussions - General questions, ideas

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

---

**Thank you for contributing to Shared Context MCP Server!** 🎉

Your efforts help make this project better for everyone in the community.
