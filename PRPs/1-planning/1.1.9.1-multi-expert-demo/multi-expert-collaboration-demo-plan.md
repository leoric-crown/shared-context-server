# Multi-Expert Collaboration Demo for Shared Context Server 1.1.9

---
session_id: session_dd6ade04de0349ed
session_purpose: "Feature planning: Multi-Expert Collaboration Demo for shared-context-server 1.1.9 release"
created_date: 2025-01-26T06:39:14.672186+00:00
stage: "1-planning"
planning_type: "demo_showcase"
---

## Executive Summary

**Goal**: Create a compelling demo that showcases shared-context-server's 1.1.9 multi-agent coordination capabilities using Claude Code with external expert persona prompts.

**Key Insight**: Expert personas should be external demo materials (.md files in .claude/agents/) rather than built into the shared-context-server itself. The server provides coordination infrastructure while expert identities exist as reusable demo assets.

**Demo Concept**: "AI Expert Committee" that analyzes and optimizes real GitHub repositories through coordinated specialist agents, showcasing both the server's capabilities and practical MCP ecosystem integration.

## Planning Context

### User Requirements Validated
- Focus on Claude Code integration and usage patterns
- Expert personas as external prompts, not built into system
- Zero-setup demo approach that works with real-world subjects
- Showcase 1.1.9 milestone capabilities for effective socialization
- Leverage existing .claude/agents structure and proven patterns

### Research Findings Applied
- **"3 Amigo Agents" pattern** (coined by George Vetticaden) proven most effective for demos - adapts the traditional "Three Amigos" methodology (Business Analyst + Developer + Tester collaboration on user stories) to AI agent coordination (Architect → Implementer → Validator)
- YAML frontmatter + system prompt structure from Claude Code best practices
- "PROACTIVELY" keyword enables automatic agent delegation
- Model optimization: Sonnet recommended for development-focused demo agents
- Visible handoffs and progress indicators crucial for demo success

## Technical Architecture

### Demo Structure
```
/shared-context-server/
├── examples/
│   └── demos/
│       └── multi-expert-optimization/
│           ├── README.md                    # Demo setup guide
│           ├── .claude/
│           │   └── agents/
│           │       ├── performance-architect.md
│           │       ├── implementation-expert.md
│           │       └── validation-expert.md
│           ├── .mcp.json                    # MCP dependencies
│           ├── demo-script.md               # Presenter guide
│           └── coordination-examples/       # Sample outputs
│               ├── session-messages.json
│               └── expert-memory-samples.json
```

### Expert Personas (3 Amigo Pattern - George Vetticaden)

#### Performance Architect Expert
- **agent_id**: `"performance_architect"` (persistent memory across demos)
- **Role**: Analyze performance bottlenecks and design optimization strategies
- **Approach**: Bundle analysis, render cycle review, database query optimization
- **Integration**: Uses octocode MCP for real GitHub repository analysis

#### Implementation Expert
- **agent_id**: `"implementation_expert"` (persistent memory)
- **Role**: Transform performance strategies into concrete code solutions
- **Approach**: Code changes, configuration updates, technical implementation
- **Integration**: Reviews real codebase patterns, suggests specific optimizations

#### Validation Expert
- **agent_id**: `"validation_expert"` (persistent memory)
- **Role**: Test performance improvements and validate outcomes
- **Approach**: Benchmarking, testing strategies, success criteria definition
- **Integration**: Creates measurement approaches based on actual tech stacks

### Coordination Workflow

#### Authentication & Session Setup
```python
# Main Claude coordinates expert committee
session_id = create_session(purpose="Repository Performance Optimization Demo")
coordinator_token = authenticate_agent("demo_coordinator", "admin")

# Provision persistent expert tokens
perf_token = authenticate_agent("performance_architect", "claude")
impl_token = authenticate_agent("implementation_expert", "claude")
val_token = authenticate_agent("validation_expert", "claude")
```

#### Expert Coordination Flow
1. **Performance Architect** (3 mins):
   - Inherits previous analysis memories via persistent agent_id
   - Uses octocode to analyze repository structure, dependencies
   - Posts findings to session: bottlenecks, optimization opportunities
   - Stores strategy in memory for future reference

2. **Implementation Expert** (3 mins):
   - Reads architect's session findings
   - Reviews actual code patterns from repository
   - Posts concrete solutions: code splitting, lazy loading, optimizations
   - Coordinates with validation expert on testing approaches

