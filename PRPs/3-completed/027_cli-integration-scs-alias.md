# PRP-027: CLI Integration and Enhancement with scs Alias

---
**Stage**: 2-prps
**Created**: 2025-08-27
**Planning Source**: Live investigation and analysis session
**Complexity Assessment**: Medium (multi-file integration, backward compatibility)
**Estimated Implementation**: 4-6 hours
---

## Research Context & Architectural Analysis

### Investigation Findings
During comprehensive CLI investigation, we discovered:

**Current CLI Architecture:**
- Main entry point: `shared-context-server` command via `src/shared_context_server/scripts/cli.py`
- Limited subcommands: `client-config`, `status`
- Enhanced `scripts/setup.py` exists but is completely disconnected from CLI
- Stale references to old `scripts/generate_keys.py` throughout codebase

**Key Discovery:** The `scripts/setup.py` has evolved into a comprehensive setup tool with rich functionality (key generation, demo mode, deployment guidance, export formats) but remains isolated from the main CLI interface.

**Architectural Scope:**
- CLI entry points in `pyproject.toml`
- CLI implementation in `src/shared_context_server/scripts/cli.py`
- Setup functionality in `scripts/setup.py`
- References across multiple files (config.py, auth_secure.py, database_manager.py, etc.)

### Existing Patterns to Leverage
- Clean subcommand structure already established
- Argument parsing with argparse
- Color-coded terminal output in setup.py
- Configuration validation patterns
- Error handling with helpful user guidance

## Implementation Specification

### Core Requirements

#### 1. Add `scs` Command Alias
- Add shorter `scs` entry point alongside existing `shared-context-server`
- Both commands should provide identical functionality
- Maintain full backward compatibility

#### 2. Integrate Setup Functionality as Subcommands
Transform isolated `scripts/setup.py` into integrated CLI subcommands:

```bash
# Current isolation:
python scripts/setup.py --demo --uvx

# New integration:
scs setup demo uvx
```

#### 3. Clean Positional Argument Design
Replace verbose flags with clean positional arguments:

```bash
scs setup                    # Basic setup (keys + .env + show deployment options)
scs setup docker            # Docker-focused commands
scs setup uvx               # uvx-focused commands
scs setup demo              # Demo mode (repo context only)
scs setup export json       # Export keys as JSON
scs setup --force           # Force overwrite (flag modifier)
```

#### 4. Repository vs Global Context Separation
- **Global CLI**: General setup features that work anywhere
- **Repo-only**: Demo mode stays as `python scripts/setup.py --demo` (requires repo structure)
- **Clean separation**: No complex path detection logic

### Integration Points

#### Entry Point Configuration
**File**: `pyproject.toml`
```toml
[project.scripts]
shared-context-server = "shared_context_server.scripts.cli:main"
scs = "shared_context_server.scripts.cli:main"
```

#### CLI Implementation Enhancement
**File**: `src/shared_context_server/scripts/cli.py`
- Add `setup` subcommand with positional argument parsing
- Import and call existing setup.py functions
- Maintain all existing server operation functionality
- Preserve client-config and status subcommands

#### Setup Function Integration
**Approach**: Import existing functions from `scripts/setup.py`
- Minimal modification of proven setup.py logic
- CLI layer handles argument parsing and calls setup functions
- Preserve all current setup.py functionality and safety checks

### Data Model Changes
**None required** - This is purely a CLI interface enhancement that leverages existing functionality.

### Interface Requirements

#### Command Structure
```bash
# Server Operations (existing)
scs                          # STDIO server (default)
scs --transport http         # HTTP server

# Setup Operations (NEW)
scs setup                    # Basic setup
scs setup docker            # Docker commands
scs setup uvx               # uvx commands
scs setup export json       # Export as JSON
scs setup --force           # Force overwrite

# Client Operations (existing)
scs client-config claude    # Generate Claude config
scs status                   # Server status
```

#### Help System Enhancement
```bash
scs --help                   # Show all commands
scs setup --help             # Show setup options
scs client-config --help     # Show client options
```

## Quality Requirements

### Testing Strategy
**Unit Tests:**
- Test new subcommand argument parsing
- Verify setup function integration
- Test both entry points (`shared-context-server` and `scs`)

**Integration Tests:**
- End-to-end CLI command execution
- Setup functionality through CLI interface
- Backward compatibility validation

