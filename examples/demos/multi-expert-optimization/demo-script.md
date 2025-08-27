# Multi-Expert Collaboration Demo Script

**Presentation Guide for Consistent Demo Experience**

This script provides exact prompts and timing guidance for delivering a compelling multi-expert collaboration demo.

## 🎯 Demo Objectives

**Primary Goal**: Demonstrate autonomous expert coordination delivering superior analysis compared to single-agent approaches

**Success Metrics**:
- Expert coordination visible and seamless
- Analysis quality obviously superior to single-agent approach
- Setup friction eliminated (sub-30 second start)
- Immediate practical value demonstrated

## ⏱️ Timing Overview

| Phase | Duration | Focus |
|-------|----------|-------|
| Setup Demo | 30 seconds | Zero-friction environment preparation |
| Expert Analysis | 3-4 minutes | Autonomous coordination in action |
| Results Review | 1-2 minutes | Value demonstration and comparison |
| **Total** | **5-6 minutes** | **Complete demo experience** |

## 📋 Pre-Demo Checklist

### Environment Preparation (Done Once)
```bash
☐ Docker installed and running
☐ Node.js available for octocode MCP
☐ Repository cloned: git clone https://github.com/leoric-crown/shared-context-server.git
☐ Demo environment copied: cp examples/demos/multi-expert-optimization/.env.demo .env
☐ Server running: docker compose up -d (verify at http://localhost:23432/health)
☐ Claude Code configured with demo.mcp.json settings
```

### Demo Readiness Check (Before Each Demo)
```bash
☐ Server health check: curl http://localhost:23432/health
☐ MCP connection test: Claude Code should show shared-context-server connected
☐ GitHub access optional: gh auth status (fallback: use self-analysis)
☐ Demo repository selected: Personal project OR popular open source OR shared-context-server itself
```

## 🎪 Demo Script

### Phase 1: Setup Demonstration (30 seconds)

#### Presenter Actions:
```bash
# Show the simplicity
cd shared-context-server
cp examples/demos/multi-expert-optimization/.env.demo .env
docker compose up -d
```

#### Presenter Speaking Points:
> "Let me show you how simple it is to set up an expert AI committee. Three commands: copy demo credentials, start the server, and open Claude Code. The entire setup takes under 30 seconds."

**Key Message**: *Setup friction completely eliminated*

### Phase 2: Expert Coordination Initiation (30 seconds)

#### Exact User Prompt:
Copy this exactly to Claude Code:
```
I want to optimize this repository using our expert committee approach. Please start by having our Performance Architect analyze the codebase for bottlenecks and optimization opportunities.
```

#### Presenter Speaking Points:
> "Now I'll ask Claude to coordinate our expert committee. Notice I'm not routing between agents manually - I'm just asking for an expert committee analysis and the system handles the coordination autonomously."

**Key Message**: *Zero manual coordination required*

### Phase 3: Expert Analysis (3-4 minutes)

#### Expected Flow:
1. **Performance Architect** (2-3 minutes):
   - Repository structure analysis via octocode
   - Bottleneck identification with specific evidence
   - Performance optimization strategy development
   - Visible handoff: "Implementation Expert: Based on my analysis..."

2. **Implementation Expert** (2-3 minutes):
   - Read Performance Architect's findings from session
   - Code pattern analysis and solution development
   - Concrete implementation recommendations
   - Visible handoff: "Validation Expert: I've developed solutions..."

3. **Validation Expert** (1-2 minutes):
   - Integration of both previous expert analyses
   - Testing strategy and success criteria development
   - Comprehensive expert committee summary

#### Presenter Speaking Points:
> "Watch how the experts coordinate. Each builds on the previous expert's work through shared sessions. The Performance Architect identifies bottlenecks, the Implementation Expert proposes concrete solutions, and the Validation Expert designs testing strategies. This is autonomous coordination in action."

**Key Message**: *Visible expert coordination with knowledge building*

### Phase 4: Results Review (1-2 minutes)

#### Follow-up Prompt:
```
Show me how the experts coordinated and built on each other's findings. What would this analysis have looked like with a single agent instead?
```

#### Expected Outcomes:
- **Coordination Summary**: Clear explanation of expert handoffs and shared knowledge
- **Quality Comparison**: Demonstration of depth vs. single-agent analysis
- **Practical Value**: Specific, actionable optimization recommendations

