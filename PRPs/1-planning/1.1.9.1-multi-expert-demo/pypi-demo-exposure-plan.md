# PyPI Demo Exposure Plan

## Goal
Expose Multi-Expert Collaboration Demo via uvx and PyPI published package to eliminate repository cloning requirement.

## Current Challenge
Demo currently requires cloning repository to access:
- Expert persona files in `.claude/agents/`
- Demo-specific docker-compose.yml
- Directory structure for proper setup

## Proposed Solutions

### Option 1: Demo Subcommand (Recommended)
Add a `demo` subcommand to the CLI that bootstraps the demo environment:

```bash
# Instead of cloning repo
uvx shared-context-server demo multi-expert-collaboration
# Creates: ./multi-expert-demo/ with all required files
```

**Implementation:**
- Add `demo` subcommand to `scripts/cli.py`
- Package expert personas as embedded resources
- Generate demo directory structure programmatically
- Include demo-specific docker-compose.yml as template
- Integrate with existing `generate_keys.py --demo` functionality

### Option 2: Package Data Integration
Include demo files as package resources and make them accessible:

```bash
uvx shared-context-server --demo-setup multi-expert-collaboration
# Sets up demo in current directory
```

**Implementation:**
- Add demo files to `pyproject.toml` as package data
- Update `create_env_file()` to handle packaged resources
- Use `importlib.resources` for cross-platform file access

### Option 3: Interactive Demo Bootstrap
Create an interactive setup command:

```bash
uvx shared-context-server setup-demo
# Interactive wizard that creates demo environment
```

## Recommended Implementation Plan

1. **Add demo subcommand to CLI** - Extend existing argument parser
2. **Package expert personas** - Include `.claude/agents/*.md` as package resources
3. **Template system** - Generate docker-compose.yml and README.md from templates
4. **Integration** - Leverage existing key generation and validation code
5. **Documentation** - Update main README with new uvx demo workflow

## Benefits
- ✅ No repository cloning required
- ✅ Single command demo setup
- ✅ Consistent with existing CLI architecture
- ✅ Maintains security (proper key generation)
- ✅ Version-synchronized with package releases

## Next Steps
1. Test current demo functionality first
2. Implement Option 1 (Demo Subcommand) for cleanest UX
3. Update package configuration and documentation