**Behavioral Tests:**
- User workflow validation (setup → server start)
- Error message consistency and helpfulness
- Cross-platform compatibility

### Documentation Needs
**User-Facing Documentation:**
- Update README.md with new `scs` command examples
- Update demo documentation to show new CLI usage
- Add CLI reference documentation

**Developer Documentation:**
- Document CLI architecture and extension patterns
- Update CLAUDE.md with new command patterns

### Performance Considerations
- Setup operations are one-time activities (no performance concerns)
- CLI startup time should remain fast
- Import optimization for setup functions

## Coordination Strategy

### Recommended Approach: **Direct Agent Implementation**

**Rationale:**
- **Medium Complexity**: Multi-file changes but clear, well-defined scope
- **Established Patterns**: Leverages existing CLI and setup.py patterns
- **Low Risk**: No complex architectural changes, mostly integration work
- **Clear Requirements**: Specific command structure and functionality defined

**Implementation Phases:**

#### Phase 1: Core Integration (2-3 hours)
1. Update `pyproject.toml` with `scs` alias
2. Add `setup` subcommand to CLI with basic argument parsing
3. Import and integrate key setup.py functions
4. Test basic `scs setup` functionality

#### Phase 2: Complete Integration (1-2 hours)
5. Implement all positional arguments (docker, uvx, export, etc.)
6. Add proper help text and error handling
7. Ensure backward compatibility

#### Phase 3: Cleanup & Documentation (1-2 hours)
8. Update all stale references from `generate_keys.py` to `scs setup`
9. Update documentation and README files
10. Final testing and validation

### Risk Mitigation
**Backward Compatibility:** Maintain existing `shared-context-server` command unchanged
**Setup.py Preservation:** Keep existing script functional for repo-only demo mode
**Gradual Migration:** Update references incrementally to avoid breaking changes

### Dependencies
- No external dependencies required
- Existing setup.py functions remain unchanged
- CLI framework already established

## Success Criteria

### Functional Success
- [x] `scs` command alias works identically to `shared-context-server`
- [x] `scs setup` generates keys and .env file correctly
- [x] `scs setup docker` shows Docker deployment guidance
- [x] `scs setup uvx` shows uvx deployment guidance
- [x] `scs setup export json` outputs keys in JSON format
- [x] All existing CLI functionality remains unchanged
- [x] Backward compatibility maintained for existing users

### Integration Success
- [x] Setup functionality accessible through standard CLI patterns
- [x] Help system provides clear guidance for all commands
- [x] Error messages are consistent and helpful
- [x] Demo mode remains repo-only without breaking global CLI

### Quality Gates
**Testing Requirements:**
- Unit tests pass for new CLI functionality
- Integration tests validate end-to-end workflows
- Backward compatibility tests ensure no regressions

**Documentation Requirements:**
- README updated with `scs` command examples
- All stale references updated to new CLI commands
- CLI help text is comprehensive and accurate

**Code Quality:**
- Linting and type checking pass
- No code duplication between CLI and setup.py
- Clean separation between global and repo-only functionality

## Implementation Context

### Files to Modify
1. **`pyproject.toml`** - Add `scs` entry point
2. **`src/shared_context_server/scripts/cli.py`** - Add setup subcommand
3. **`src/shared_context_server/scripts/cli.py`** - Update error messages (stale references)
4. **`src/shared_context_server/config.py`** - Update error messages
5. **`src/shared_context_server/auth_secure.py`** - Update error messages
6. **`src/shared_context_server/database_manager.py`** - Update error messages
7. **`README.md`** - Update examples to use `scs`
8. **`examples/demos/multi-expert-optimization/README.md`** - Update CLI examples

### Integration Approach
- **Import Strategy**: Import setup functions from `scripts.setup` module
- **Argument Mapping**: Map CLI positional args to setup.py function parameters
- **Error Handling**: Preserve existing setup.py error messages and user guidance
- **Output Consistency**: Maintain setup.py's color-coded output and formatting

### Success Validation
The implementation is successful when:
1. Users can type `scs setup` and get keys + .env file created
2. Users can discover all functionality through `scs --help`
3. Existing `shared-context-server` users experience no changes
4. Demo mode continues to work for repo contributors
5. All stale references are updated to new CLI patterns

**Completion Estimate**: 4-6 hours for complete implementation and testing
**Risk Level**: Low-Medium (established patterns, clear requirements, good separation of concerns)
