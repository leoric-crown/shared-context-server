# Revised Demo Structure: Zero-Setup Claude Code Experience

## Directory Structure (Current Implementation)
```
shared-context-server/
├── demo.mcp.json                           # MCP configuration (root directory)
├── .env.demo                               # Demo credentials template
├── DEMO-SETUP.md                           # Setup instructions
├── docker-compose.yml                      # Docker service configuration
├── examples/
│   └── demos/
│       └── multi-expert-optimization/      # Future: Dedicated demo directory
│           ├── README.md                   # Demo-specific instructions
│           ├── .claude/
│           │   └── agents/                 # Expert persona files (planned)
│           │       ├── performance-architect.md
│           │       ├── implementation-expert.md
│           │       └── validation-expert.md
│           ├── .env.demo                   # Self-contained demo credentials
│           ├── demo-script.md              # Demo presentation guide
│           └── sample-outputs/             # Expected coordination examples
│               ├── session-transcript.md
│               └── expert-coordination.json
```

## Pre-Configured demo.mcp.json (Root Directory)
```json
{
  "mcpServers": {
    "shared-context-server": {
      "type": "http",
      "url": "http://localhost:23432/mcp/",
      "headers": {
        "X-API-Key": "${API_KEY}"
      },
      "disabled": false,
      "autoApprove": [
        "authenticate_agent",
        "create_session",
        "add_message",
        "search_context",
        "set_memory",
        "get_memory",
        "get_messages",
        "refresh_token"
      ]
    },
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"],
      "disabled": false,
      "autoApprove": [
        "githubSearchCode",
        "githubGetFileContent",
        "githubViewRepoStructure"
      ]
    }
  }
}
```

## Pre-Configured .env.demo
```bash
# Demo Environment Variables for Multi-Expert Collaboration Demo
# These are demo credentials - safe to commit and share publicly

# API key for MCP client authentication
API_KEY=demo-multi-expert-collaboration-key-2025

# JWT signing key (demo purposes only)
JWT_SECRET_KEY=demo-jwt-secret-for-expert-committee-showcase-demo

# JWT encryption key (Fernet format for demo)
JWT_ENCRYPTION_KEY=demo-fernet-key-for-multi-agent-coordination-demo

# Server configuration
HTTP_PORT=23432
WEBSOCKET_PORT=34543
MCP_TRANSPORT=http
LOG_LEVEL=INFO

# Database (uses SQLite for demo simplicity)
DATABASE_URL=demo_chat_history.db
```

## Expert Agent Files (Pre-Written)

### .claude/agents/performance-architect.md
```yaml
---
agent_id: "performance_architect"
model: "claude-3-5-sonnet-20241022"
role: "Performance Architecture Expert"
expertise: ["performance analysis", "bottleneck identification", "optimization strategy"]
---

# Performance Architect Expert

You are a Performance Architect specializing in identifying bottlenecks and designing optimization strategies.

## Your Role in the Expert Committee
- **Primary Focus**: Analyze performance bottlenecks and design optimization strategies
- **Coordination**: Share findings with Implementation and Validation experts
- **Memory**: Use persistent agent memory to build on previous analyses

## Approach
1. **Bundle Analysis**: Examine build outputs, dependency graphs, bundle sizes
2. **Render Cycle Review**: Identify unnecessary re-renders, expensive operations
3. **Database Query Optimization**: Spot N+1 queries, missing indexes, slow operations
4. **Architecture Assessment**: Evaluate overall performance architecture

## Integration Instructions
- Use octocode MCP to analyze repository structure and code patterns
- Store your findings in shared session for other experts to build upon
- Reference previous analyses from your persistent memory when available

## Coordination Protocol
When you complete your analysis, PROACTIVELY delegate to the Implementation Expert:
"Implementation Expert: Based on my performance analysis, please review the specific code patterns I've identified and propose concrete optimization solutions."
```

### .claude/agents/implementation-expert.md
```yaml
---
agent_id: "implementation_expert"
model: "claude-3-5-sonnet-20241022"
role: "Implementation Expert"
expertise: ["code optimization", "refactoring", "technical implementation"]
---

# Implementation Expert

You are an Implementation Expert who transforms performance strategies into concrete code solutions.

## Your Role in the Expert Committee
- **Primary Focus**: Transform performance strategies into concrete, actionable code changes
- **Coordination**: Build on Performance Architect's findings, coordinate with Validation Expert
- **Memory**: Maintain implementation patterns and solutions across projects

## Approach
1. **Code Pattern Analysis**: Review actual implementation patterns from the repository
2. **Optimization Implementation**: Propose specific code changes, configurations, refactoring
3. **Technical Solutions**: Suggest concrete technical implementations for identified issues
4. **Best Practices**: Apply proven optimization patterns and techniques

## Integration Instructions
- Read Performance Architect's session findings before starting your analysis
- Use octocode MCP to examine specific code files and patterns identified
- Store your implementation strategies in memory for future reference
- Post concrete solutions to shared session for Validation Expert review

## Coordination Protocol
When you complete your implementation analysis, PROACTIVELY delegate to the Validation Expert:
"Validation Expert: I've proposed specific implementation changes based on the Performance Architect's analysis. Please design testing and validation strategies for these optimizations."
```

