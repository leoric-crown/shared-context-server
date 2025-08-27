# Multi-Expert Collaboration Demo

**Transform AI from individual agents into coordinated expert committees**

## Content Navigation

| Symbol | Meaning | Time Investment |
|--------|---------|----------------|
| 🚀 | Quick start | 2-3 minutes |
| 🎯 | Demo script | 5-7 minutes |
| 🔧 | Configuration | 5-10 minutes |
| 💡 | Why this works | Context only |

---

## 🎯 Quick Understanding (30 seconds)

**The Demo**: Watch three AI experts (Performance Architect → Implementation Expert → Validation Expert) collaborate autonomously to analyze any codebase more effectively than a single agent could.

**The Collaboration**: Each expert builds on the previous expert's findings through persistent shared sessions - no manual coordination required.

```
Agent 1: "Found 4 performance bottlenecks with evidence"
Agent 2: "Building on your analysis, here are concrete solutions"
Agent 3: "Designing tests for both your findings - comprehensive strategy complete"
```

💡 **Uses shared-context-server MCP tools**: Universal protocol that works with Claude Code, Gemini, VS Code, Cursor, and custom frameworks.

---

## 🚀 Quick Start (2-3 minutes)

### Step 1: Generate Keys & Start Server

**🚀 One-Command Demo Setup (Recommended)**
```bash
# Clone and generate keys directly for demo
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
python scripts/generate_keys.py --demo --uvx
# ↳ Generates secure keys, saves to demo directory, shows next steps
```

**Start the Server:**
```bash
# Follow the exact commands shown by the script above
cd examples/demos/multi-expert-optimization/

# For uvx (recommended):
API_KEY="your-generated-key" JWT_SECRET_KEY="your-generated-secret" \
JWT_ENCRYPTION_KEY="your-generated-encryption-key" \
uvx shared-context-server --transport http

# For Docker:
docker compose up -d
```

### Step 2: Connect Claude Code

```bash
# Use the API key from Step 1 key generation
# For uvx (port 23456):
claude mcp add --transport http scs http://localhost:23456/mcp/ \
  --header "X-API-Key: YOUR_GENERATED_API_KEY"

# For Docker demo (port 23432):
claude mcp add --transport http scs http://localhost:23432/mcp/ \
  --header "X-API-Key: YOUR_GENERATED_API_KEY"

# Alternative: Copy examples/demos/multi-expert-optimization/demo.mcp.json
# to your Claude Code settings and update the API key
```

### Step 3: Verify Setup
```bash
# Health check
# For uvx:
curl http://localhost:23456/health
# For Docker demo:
curl http://localhost:23432/health

# View dashboard (optional)
# For uvx:
open http://localhost:23456/ui/
# For Docker demo:
open http://localhost:23432/ui/
```

**✅ Success**: Health endpoint returns healthy status and Claude Code shows `✓ Connected`

## ✨ What You'll Experience

### The Expert Committee
- **Performance Architect**: Identifies bottlenecks and optimization opportunities
- **Implementation Expert**: Transforms strategies into concrete code solutions
- **Validation Expert**: Designs testing frameworks and success metrics

### Autonomous Coordination
- Experts share findings through persistent sessions
- Each expert builds on the previous expert's analysis
- Visible handoffs show coordination in action
- Memory persistence enables expertise building over time

## 🎯 Demo Script (5-7 minutes)

### The Magic Prompt
Copy this exact prompt to Claude Code:
```
I want to optimize this repository using our expert committee approach. Please start by having our Performance Architect analyze the codebase for bottlenecks and optimization opportunities.
```

### What Happens Next (Autonomous Coordination)
**Phase 1**: **Performance Architect** (2-3 minutes)
- Repository analysis using octocode MCP integration
- Identifies specific bottlenecks with evidence
- Stores findings in shared session
- **Handoff**: "Implementation Expert: Based on my analysis..."

**Phase 2**: **Implementation Expert** (2-3 minutes)
- Reads Performance Architect's findings from session
- Develops concrete code solutions
- Provides implementation details and risk assessment
- **Handoff**: "Validation Expert: I've developed solutions..."

**Phase 3**: **Validation Expert** (1-2 minutes)
- Integrates both previous expert analyses
- Designs comprehensive testing strategy
- **Summary**: "Expert Committee Summary: Complete optimization strategy..."

### Value Demonstration
Ask Claude:
```
Show me how the experts coordinated and built on each other's findings. What would this analysis have looked like with a single agent instead?
```

**Expected Result**: Clear demonstration of knowledge building through expert coordination vs. surface-level single-agent advice.

## 📋 Expected Outcomes

### Performance Analysis
- **Specific Bottlenecks**: Concrete performance issues with evidence from code analysis
- **Impact Assessment**: Quantified performance impact of each identified issue
- **Optimization Strategy**: Prioritized roadmap based on impact and feasibility

### Implementation Strategy
- **Concrete Solutions**: Specific code changes with implementation details
- **Technical Approach**: Framework-specific optimizations and best practices
- **Risk Assessment**: Implementation complexity and potential side effects

