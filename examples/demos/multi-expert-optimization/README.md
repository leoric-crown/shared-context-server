# Multi-Expert Collaboration Demo

**Transform AI from individual agents into coordinated expert committees**

This demo showcases how the shared-context-server enables three AI experts to collaborate autonomously, analyzing your codebase more effectively than any single agent could alone.

## 🚀 Quick Start (20 seconds)

```bash
# 1. Clone and navigate to demo
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server/examples/demos/multi-expert-optimization/

# 2. Start the demo server (everything pre-configured)
docker compose up -d

# 3. Open Claude Code with demo MCP config
# Copy demo.mcp.json to your Claude Code settings
```

**That's it!** Your expert committee is ready to analyze any repository.

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

## 🎯 Demo Script (5 minutes)

### Step 1: Initiate Expert Analysis (30 seconds)
Say to Claude Code:
> "I want to optimize this repository using our expert committee approach. Please start by having our Performance Architect analyze the codebase for bottlenecks and optimization opportunities."

### Step 2: Watch Expert Coordination (3-4 minutes)
Claude will automatically coordinate three experts:

1. **Performance Architect** (2-3 min): Repository analysis using octocode MCP integration
2. **Implementation Expert** (2-3 min): Concrete solutions based on architect findings
3. **Validation Expert** (1-2 min): Testing strategy and comprehensive summary

### Step 3: Review Coordination Results (1-2 minutes)
Ask Claude:
> "Show me how the experts coordinated and what would this analysis have looked like with a single agent instead?"

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

### Docker Issues
```bash
# Check container status
docker compose ps

# View logs if issues
docker compose logs shared-context-server

# Reset if needed
docker compose down && docker compose up -d
```

### MCP Connection Issues
1. **Verify .env file**: Ensure you copied `.env.demo` to `.env` in root directory
2. **Check server status**: Visit http://localhost:23432/health
3. **MCP Configuration**: Ensure `demo.mcp.json` is properly configured in Claude Code

### GitHub Authentication (Optional)
```bash
# If you want to analyze external repositories
gh auth login

# Or set token manually
export GITHUB_TOKEN=your_token_here
```

**Note**: Demo works without GitHub auth using self-analysis of the shared-context-server repository.

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
