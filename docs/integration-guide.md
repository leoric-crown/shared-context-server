# Integration Guide: Collaborative Agent Sessions

Transform your AI agents from independent workers into collaborative teams. This guide shows MCP protocol integration (tested) and conceptual patterns for popular agent frameworks (community contributions welcome).

## Content Navigation

| Symbol | Meaning | Time Investment |
|--------|---------|----------------|
| 🟢 | Beginner friendly | 5-10 minutes |
| 🟡 | Intermediate setup | 15-30 minutes |
| 🔴 | Advanced/Production | 30+ minutes |
| 💡 | Why this works | Context only |
| ⚠️ | Important note | Read carefully |

---

## 🟢 Quick Start (5 minutes)

### One-Command Setup
```bash
# Start the server
docker run -d --name shared-context-server -p 23456:23456 \
  -e API_KEY="test-key" -e JWT_SECRET_KEY="test-secret" \
  -e JWT_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  ghcr.io/leoric-crown/shared-context-server:latest

# Connect with Claude Code
claude mcp add --transport http shared-context-server http://localhost:23456/mcp/ \
  --header "X-API-Key: test-key"
```

### 3-Line Collaboration Test
```python
# Create shared session
session = await client.call_tool("create_session", {"purpose": "test collaboration"})

# Agent 1 shares discovery
await client.call_tool("add_message", {
    "session_id": session["session_id"],
    "content": "Agent 1: Found the root cause in authentication module"
})

# Agent 2 builds on it
await client.call_tool("add_message", {
    "session_id": session["session_id"],
    "content": "Agent 2: Fixed the auth issue and optimized the query performance"
})
```

💡 **Why this works**: Each agent sees the previous findings instead of starting from zero.

---

## 🟢 MCP Protocol Integration (Tested)

### Claude Code Integration
```python
# Add to Claude Code (tested and working)
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'

# Use MCP tools directly
session = await client.call_tool("create_session", {"purpose": "code review"})
await client.call_tool("add_message", {
    "session_id": session["session_id"],
    "content": "Security Agent: Found vulnerabilities in auth module"
})
```

### Direct HTTP API
```python
import httpx
client = httpx.AsyncClient()

# Create collaborative session
session = await client.post("http://localhost:23456/mcp/tool/create_session",
                           json={"purpose": "agent collaboration"})

# Share findings between agents
await client.post("http://localhost:23456/mcp/tool/add_message", json={
    "session_id": session_id,
    "content": "Agent 1: Found root cause in authentication"
})
```