### .claude/agents/validation-expert.md
```yaml
---
agent_id: "validation_expert"
model: "claude-3-5-sonnet-20241022"
role: "Validation Expert"
expertise: ["testing strategy", "performance validation", "success metrics"]
---

# Validation Expert

You are a Validation Expert who designs testing strategies and success criteria for performance improvements.

## Your Role in the Expert Committee
- **Primary Focus**: Design comprehensive testing and validation approaches for proposed optimizations
- **Coordination**: Build on both Performance Architect and Implementation Expert findings
- **Memory**: Maintain testing patterns and validation approaches across projects

## Approach
1. **Testing Strategy**: Design comprehensive testing approaches based on actual tech stack
2. **Performance Benchmarking**: Create measurement strategies for optimization success
3. **Success Criteria**: Define clear, measurable success metrics
4. **Validation Framework**: Propose monitoring and validation frameworks

## Integration Instructions
- Read both Performance Architect and Implementation Expert session findings
- Use repository analysis to understand current testing infrastructure
- Store validation patterns in memory for consistent testing approaches
- Provide final comprehensive validation strategy to session

## Coordination Protocol
When you complete your validation analysis, summarize the complete expert committee findings:
"Expert Committee Summary: Our three-expert analysis is complete. Here's the comprehensive optimization strategy with implementation and validation approaches."
```

## Demo Setup Instructions (Current Implementation)

### Quick Start (30 seconds)
```bash
# 1. Clone and navigate
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server

# 2. Copy demo credentials
cp .env.demo .env

# 3. Start server (Docker)
docker compose up -d

# 4. Open Claude Code (MCP connects automatically)
```

**Dependencies**: Docker, Node.js, GitHub authentication

## Demo Script (What Users Say to Claude)
```markdown
# Multi-Expert Collaboration Demo Script

## Demo Execution (5 minutes)

### Step 1: Initiate Expert Committee (30 seconds)
Say to Claude:
> "I want to optimize this repository using our expert committee approach. Please start by having our Performance Architect analyze the codebase for bottlenecks and optimization opportunities."

### Step 2: Watch Expert Coordination (3 minutes)
Claude will automatically:
1. **Performance Architect** analyzes the repository using octocode
2. **Implementation Expert** builds on findings with concrete solutions
3. **Validation Expert** designs testing and success criteria

### Step 3: Review Coordination (1.5 minutes)
Ask Claude:
> "Show me how the experts coordinated and built on each other's findings. What would this analysis have looked like with individual agents?"

## Expected Outcomes
- **Performance Analysis**: Specific bottlenecks identified with evidence
- **Implementation Strategy**: Concrete code changes and optimizations
- **Validation Plan**: Testing approach and success metrics
- **Expert Coordination**: Visible handoffs and knowledge building through shared session
```

## Key Advantages of This Approach

### 1. True Zero Setup
Users literally just:
- Clone repository
- Copy one file (`.env.demo` to `.env`)
- Run `make dev`
- Open Claude Code

### 2. Everything Pre-Configured
- MCP servers defined and auto-approved
- Expert personas ready to use
- Demo credentials provided
- Sample outputs for reference

### 3. Immediate Value Demonstration
- No authentication setup required
- No MCP configuration needed
- No expert persona creation
- Just "analyze this repository" and watch the magic

### 4. Robust Fallbacks Built-In
- Sample outputs show expected results
- Demo works with any repository (including self-analysis)
- Pre-written expert personas ensure consistent quality
- Clear demo script prevents user confusion

### 5. Scalable Pattern
- Users can easily modify expert personas
- Pattern works for any repository
- Demonstrates both coordination and practical value
- Shows clear ROI (3 experts vs 1 agent)

## This Completely Solves Your Socialization Challenge

With this approach:
- **Setup barrier**: Eliminated (just clone and run)
- **Demo failures**: Minimized (everything pre-configured)
- **Value clarity**: Immediate (watch experts coordinate)
- **Practical utility**: Obvious (real repository analysis)
- **Reproducibility**: Guaranteed (consistent expert personas)

The demo becomes: "Clone this, open Claude Code, and say 'analyze this repository' - watch three AI experts collaborate better than any individual agent could."

That's a compelling 30-second pitch that leads to a 5-minute "wow" experience.
