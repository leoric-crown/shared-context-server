# Contributing

Thank you for your interest in contributing! This guide covers the essentials.

## Quick Start

### Prerequisites
- Python 3.10+ and [uv](https://docs.astral.sh/uv/)
- Git

### Development Setup
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/shared-context-server.git
cd shared-context-server

# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env

# Start development server
make dev
```

### Before You Submit
```bash
# Run all quality checks
make quality

# Run tests with coverage
make test

# Check individual components
make lint    # Code formatting and linting
make type    # Type checking
```

## Making Changes

### What We Welcome
- 🐛 **Bug fixes** - Check existing issues first
- ✨ **New features** - Discuss in an issue before implementing
- 📚 **Documentation** - Improvements, examples, clarifications
- 🧪 **Tests** - Coverage improvements, edge cases

### Code Style
- Follow existing patterns in the codebase
- Use type hints for all functions
- Maximum line length: 100 characters
- Add docstrings for public functions

### Commit Messages
Use conventional commits:
```
feat(auth): add JWT token refresh endpoint
fix(db): resolve connection pool exhaustion issue
docs(api): update authentication examples
```

## Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes** following our code style
3. **Test locally**: `make quality && make test`
4. **Update docs** if needed (README, API docs)
5. **Submit PR** with clear description

### PR Checklist
- [ ] Tests pass locally (`make test`)
- [ ] Code follows style guidelines (`make quality`)
- [ ] Documentation updated if needed
- [ ] Self-review completed

## Testing

### Test Structure
- `tests/unit/` - Individual function tests
- `tests/integration/` - Component interaction tests
- `tests/behavioral/` - End-to-end scenarios

### Coverage Requirement
- Minimum 84% line coverage
- New features must include tests
- Bug fixes must include regression tests

## Getting Help

- **Issues**: Bug reports and feature requests
- **Discussions**: General questions and ideas
- **Documentation**: See `docs/` folder

---

**Questions?** Check existing issues or start a discussion. We're here to help!

By contributing, you agree that your contributions will be licensed under the project's MIT License.