**➡️ Next**: [Conceptual Framework Patterns](#-conceptual-framework-patterns) (untested)

---

## 🟡 Collaborative Workflows

### Code Review Pipeline
**Problem**: Security → Performance → Documentation agents work independently

**Solution**: Sequential collaboration with context handoffs

```python
# Phase 1: Security Agent
security_findings = await security_agent.review_code(file_path)
await session.add_message(f"🔒 Security: Found {len(security_findings)} issues")

# Phase 2: Performance Agent (sees security context)
security_context = await session.search_context("security vulnerabilities")
perf_findings = await performance_agent.optimize_with_security(file_path, security_context)
await session.add_message(f"⚡ Performance: Optimized while fixing security issues")

# Phase 3: Documentation Agent (has full context)
complete_context = await session.get_messages(limit=20)
docs = await docs_agent.document_solution(file_path, complete_context)
```

💡 **Why this pattern works**: Each agent builds on previous discoveries instead of duplicating work.

### Research & Implementation Workflow
```python
# Research Phase
research_findings = await research_agent.investigate(topic)
await session.add_message(f"📊 Research: {research_findings.summary}")

# Architecture Phase (builds on research)
research_context = await session.search_context("requirements constraints")
architecture = await architect_agent.design_solution(research_context)
await session.add_message(f"🏗️ Architecture: {architecture.summary}")

# Implementation Phase (has full context)
implementation = await developer_agent.implement_solution(await session.get_messages())
```

<details>
<summary>🟡 Advanced Workflow Patterns</summary>

### Parallel Specialist Collaboration
```python
# Problem analysis
analyst_results = await analyst_agent.analyze_problem(description)

# Multiple specialists work in parallel with shared context
specialists = [
    TechnicalSpecialist(session, "backend"),
    TechnicalSpecialist(session, "frontend"),
    TechnicalSpecialist(session, "database"),
    TechnicalSpecialist(session, "security")
]

# Each specialist sees others' findings as they work
for specialist in specialists:
    context = await session.get_context_for_agent(specialist.specialty)
    result = await specialist.solve_aspect(description, context)
    await session.add_message(f"✅ {specialist.specialty}: {result}")

# Integration specialist combines all solutions
integrator = IntegrationSpecialist(session)
final_solution = await integrator.combine_solutions(await session.get_messages())
```

### Clean Agent Handoffs
```python
class AgentHandoffManager:
    def __init__(self, session):
        self.session = session

    async def handoff(self, from_agent: str, to_agent: str, summary: str):
        """Clean handoff with context preservation."""
        await self.session.add_message(
            f"🔄 HANDOFF: {from_agent} → {to_agent}\n{summary}",
            metadata={"type": "handoff", "from": from_agent, "to": to_agent}
        )

    async def get_handoff_context(self, for_agent: str):
        """Get relevant context for incoming agent."""
        return await self.session.search_context(f"handoff {for_agent}")
```

</details>

---

## 🟡 Conceptual Framework Patterns

⚠️ **Important**: The following framework integrations are conceptual designs that have not been tested. They represent potential integration patterns that could be developed by the community.

### CrewAI: Team Collaboration

<details>
<summary>🟢 Conceptual CrewAI Integration (untested)</summary>

```python
# CONCEPTUAL - NOT TESTED
from crewai import Agent, Task, Crew
from crewai.tools import tool

# This integration pattern is theoretical
# CrewAI would need to add support for external context servers
crew = Crew(
    agents=[security_agent, perf_agent, docs_agent],
    tasks=[security_task, perf_task, docs_task],
    context_server="http://localhost:23456"  # Conceptual feature
)

result = crew.kickoff()  # Would need CrewAI framework changes
```

💡 **Implementation needed**: CrewAI framework would need to add context server support. Community contributions welcome!

</details>

<details>
<summary>🟡 Production CrewAI with Custom Tools (20 minutes)</summary>

```python
class SharedContextCrewAI:
    def __init__(self, api_key: str):
        self.context_client = SharedContextClient(api_key)
        self.session_id = None

    async def setup_crew_session(self, purpose: str):
        session = await self.context_client.create_session(purpose)
        self.session_id = session["session_id"]
        return self.session_id

    @tool("Share findings with crew")
    def share_findings(self, findings: str) -> str:
        """Share discoveries with other crew members."""
        asyncio.run(self.context_client.add_message(
            session_id=self.session_id,
            content=f"💡 CREW FINDINGS: {findings}",
            visibility="public"
        ))
        return f"Shared with crew: {findings[:100]}..."

    @tool("Get crew insights")
    def get_crew_insights(self, topic: str) -> str:
        """Get relevant insights from crew members."""
        results = asyncio.run(self.context_client.search_context(
            session_id=self.session_id,
            query=topic,
            fuzzy_threshold=70.0
        ))

        if results["success"] and results["results"]:
            insights = [f"- {r['message']['content'][:150]}..."
                       for r in results["results"][:3]]
            return f"Crew insights on '{topic}':\n" + "\n".join(insights)
        return f"No crew insights found for '{topic}'"

# Create development crew with shared context
async def create_development_crew():
    shared_crew = SharedContextCrewAI(api_key="your-key")
    await shared_crew.setup_crew_session("Software feature development")

    # Agents with shared context tools
    product_manager = Agent(
        role='Product Manager',
        goal='Define requirements and coordinate with technical team',
        tools=[shared_crew.share_findings, shared_crew.get_crew_insights],
        allow_delegation=True
    )

    tech_lead = Agent(
        role='Technical Lead',
        goal='Design architecture based on requirements',
        tools=[shared_crew.share_findings, shared_crew.get_crew_insights],
        allow_delegation=True
    )

    # Tasks that build on each other through shared context
    requirements_task = Task(
        description="""
        Define requirements for authentication feature:
        1. Use get_crew_insights to check existing features
        2. Define detailed requirements
        3. Use share_findings to document for technical team
        """,
        agent=product_manager
    )

    architecture_task = Task(
        description="""
        Design technical architecture:
        1. Use get_crew_insights('requirements') to get PM's analysis
        2. Design system architecture
        3. Use share_findings to document for implementation
        """,
        agent=tech_lead
    )

    crew = Crew(
        agents=[product_manager, tech_lead],
        tasks=[requirements_task, architecture_task],
        process="sequential"  # Each task builds on previous
    )

    return crew.kickoff()
```

</details>

### AutoGen: Multi-Agent Conversations

<details>
<summary>🟢 Conceptual AutoGen Integration (untested)</summary>

```python
# CONCEPTUAL - NOT TESTED
import autogen
from autogen import ConversableAgent, GroupChat

# This integration pattern is theoretical
# AutoGen would need to add context server support
session_id = context_server.create_session("research_collaboration")

researcher = ConversableAgent(
    name="Researcher",
    system_message="Research specialist. Always check shared context before starting work.",
    context_session=session_id  # Connect to shared session
)

analyst = ConversableAgent(
    name="Analyst",
    system_message="Data analyst. Build on research findings from shared context.",
    context_session=session_id  # Same shared session
)

# Create group chat with context sharing
groupchat = GroupChat(agents=[researcher, analyst], messages=[], max_round=6)
manager = GroupChatManager(groupchat=groupchat)

# Agents automatically share context through session
researcher.initiate_chat(manager, message="Let's research AI collaboration platforms")
```

</details>

<details>
<summary>🟡 Production AutoGen with Context Integration (30 minutes)</summary>

```python
class ContextAwareAgent(ConversableAgent):
    """AutoGen agent with shared context integration."""

    def __init__(self, name, context_client, session_id, **kwargs):
        super().__init__(name, **kwargs)
        self.context_client = context_client
        self.session_id = session_id
        self.agent_id = name.lower().replace(" ", "-")

    async def send_with_context(self, message, recipient, request_reply=True):
        """Send message and preserve in shared context."""
        # Add to shared context for other agents
        await self.context_client.add_message(
            session_id=self.session_id,
            content=f"{self.name}: {message}",
            metadata={
                "autogen_agent": self.name,
                "recipient": recipient.name if recipient else "group"
            }
        )
        # Send through AutoGen
        return await super().a_send(message, recipient, request_reply)

    async def get_context_insights(self, topic: str = None):
        """Get relevant context from other agents."""
        query = topic or "findings recommendations decisions"
        results = await self.context_client.search_context(
            session_id=self.session_id,
            query=query,
            fuzzy_threshold=60.0
        )

        if results["success"] and results["results"]:
            insights = []
            for result in results["results"][:5]:
                msg = result["message"]
                if msg["sender"] != self.agent_id:  # Don't include own messages
                    insights.append(f"{msg['sender']}: {msg['content'][:200]}...")
            return "\n".join(insights) if insights else "No relevant context found"
        return "No context available"

# Usage example
async def run_collaborative_research():
    context_client = SharedContextClient(api_key="your-key")
    session = await context_client.create_session("Multi-agent research")
    session_id = session["session_id"]

    # Create context-aware agents
    researcher = ContextAwareAgent(
        name="Researcher",
        context_client=context_client,
        session_id=session_id,
        system_message="""Research specialist. Before providing analysis:
        1. Use get_context_insights() to see what others discovered
        2. Build on existing findings rather than duplicating work
        3. Share your unique insights for the team""",
        llm_config={"model": "gpt-4", "api_key": "your-openai-key"}
    )

    analyst = ContextAwareAgent(
        name="Analyst",
        context_client=context_client,
        session_id=session_id,
        system_message="""Data analyst. Before analysis:
        1. Use get_context_insights('research findings') to get research data
        2. Analyze trends and patterns
        3. Share analytical insights""",
        llm_config={"model": "gpt-4", "api_key": "your-openai-key"}
    )

    # Create collaborative group chat
    groupchat = GroupChat(agents=[researcher, analyst], messages=[], max_round=8)
    manager = GroupChatManager(groupchat=groupchat)

    # Start collaboration with context sharing
    await researcher.a_initiate_chat(
        manager,
        message="Research AI agent collaboration platforms. Check context first."
    )

    # Get final shared context summary
    final_context = await context_client.get_messages(session_id=session_id, limit=50)
    return final_context
```

</details>

### LangChain: Workflow Continuity

<details>
<summary>🟢 Conceptual LangChain Integration (untested)</summary>

```python
# CONCEPTUAL - NOT TESTED
from langchain.agents import initialize_agent
from langchain.tools import Tool

# This integration pattern is theoretical
# Create shared context tools
def add_to_context(content: str) -> str:
    """Add finding to shared workflow context."""
    context_client.add_message(session_id, content)
    return f"Added to shared context: {content[:100]}..."

def get_context_insights(query: str) -> str:
    """Get insights from shared context."""
    results = context_client.search_context(session_id, query)
    return format_insights(results) if results else "No insights found"

# Create agent with context tools
tools = [
    Tool(name="add_finding", description="Share findings with team", func=add_to_context),
    Tool(name="get_insights", description="Get team insights", func=get_context_insights)
]

agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
```

</details>

<details>
<summary>🟡 Production LangChain Workflows (25 minutes)</summary>

```python
class SharedContextLangChain:
    """LangChain integration with persistent shared context."""

    def __init__(self, api_key: str):
        self.context_client = SharedContextClient(api_key)
        self.session_id = None

    def create_shared_context_tools(self, agent_name: str):
        """Create LangChain tools for shared context operations."""

        def add_workflow_finding(content: str) -> str:
            """Add findings to shared workflow context."""
            asyncio.run(self.context_client.add_message(
                session_id=self.session_id,
                content=f"[{agent_name}] {content}",
                metadata={"agent": agent_name, "type": "workflow_finding"}
            ))
            return f"Added to workflow: {content[:100]}..."

        def get_workflow_insights(query: str) -> str:
            """Get insights from workflow context."""
            results = asyncio.run(self.context_client.search_context(
                session_id=self.session_id,
                query=query,
                fuzzy_threshold=65.0
            ))

            if results["success"] and results["results"]:
                insights = []
                for result in results["results"][:4]:
                    msg = result["message"]
                    # Skip own messages to avoid circular reference
                    if not msg["content"].startswith(f"[{agent_name}]"):
                        insights.append(f"- {msg['content'][:180]}...")
                return f"Workflow insights:\n" + "\n".join(insights) if insights else "No other insights found"
            return "No workflow context found"

        def handoff_to_agent(input_str: str) -> str:
            """Clean handoff to another agent. Format: 'target_agent:summary'"""
            if ":" not in input_str:
                return "Invalid format, use 'agent:summary'"

            target_agent, summary = input_str.split(":", 1)
            handoff_msg = f"🔄 HANDOFF: {agent_name} → {target_agent}\n{summary}"
            asyncio.run(self.context_client.add_message(
                session_id=self.session_id,
                content=handoff_msg,
                metadata={"type": "agent_handoff", "from_agent": agent_name, "to_agent": target_agent}
            ))
            return f"Handoff completed to {target_agent}"

        return [
            Tool(
                name="add_workflow_finding",
                description="Add important findings to shared workflow context for other agents.",
                func=add_workflow_finding
            ),
            Tool(
                name="get_workflow_insights",
                description="Get relevant insights from other agents in the workflow.",
                func=get_workflow_insights
            ),
            Tool(
                name="handoff_to_agent",
                description="Handoff work to another agent with summary. Use 'agent:summary' format.",
                func=handoff_to_agent
            )
        ]

    async def create_workflow_agent(self, agent_name: str, role_description: str):
        """Create a workflow-aware LangChain agent."""
        tools = self.create_shared_context_tools(agent_name)

        agent = initialize_agent(
            tools=tools,
            llm=OpenAI(temperature=0.1, openai_api_key="your-openai-key"),
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            agent_kwargs={
                "prefix": f"""You are {agent_name}, {role_description}

                WORKFLOW RULES:
                1. Use get_workflow_insights to see what other agents discovered
                2. Build on existing findings rather than duplicating work
                3. Use add_workflow_finding to share important discoveries
                4. Use handoff_to_agent when completing your phase

                Available tools:"""
            }
        )
        return agent

# Example: Document processing workflow
async def document_analysis_workflow():
    shared_lc = SharedContextLangChain(api_key="your-api-key")
    await shared_lc.setup_shared_workflow("Document analysis workflow")

    # Create specialized workflow agents
    extractor = await shared_lc.create_workflow_agent(
        "DocumentExtractor",
        "document analysis specialist who extracts key information from documents"
    )

    analyzer = await shared_lc.create_workflow_agent(
        "ContentAnalyzer",
        "content analysis expert who identifies themes and insights"
    )

    summarizer = await shared_lc.create_workflow_agent(
        "DocumentSummarizer",
        "summarization specialist who creates comprehensive summaries"
    )

    # Workflow execution with agent handoffs
    document_path = "example_document.pdf"

    # Phase 1: Document extraction
    extraction_result = extractor.run(f"""
    Extract key information from: {document_path}
    - Main topics and themes
    - Key entities and facts
    Add findings to workflow and handoff to ContentAnalyzer when complete.
    """)

    # Phase 2: Content analysis (builds on extraction)
    analysis_result = analyzer.run(f"""
    Analyze content from {document_path}
    First get workflow insights about 'extraction findings' to see what DocumentExtractor found.
    Then analyze themes, sentiment, and insights.
    Add analysis to workflow and handoff to DocumentSummarizer.
    """)

    # Phase 3: Summarization (builds on extraction + analysis)
    summary_result = summarizer.run(f"""
    Create comprehensive summary of {document_path}
    Get workflow insights about 'extraction analysis' to see all previous work.
    Create executive summary and recommendations.
    """)

    # Get complete workflow context
    workflow_context = await shared_lc.context_client.get_messages(
        session_id=shared_lc.session_id, limit=100
    )

    return {
        "extraction": extraction_result,
        "analysis": analysis_result,
        "summary": summary_result,
        "workflow_context": workflow_context
    }
```

</details>

---

## 🔴 Custom Agent Integration

<details>
<summary>🟡 Simple Custom Agent SDK (15 minutes)</summary>

```python
import asyncio
import httpx

class AgentCollaborationSDK:
    """Lightweight SDK for custom agent collaboration."""

    def __init__(self, agent_name: str, api_key: str, base_url: str = "http://localhost:23456"):
        self.agent_name = agent_name
        self.api_key = api_key
        self.base_url = base_url
        self.session_id = None
        self.client = httpx.AsyncClient()
        self.token = None

    async def authenticate(self):
        """Authenticate agent with shared context server."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/authenticate_agent",
            json={
                "agent_id": self.agent_name.lower().replace(" ", "-"),
                "agent_type": "custom",
                "api_key": self.api_key,
                "requested_permissions": ["read", "write"]
            }
        )
        result = response.json()
        if result.get("success"):
            self.token = result["token"]
        else:
            raise Exception(f"Authentication failed: {result}")

    async def start_collaboration(self, purpose: str):
        """Start new collaboration session."""
        if not self.token:
            await self.authenticate()

        response = await self.client.post(
            f"{self.base_url}/mcp/tool/create_session",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"purpose": purpose}
        )
        result = response.json()
        if result.get("success"):
            self.session_id = result["session_id"]
            return self.session_id
        else:
            raise Exception(f"Session creation failed: {result}")

    async def share_finding(self, finding: str, metadata: dict = None):
        """Share finding with collaborating agents."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/add_message",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.session_id,
                "content": f"[{self.agent_name}] {finding}",
                "visibility": "public",
                "metadata": metadata or {"agent": self.agent_name}
            }
        )
        return response.json()

    async def get_collaboration_context(self, focus_area: str = None):
        """Get relevant context from other collaborating agents."""
        query = focus_area or "findings recommendations insights"
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/search_context",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.session_id,
                "query": query,
                "fuzzy_threshold": 65.0
            }
        )
        result = response.json()
        if result.get("success"):
            # Filter out own messages
            relevant_findings = []
            for item in result.get("results", []):
                content = item["message"]["content"]
                if not content.startswith(f"[{self.agent_name}]"):
                    relevant_findings.append(content)
            return relevant_findings
        return []

# Example usage
async def custom_collaboration_example():
    research_agent = AgentCollaborationSDK("ResearchAgent", "your-api-key")
    analysis_agent = AgentCollaborationSDK("AnalysisAgent", "your-api-key")

    # Start collaboration
    session_id = await research_agent.start_collaboration("Market analysis project")
    analysis_agent.session_id = session_id
    await analysis_agent.authenticate()

    # Phase 1: Research
    await research_agent.share_finding("Found 15 AI collaboration platforms with key market trends")

    # Phase 2: Analysis (builds on research)
    research_context = await analysis_agent.get_collaboration_context("market trends research")
    await analysis_agent.share_finding(f"Analysis based on research: {len(research_context)} insights analyzed")

    return session_id
```

</details>

<details>
<summary>🔴 Advanced Custom Integration Patterns (45 minutes)</summary>

[Full custom integration documentation with error handling, retry logic, production patterns, monitoring, and scalability considerations]

</details>

---

## 🔴 Production Deployment

<details>
<summary>🟡 Docker Production Setup (20 minutes)</summary>

```yaml
# docker-compose.yml for collaborative agents
version: '3.8'

services:
  shared-context-server:
    image: ghcr.io/leoric-crown/shared-context-server:latest
    ports:
      - "23456:23456"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/shared_context
      - API_KEY=${API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - LOG_LEVEL=INFO
      - AUTH_ENABLED=true
      - MAX_CONCURRENT_SESSIONS=100
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=shared_context
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

💡 **Why PostgreSQL for production?** Supports 20+ concurrent agents vs SQLite's ~5 agent limit.

</details>

<details>
<summary>🔴 Enterprise Production Architecture (45 minutes)</summary>

[Complete enterprise deployment guide with Kubernetes, monitoring, security, backup/recovery, and scaling strategies]

</details>

---

## Best Practices Summary

### 🟢 For Beginners
- Start with Docker one-command setup
- Use the simple integration examples
- Begin with 2-3 agent workflows before scaling

### 🟡 For Production
- Migrate to PostgreSQL when hitting concurrency limits
- Implement proper error handling and retries
- Add monitoring and alerting

### 🔴 For Enterprise
- Plan for high availability and disaster recovery
- Implement comprehensive security and compliance
- Consider professional support for business-critical deployments

---

**Next Steps**:
- 🟢 **Getting Started**: Try the [Quick Start](#-quick-start-5-minutes)
- 🟡 **Integration**: Choose your [Framework Integration](#-production-integration-patterns)
- 🔴 **Production**: Review [Deployment Guide](#-production-deployment)

For additional help: [API Reference](./api-reference.md) | [Troubleshooting](./troubleshooting.md)