3. **Validation Expert** (2 mins):
   - Reviews both architect and implementation session history
   - Designs testing strategy based on actual tech stack
   - Posts validation approach: performance budgets, monitoring
   - Provides success criteria and measurement strategy

## Demo Subjects & Use Cases

### Primary: Personal Project Analysis ⭐ **Recommended**
**Subject**: "Optimize your recent coding project"
**Setup**: User provides their own repository or project directory
**Benefits**:
- Immediately personal and valuable to the user
- Real, actionable insights they can implement
- Demonstrates practical utility, not just coordination
- User engagement through personal investment
- Every demo is unique and relevant

**Ideal Projects**:
- Recent side projects or hackathon entries
- Work projects they can share publicly
- Personal experiments or learning projects
- Any codebase they've been "vibing" with recently
- Projects where they've felt performance could be better

### Alternative Use Cases

#### Popular Repository Analysis (Fallback Option)
- **Subject**: Well-known open source projects
- **Setup**: Provide GitHub URL to popular repository
- **Benefits**: Works when users don't have projects to share
- **Examples**: `microsoft/vscode`, `facebook/react`, `vercel/next.js`
- **Use Case**: Conference demos, educational workshops

#### Web Performance Audit (No GitHub Required)
- **Subject**: Live website performance analysis
- **Setup**: User provides website URL they own or work on
- **MCP Integration**: crawl4ai for page structure analysis
- **Benefits**: Works without GitHub access, broader applicability

#### Self-Analysis Demo (Meta Demonstration)
- **Subject**: Optimize shared-context-server itself
- **Setup**: Analyze the current project
- **Benefits**: Meta-demonstration, always available
- **Drawback**: Less engaging for audiences

## MCP Dependencies & Configuration

### Required .mcp.json Configuration
```json
{
  "mcpServers": {
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"],
      "description": "GitHub repository analysis and code search",
      "required": true
    },
    "shared-context-server": {
      "command": "uv",
      "args": ["run", "python", "-m", "shared_context_server.scripts.cli"],
      "description": "Multi-agent coordination and session management",
      "required": true,
      "env": {
        "API_KEY": "your-api-key-here",
        "JWT_SECRET_KEY": "your-jwt-secret-key-here",
        "JWT_ENCRYPTION_KEY": "your-jwt-encryption-key-here"
      }
    }
  }
}
```

### ⚠️ Critical Setup Requirements

#### GitHub Authentication for octocode (Required)
**octocode requires GitHub authentication to function.** Choose one option:

**Option A: GitHub CLI (Recommended)**
```bash
gh auth login
```

**Option B: Environment Variable**
```bash
export GITHUB_TOKEN="your_github_personal_access_token"
```

**Option C: Authorization Header Format**
```bash
export Authorization="Bearer your_github_personal_access_token"
```

**Getting a GitHub Personal Access Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `public_repo` scope (for public repos)
3. For private repos, add `repo` scope

#### Shared Context Server Environment Variables (Required)
**The shared-context-server requires three environment variables:**

```bash
# Generate API key (any secure string)
export API_KEY="demo-api-key-$(date +%s)"

# Generate JWT secret (32+ characters recommended)
export JWT_SECRET_KEY="demo-jwt-secret-key-for-multi-expert-demo-$(date +%s)"

# Generate JWT encryption key (Fernet key format)
export JWT_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

**Alternative: Use project's key generation script**
```bash
cd shared-context-server/
./scripts/generate-keys.sh
# Follow the script's instructions to set environment variables
```

**Demo Failure Prevention:**
- Test octocode authentication before demo: `npx octocode-mcp --test`
- Test shared-context-server startup with all env vars set
- Have backup demo materials ready in case of auth issues
- Consider using popular public repositories to avoid private repo access needs

### Optional MCP Servers (Enhanced Functionality)
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
      "description": "Complex architectural decision analysis"
    }
  }
}
```

### Alternative MCP Configurations

#### Minimal Setup (GitHub Analysis Only)
```json
{
  "mcpServers": {
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"]
    },
    "shared-context-server": {
      "command": "make",
      "args": ["dev"]
    }
  }
}
```

#### Self-Contained Setup (No External Dependencies)
```json
{
  "mcpServers": {
    "shared-context-server": {
      "command": "make",
      "args": ["dev"]
    }
  }
}
```