#### Presenter Speaking Points:
> "Look at the depth and breadth we achieved. Each expert specialized in their domain while building on the others' work. A single agent would give you general advice, but our expert committee delivered specific bottlenecks, concrete solutions, and validation strategies. This is the power of coordinated AI expertise."

**Key Message**: *Obviously superior results through expert coordination*

## 🎯 Talking Points Library

### Opening Hook
> "What if instead of one AI agent, you had an entire expert committee collaborating autonomously on your code optimization challenges?"

### Setup Value Prop
> "Traditional multi-agent systems require complex setup and manual coordination. Watch how we've eliminated both problems completely."

### Coordination Emphasis
> "Notice the experts are coordinating through persistent sessions - each expert builds on the previous expert's findings. This isn't sequential prompting, it's genuine AI collaboration."

### Quality Differentiation
> "A single agent gives you general optimization advice. Our expert committee gives you specific bottlenecks, concrete implementation plans, and validation strategies. The difference in quality is obvious."

### Practical Value Close
> "In 5 minutes, you've seen three AI experts deliver analysis that would take you hours to gather manually. This is how AI should work - not replacing human expertise, but amplifying it through coordination."

## 🔧 Troubleshooting Guide

### Common Issues & Quick Fixes

#### Docker Connection Issues
```bash
# Quick fix
docker compose restart shared-context-server
# Verify: curl http://localhost:23432/health
```

#### MCP Connection Problems
- **Check**: API_KEY in .env matches demo.mcp.json configuration
- **Reset**: Restart Claude Code and verify server connection
- **Fallback**: Use existing server instance if available

#### GitHub Authentication Failures
- **Fallback Option**: "Let's analyze the shared-context-server repository itself instead"
- **Quick Fix**: `gh auth login` if time permits
- **Alternative**: Use any publicly accessible repository

#### Expert Coordination Not Visible
- **Verification**: Ask Claude to "show me the current session messages"
- **Recovery**: "Please have the experts coordinate through our shared session"
- **Explanation**: Emphasize the coordination is happening in shared session storage

### Backup Demo Scenarios

#### No GitHub Access Available
> "Let's have our expert committee analyze the shared-context-server codebase itself - a Python FastAPI application with SQLAlchemy database integration."

#### Time Constraints (2-minute version)
> "Let me show you our Performance Architect in action first - we can see the full committee coordination in the extended demo."

#### Technical Difficulties
> "Let me show you the expert persona files and coordination protocol while we resolve the connection issue."

## 📊 Success Indicators

### Audience Engagement Signs
- ✅ **Visible Interest**: Audience watching expert coordination actively
- ✅ **Understanding**: Comments about coordination being "autonomous" or "impressive"
- ✅ **Value Recognition**: Questions about using this for their own projects
- ✅ **Quality Appreciation**: Recognition that analysis depth exceeds single-agent results

### Demo Execution Success
- ✅ **Smooth Setup**: Sub-30 second environment preparation
- ✅ **Expert Coordination**: Visible handoffs between all three experts
- ✅ **Quality Results**: Specific, actionable optimization recommendations
- ✅ **Obvious Value**: Clear superiority over single-agent approaches demonstrated

## 🚀 Demo Variations

### Technical Deep Dive (8-10 minutes)
Add technical explanation of MCP architecture, session management, and memory persistence patterns.

### Business Value Focus (3-5 minutes)
Emphasize ROI: "Three expert analyses in 5 minutes vs. hours of manual research"

### Comparative Demo (7-9 minutes)
Run single-agent analysis first, then expert committee to show quality difference directly.

### Custom Use Case (5-8 minutes)
Adapt expert personas for specific domains (security, performance, accessibility) based on audience needs.

## 💡 Post-Demo Follow-up

### Immediate Next Steps
1. **Repository Access**: Provide demo repository link and setup instructions
2. **Documentation**: Point to complete README.md and integration guides
3. **Customization**: Explain how to modify expert personas for specific domains

### Advanced Integration
1. **Production Usage**: Discuss scaling patterns and production deployment
2. **Custom Experts**: Show how to create domain-specific expert committees
3. **Integration Patterns**: CI/CD integration, automated analysis workflows

---

## 🎯 Key Success Formula

**Setup** (30s) + **Coordination** (3-4m) + **Results** (1-2m) = **Obvious Value**

The demo succeeds when the audience sees:
1. **Zero friction** in setup and execution
2. **Autonomous coordination** between expert agents
3. **Superior quality** compared to single-agent approaches
4. **Immediate practical value** for their own projects

**Result**: Transformation from infrastructure demo to compelling value demonstration.