### Validation Framework
- **Testing Strategy**: Comprehensive validation approaches for proposed optimizations
- **Success Metrics**: Clear, measurable criteria for optimization success
- **Monitoring Plan**: Ongoing performance tracking and regression detection

## 🔧 Technical Details

### MCP Integration
- **shared-context-server**: Session management and expert coordination
- **octocode**: GitHub repository analysis and code pattern discovery
- **HTTP Transport**: API key authentication with auto-approved tool sets

### Expert Coordination Flow
```
Performance Architect → Implementation Expert → Validation Expert
       ↓                        ↓                      ↓
   Shared Session          Shared Session        Final Summary
   (Analysis Results)      (Solutions)           (Complete Strategy)
```

### Memory Architecture
- **Session Memory**: Immediate coordination and handoff context
- **Persistent Memory**: Expert knowledge building across multiple analyses
- **Visibility Controls**: Public coordination visible to all experts

## 🏗️ Architecture Benefits

### vs. Single Agent Analysis
- **Depth**: Each expert specializes deeply in their domain area
- **Breadth**: Combined expertise covers performance, implementation, and validation
- **Quality**: Peer review through expert handoffs improves analysis quality
- **Consistency**: Persistent memory enables expertise building over time

### Multi-Agent Coordination
- **Autonomous**: Experts coordinate without manual routing
- **Transparent**: Visible handoffs show coordination in action
- **Persistent**: Session history preserves complete analysis context
- **Scalable**: Pattern works for any repository or optimization challenge

## 🚨 Troubleshooting

<details>
<summary>🔧 Common Setup Issues</summary>

### Key Generation Problems
```bash
# If generate_keys.py fails
pip install cryptography

# Verify Python version
python --version  # Requires Python 3.10+
```

### Server Connection Issues
```bash
# Health check
curl http://localhost:23456/health
# Expected: {"status": "healthy", ...}

# For uvx (recommended) - server logs appear in terminal where you ran uvx

# For Docker - check logs (from demo directory)
docker compose logs scs-demo
```

### MCP Connection Problems
```bash
# Test MCP tools discovery
claude mcp list
# Expected: ✓ Connected status for shared-context-server

# Verify API key
echo $API_KEY  # Should show your generated key

# Alternative: Check Claude Code settings for proper API key
```

</details>

<details>
<summary>⚠️ Demo Execution Issues</summary>

### Expert Coordination Not Visible
- **Check**: Ask Claude to "show me the current session messages"
- **Verify**: Experts should reference previous findings in their responses
- **Recovery**: "Please have the experts coordinate through our shared session"

### GitHub Authentication (Optional)
```bash
# For external repository analysis
gh auth login

# Fallback: Use shared-context-server self-analysis
```

### Performance Issues
```bash
# For uvx deployment (recommended)
# Stop with Ctrl+C and restart with the uvx command

# For Docker deployment (from demo directory)
docker compose restart scs-demo
```

</details>

## 📁 Repository Analysis Options

### Personal Projects
Point Claude to your own repositories for immediate value:
- Web applications for performance optimization
- APIs for scalability analysis
- Open source projects for contribution opportunities

### Popular Open Source
Analyze well-known repositories to see expert coordination patterns:
- React, Vue, Angular for frontend optimization insights
- Express, FastAPI, Django for backend performance analysis
- Popular libraries for architectural pattern analysis

### Self-Analysis Fallback
Without GitHub access, analyze the shared-context-server itself:
- Python FastAPI performance optimization
- SQLAlchemy database query analysis
- Docker containerization improvements

## 🎪 Demo Variations

### Quick Demo (2 minutes)
Focus on one aspect: "Have our Performance Architect quickly analyze this codebase for the top 3 optimization opportunities."

### Deep Analysis (10 minutes)
Full expert committee with implementation planning: "I want a comprehensive optimization strategy from our expert committee with specific implementation steps."

### Comparative Analysis (5 minutes)
"Show me how our expert committee approach compares to a single agent analyzing the same repository."

## 🔮 Extending the Demo

### Custom Expert Personas
- Modify `.claude/agents/*.md` files to customize expert behavior
- Add domain-specific expertise (security, accessibility, SEO)
- Create industry-specific optimization focuses

### Alternative Use Cases
- **Security Audits**: Security Expert → Remediation Expert → Compliance Expert
- **Code Reviews**: Code Quality Expert → Best Practices Expert → Documentation Expert
- **Feature Planning**: Requirements Expert → Architecture Expert → Implementation Expert

### Integration Patterns
- Use the coordination patterns for your own multi-agent workflows
- Integrate with CI/CD pipelines for automated optimization analysis
- Build custom expert committees for specialized domains

---

## 🤝 Why This Matters

This demo transforms the value proposition from:
> "Here's infrastructure for multi-agent coordination"

To:
> "Watch three AI experts collaborate better than any individual agent could"

The result: **Immediate, obvious value** that showcases the power of coordinated AI expertise.

**Ready to see expert AI collaboration in action?** Follow the Quick Start above and experience the future of AI-assisted development.