#### Alternative Shared Context Server Setup
**Environment Variables in .mcp.json:**
```json
{
  "shared-context-server": {
    "command": "uv",
    "args": ["run", "python", "-m", "shared_context_server.scripts.cli"],
    "env": {
      "API_KEY": "demo-api-key-12345",
      "JWT_SECRET_KEY": "demo-jwt-secret-key-for-multi-expert-demo-12345",
      "JWT_ENCRYPTION_KEY": "your-generated-fernet-key-here"
    }
  }
}
```

**Using make dev (Development Mode):**
```bash
# Set environment variables first
export API_KEY="demo-api-key-$(date +%s)"
export JWT_SECRET_KEY="demo-jwt-secret-key-$(date +%s)"
export JWT_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# Then use make dev
make dev
```

## Implementation Plan

### Phase 1: Core Demo Assets (Week 1)
- [ ] Create .claude/agents/ expert persona files
- [ ] Develop .mcp.json with required dependencies
- [ ] Write demo-script.md with presenter guidance
- [ ] Create README.md with setup instructions

### Phase 2: Testing & Refinement (Week 2)
- [ ] Test coordination workflow with real repositories
- [ ] Refine expert personas based on interaction patterns
- [ ] Validate MCP integration and error handling
- [ ] Create sample coordination outputs for reference

### Phase 3: Documentation & Packaging (Week 3)
- [ ] Complete presenter guide with timing and talking points
- [ ] Document alternative use cases and fallback options
- [ ] Create troubleshooting guide for common issues
- [ ] Package demo materials for distribution

### Phase 4: Release Integration (Week 4)
- [ ] Integrate demo with 1.1.9 release materials
- [ ] Create blog post with demo walkthrough
- [ ] Add to documentation as showcase example
- [ ] Distribute to community and potential users

## Success Criteria

### Technical Demonstration
- [ ] Multi-agent coordination through shared-context-server sessions
- [ ] Persistent expertise via consistent agent_id memory inheritance
- [ ] Real-time collaboration with visible handoffs and progress
- [ ] Role-based access control with JWT authentication
- [ ] MCP ecosystem integration (octocode for GitHub analysis)

### Business Impact
- [ ] Faster problem-solving through specialized expertise division
- [ ] Knowledge preservation across AI interactions and demo sessions
- [ ] Scalable AI workflows for complex development tasks
- [ ] Reproducible collaboration patterns for real-world applications

### User Experience
- [ ] Zero artificial setup - works with any GitHub repository
- [ ] Dynamic content - different repository each demo run
- [ ] Educational value - audiences learn optimization techniques
- [ ] Clear progression - visible expert handoffs and coordination
- [ ] Compelling narrative - AI committee solving real problems

## Risk Mitigation

### GitHub Authentication Risks
- **Risk**: GitHub authentication fails during demo
- **Mitigation**: Test authentication beforehand with `gh auth status`
- **Fallback**: Use self-analysis demo (analyze shared-context-server itself)
- **Backup**: Pre-recorded coordination examples

### MCP Dependency Risks
- **Risk**: octocode MCP server unavailable or failing
- **Mitigation**: Alternative use cases (self-analysis without external deps)
- **Fallback**: Pre-analyzed repository examples with cached results

### Coordination Complexity
- **Risk**: Expert coordination appears confusing or chaotic
- **Mitigation**: Clear demo script with timing and talking points
- **Fallback**: Simplified 2-agent coordination if needed

### Technical Setup Issues
- **Risk**: Demo environment failures during presentation
- **Mitigation**: Pre-recorded coordination examples as backup
- **Fallback**: Presentation slides showing expected coordination flow

## Future Enhancements

### MCP Prompt Templates
- Convert successful demo personas into reusable MCP prompt templates
- Enable programmatic expert committee instantiation
- Support custom expert types for different domains

### Advanced Coordination Patterns
- Implement conflict resolution when experts disagree
- Add dynamic expert routing based on problem complexity
- Support larger expert committees (5+ agents)

### Integration Extensions
- GitHub integration for automated optimization PRs
- Performance monitoring integration for validation
- Custom repository analysis pipelines

---

**Planning Session Reference**: session_dd6ade04de0349ed
**Research Context**: research_claude_subagents_demo_patterns_20250826
**Next Steps**: Use `create-prp` to transform this planning into detailed implementation specifications
