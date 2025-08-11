# Shared Context MCP Server - Integration Guide

Comprehensive guide for integrating the Shared Context MCP Server with major agent frameworks and platforms.

## Table of Contents

- [Quick Start Integration](#quick-start-integration)
- [Framework-Specific Integrations](#framework-specific-integrations)
- [Custom Agent Integration](#custom-agent-integration)
- [Multi-Agent Coordination Patterns](#multi-agent-coordination-patterns)
- [Production Deployment](#production-deployment)

---

## Quick Start Integration

### Prerequisites

- Python 3.11+
- Shared Context MCP Server running
- Agent API credentials

### 5-Minute Setup

1. **Start the Server**:
```bash
# Clone and setup
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
uv sync

# Start with hot reload for development
MCP_TRANSPORT=http HTTP_PORT=23456 uv run python -m shared_context_server.scripts.dev
```

2. **Connect Claude Code**:
```bash
# Install mcp-proxy and configure Claude Code
uv tool install mcp-proxy
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'
claude mcp list  # Verify connection: ✓ Connected
```

3. **Test Basic Operations**:
```python
# Authenticate
auth_result = await client.call_tool("authenticate_agent", {
    "agent_id": "test-agent",
    "agent_type": "claude",
    "api_key": "your-api-key"
})

# Create session and add message
session = await client.call_tool("create_session", {
    "purpose": "Quick test session"
})
await client.call_tool("add_message", {
    "session_id": session["session_id"],
    "content": "Hello from integrated agent!"
})
```

---

## Framework-Specific Integrations

### AutoGen Integration

Microsoft AutoGen integration for multi-agent conversations with shared context.

#### Installation & Setup

```python
# requirements.txt
pyautogen>=0.2.0
httpx>=0.25.0
pydantic>=2.0.0

# Install dependencies
pip install -r requirements.txt
```

#### Complete AutoGen Example

```python
import asyncio
import httpx
from typing import Dict, Any, List
import autogen
from autogen import ConversableAgent, GroupChat, GroupChatManager

class SharedContextMCPClient:
    """MCP client for AutoGen agents."""

    def __init__(self, base_url: str = "http://localhost:23456", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = httpx.AsyncClient()
        self.token = None
        self.current_session_id = None

    async def authenticate(self, agent_id: str, agent_type: str = "autogen"):
        """Authenticate agent and get JWT token."""
        response = await self.session.post(
            f"{self.base_url}/mcp/tool/authenticate_agent",
            json={
                "agent_id": agent_id,
                "agent_type": agent_type,
                "api_key": self.api_key,
                "requested_permissions": ["read", "write"]
            }
        )
        result = response.json()
        if result.get("success"):
            self.token = result["token"]
            return result
        else:
            raise Exception(f"Authentication failed: {result.get('error', 'Unknown error')}")

    async def create_session(self, purpose: str, metadata: Dict = None):
        """Create a new collaboration session."""
        if not self.token:
            raise Exception("Not authenticated")

        response = await self.session.post(
            f"{self.base_url}/mcp/tool/create_session",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "purpose": purpose,
                "metadata": metadata or {}
            }
        )
        result = response.json()
        if result.get("success"):
            self.current_session_id = result["session_id"]
            return result
        else:
            raise Exception(f"Session creation failed: {result.get('error', 'Unknown error')}")

    async def add_message(self, content: str, visibility: str = "public", metadata: Dict = None):
        """Add message to current session."""
        if not self.current_session_id:
            raise Exception("No active session")

        response = await self.session.post(
            f"{self.base_url}/mcp/tool/add_message",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.current_session_id,
                "content": content,
                "visibility": visibility,
                "metadata": metadata or {}
            }
        )
        return response.json()

    async def get_messages(self, limit: int = 50):
        """Get messages from current session."""
        if not self.current_session_id:
            raise Exception("No active session")

        response = await self.session.post(
            f"{self.base_url}/mcp/tool/get_messages",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.current_session_id,
                "limit": limit
            }
        )
        return response.json()

    async def search_context(self, query: str, fuzzy_threshold: float = 60.0):
        """Search session context."""
        if not self.current_session_id:
            raise Exception("No active session")

        response = await self.session.post(
            f"{self.base_url}/mcp/tool/search_context",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.current_session_id,
                "query": query,
                "fuzzy_threshold": fuzzy_threshold
            }
        )
        return response.json()

class SharedContextAgent(ConversableAgent):
    """AutoGen agent with shared context integration."""

    def __init__(self, name: str, shared_context_client: SharedContextMCPClient, **kwargs):
        super().__init__(name, **kwargs)
        self.shared_context = shared_context_client
        self.agent_id = name.lower().replace(" ", "-")

    async def setup_shared_context(self, session_purpose: str):
        """Setup shared context for this agent."""
        await self.shared_context.authenticate(self.agent_id)
        session = await self.shared_context.create_session(
            purpose=session_purpose,
            metadata={"autogen_agent": self.name, "framework": "autogen"}
        )
        print(f"Agent {self.name} connected to session: {session['session_id']}")
        return session

    async def send_with_context(self, message: str, recipient=None, request_reply: bool = None):
        """Send message and log to shared context."""
        # Log to shared context
        await self.shared_context.add_message(
            content=message,
            metadata={
                "sender": self.name,
                "recipient": recipient.name if recipient else "group",
                "message_type": "autogen_message"
            }
        )

        # Send normal AutoGen message
        return await super().a_send(message, recipient, request_reply)

# Example Usage: Multi-Agent Research Team
async def main():
    # Initialize shared context
    api_key = "your-api-key"  # Replace with actual API key
    shared_context = SharedContextMCPClient(api_key=api_key)

    # Create specialized agents
    researcher = SharedContextAgent(
        name="Researcher",
        shared_context_client=shared_context,
        system_message="You are a research specialist. Gather and analyze information systematically.",
        llm_config={"model": "gpt-4", "api_key": "your-openai-key"}
    )

    analyst = SharedContextAgent(
        name="Analyst",
        shared_context_client=shared_context,
        system_message="You are a data analyst. Process and interpret research findings.",
        llm_config={"model": "gpt-4", "api_key": "your-openai-key"}
    )

    writer = SharedContextAgent(
        name="Writer",
        shared_context_client=shared_context,
        system_message="You are a technical writer. Create clear, comprehensive reports.",
        llm_config={"model": "gpt-4", "api_key": "your-openai-key"}
    )

    # Setup shared context for collaboration
    await researcher.setup_shared_context("Multi-agent research collaboration")

    # Share the same session across agents
    analyst.shared_context.token = researcher.shared_context.token
    analyst.shared_context.current_session_id = researcher.shared_context.current_session_id
    writer.shared_context.token = researcher.shared_context.token
    writer.shared_context.current_session_id = researcher.shared_context.current_session_id

    # Create AutoGen group chat
    groupchat = GroupChat(
        agents=[researcher, analyst, writer],
        messages=[],
        max_round=6
    )

    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config={"model": "gpt-4", "api_key": "your-openai-key"}
    )

    # Start collaboration
    await researcher.a_initiate_chat(
        manager,
        message="Research the latest trends in AI agent frameworks and multi-agent systems. Analyze the findings and prepare a comprehensive report."
    )

    # Retrieve shared context after collaboration
    messages = await shared_context.get_messages()
    print(f"Session captured {messages['count']} messages")

    # Search for specific topics
    search_results = await shared_context.search_context("AI agent frameworks")
    print(f"Found {len(search_results['results'])} relevant messages about AI frameworks")

if __name__ == "__main__":
    asyncio.run(main())
```

### CrewAI Integration

CrewAI integration for role-based agent crews with shared context memory.

#### Installation & Setup

```python
# requirements.txt
crewai>=0.1.0
httpx>=0.25.0
pydantic>=2.0.0

# Install dependencies
pip install -r requirements.txt
```

#### Complete CrewAI Example

```python
from crewai import Agent, Task, Crew
from crewai.tools import tool
import asyncio
import httpx
from typing import Dict, Any

class SharedContextTool:
    """CrewAI tool for shared context operations."""

    def __init__(self, api_key: str, base_url: str = "http://localhost:23456"):
        self.api_key = api_key
        self.base_url = base_url
        self.token = None
        self.session_id = None

    async def authenticate(self, agent_id: str):
        """Authenticate with shared context server."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tool/authenticate_agent",
                json={
                    "agent_id": agent_id,
                    "agent_type": "crewai",
                    "api_key": self.api_key,
                    "requested_permissions": ["read", "write"]
                }
            )
            result = response.json()
            if result.get("success"):
                self.token = result["token"]
                return True
            return False

    async def create_session(self, purpose: str, metadata: Dict = None):
        """Create collaboration session."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tool/create_session",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"purpose": purpose, "metadata": metadata or {}}
            )
            result = response.json()
            if result.get("success"):
                self.session_id = result["session_id"]
                return result
            return None

    @tool("Add message to shared context")
    def add_message(self, content: str, visibility: str = "public") -> str:
        """Add a message to the shared context session."""
        async def _add():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/mcp/tool/add_message",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "session_id": self.session_id,
                        "content": content,
                        "visibility": visibility,
                        "metadata": {"framework": "crewai"}
                    }
                )
                return response.json()

        # Run async operation
        result = asyncio.run(_add())
        if result.get("success"):
            return f"Message added to shared context (ID: {result['message_id']})"
        return f"Failed to add message: {result.get('error', 'Unknown error')}"

    @tool("Search shared context")
    def search_context(self, query: str, threshold: float = 60.0) -> str:
        """Search the shared context for relevant information."""
        async def _search():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/mcp/tool/search_context",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "session_id": self.session_id,
                        "query": query,
                        "fuzzy_threshold": threshold
                    }
                )
                return response.json()

        result = asyncio.run(_search())
        if result.get("success"):
            matches = result.get("results", [])
            if matches:
                summaries = []
                for match in matches[:3]:  # Top 3 results
                    msg = match["message"]
                    summaries.append(f"- {msg['sender']}: {msg['content'][:100]}... (Score: {match['score']})")
                return f"Found {len(matches)} matches:\n" + "\n".join(summaries)
            return "No relevant information found in shared context."
        return f"Search failed: {result.get('error', 'Unknown error')}"

# Example: Software Development Crew
async def create_development_crew():
    # Initialize shared context
    shared_context = SharedContextTool(api_key="your-api-key")
    await shared_context.authenticate("crewai-coordinator")
    await shared_context.create_session(
        "Software development project planning",
        metadata={"project": "new-feature", "team": "development"}
    )

    # Create agents with shared context tools
    product_manager = Agent(
        role='Product Manager',
        goal='Define product requirements and coordinate development priorities',
        backstory="""You are an experienced product manager with expertise in
        software development lifecycle and stakeholder management. You excel at
        translating business needs into technical requirements.""",
        verbose=True,
        allow_delegation=True,
        tools=[shared_context.add_message, shared_context.search_context]
    )

    tech_lead = Agent(
        role='Technical Lead',
        goal='Design technical architecture and guide implementation approach',
        backstory="""You are a senior technical lead with deep knowledge of
        software architecture, design patterns, and best practices. You ensure
        technical quality and scalability.""",
        verbose=True,
        allow_delegation=True,
        tools=[shared_context.add_message, shared_context.search_context]
    )

    developer = Agent(
        role='Senior Developer',
        goal='Implement features following technical specifications and best practices',
        backstory="""You are an experienced developer skilled in multiple
        programming languages and frameworks. You focus on clean, maintainable code.""",
        verbose=True,
        tools=[shared_context.add_message, shared_context.search_context]
    )

    # Define tasks
    requirements_task = Task(
        description="""Analyze the request for a new user authentication feature.
        Define detailed requirements including:
        1. User stories and acceptance criteria
        2. Security requirements
        3. Performance expectations
        4. Integration points with existing systems

        Document all findings in shared context for team visibility.""",
        agent=product_manager,
        expected_output="Detailed requirements document with user stories and technical specifications"
    )

    architecture_task = Task(
        description="""Based on the requirements, design the technical architecture:
        1. System design and component interactions
        2. Database schema changes
        3. API endpoints and authentication flow
        4. Security considerations and implementation approach

        Search shared context for requirements and document the architecture design.""",
        agent=tech_lead,
        expected_output="Technical architecture document with diagrams and implementation plan"
    )

    implementation_task = Task(
        description="""Implement the authentication feature according to specifications:
        1. Review architecture design from shared context
        2. Implement core authentication components
        3. Create API endpoints with proper validation
        4. Write unit tests and integration tests
        5. Document implementation details

        Use shared context to coordinate with team and document progress.""",
        agent=developer,
        expected_output="Working authentication system with tests and documentation"
    )

    # Create and run crew
    crew = Crew(
        agents=[product_manager, tech_lead, developer],
        tasks=[requirements_task, architecture_task, implementation_task],
        verbose=2,
        process="sequential"  # Tasks run in order with context sharing
    )

    # Execute the crew
    result = crew.kickoff()

    # Retrieve final shared context
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{shared_context.base_url}/mcp/tool/get_messages",
            headers={"Authorization": f"Bearer {shared_context.token}"},
            json={"session_id": shared_context.session_id, "limit": 100}
        )
        messages = response.json()

    print(f"\nCrewAI collaboration completed!")
    print(f"Shared context captured {messages['count']} messages")
    print(f"Final result: {result}")

    return result

# Run the crew
if __name__ == "__main__":
    asyncio.run(create_development_crew())
```

### LangChain Integration

LangChain integration with shared context for multi-agent workflows and memory persistence.

#### Installation & Setup

```python
# requirements.txt
langchain>=0.1.0
langchain-community>=0.0.1
httpx>=0.25.0
pydantic>=2.0.0

# Install dependencies
pip install -r requirements.txt
```

#### Complete LangChain Example

```python
from langchain.agents import Agent, AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain.llms import OpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage
import asyncio
import httpx
from typing import Dict, List, Any

class SharedContextMemory:
    """LangChain-compatible memory with shared context backend."""

    def __init__(self, api_key: str, agent_id: str, base_url: str = "http://localhost:23456"):
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url
        self.token = None
        self.session_id = None
        self.memory_key = f"{agent_id}_conversation_history"

    async def authenticate(self):
        """Authenticate with shared context server."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tool/authenticate_agent",
                json={
                    "agent_id": self.agent_id,
                    "agent_type": "langchain",
                    "api_key": self.api_key,
                    "requested_permissions": ["read", "write"]
                }
            )
            result = response.json()
            if result.get("success"):
                self.token = result["token"]
                return True
            return False

    async def set_session(self, session_id: str):
        """Set the active session for shared context."""
        self.session_id = session_id

    async def save_conversation(self, messages: List[BaseMessage]):
        """Save conversation to shared context memory."""
        if not self.token:
            await self.authenticate()

        conversation_data = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                conversation_data.append({"role": "human", "content": msg.content})
            elif isinstance(msg, AIMessage):
                conversation_data.append({"role": "assistant", "content": msg.content})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tool/set_memory",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "key": self.memory_key,
                    "value": conversation_data,
                    "session_id": self.session_id,
                    "metadata": {"agent_id": self.agent_id, "type": "conversation"}
                }
            )
            return response.json()

    async def load_conversation(self) -> List[Dict]:
        """Load conversation from shared context memory."""
        if not self.token:
            await self.authenticate()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tool/get_memory",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "key": self.memory_key,
                    "session_id": self.session_id
                }
            )
            result = response.json()
            if result.get("success"):
                return result.get("value", [])
            return []

class SharedContextTool:
    """LangChain tool for shared context operations."""

    def __init__(self, api_key: str, agent_id: str, base_url: str = "http://localhost:23456"):
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url
        self.token = None
        self.session_id = None

    async def authenticate(self):
        """Authenticate with shared context server."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tool/authenticate_agent",
                json={
                    "agent_id": self.agent_id,
                    "agent_type": "langchain",
                    "api_key": self.api_key,
                    "requested_permissions": ["read", "write"]
                }
            )
            result = response.json()
            if result.get("success"):
                self.token = result["token"]
                return True
            return False

    async def set_session(self, session_id: str):
        """Set active session."""
        self.session_id = session_id

    def create_tools(self) -> List[Tool]:
        """Create LangChain tools for shared context operations."""

        def add_to_shared_context(content: str) -> str:
            """Add information to shared context for other agents."""
            async def _add():
                if not self.token:
                    await self.authenticate()

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/mcp/tool/add_message",
                        headers={"Authorization": f"Bearer {self.token}"},
                        json={
                            "session_id": self.session_id,
                            "content": content,
                            "visibility": "public",
                            "metadata": {"source": "langchain", "agent": self.agent_id}
                        }
                    )
                    return response.json()

            result = asyncio.run(_add())
            if result.get("success"):
                return f"Successfully added to shared context: {content[:100]}..."
            return f"Failed to add to shared context: {result.get('error', 'Unknown error')}"

        def search_shared_context(query: str) -> str:
            """Search shared context for relevant information."""
            async def _search():
                if not self.token:
                    await self.authenticate()

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/mcp/tool/search_context",
                        headers={"Authorization": f"Bearer {self.token}"},
                        json={
                            "session_id": self.session_id,
                            "query": query,
                            "fuzzy_threshold": 60.0
                        }
                    )
                    return response.json()

            result = asyncio.run(_search())
            if result.get("success") and result.get("results"):
                summaries = []
                for match in result["results"][:5]:
                    msg = match["message"]
                    summaries.append(f"[{msg['sender']}]: {msg['content'][:150]}...")
                return f"Found {len(result['results'])} matches:\n" + "\n".join(summaries)
            return "No relevant information found in shared context."

        def get_agent_memory(key: str) -> str:
            """Retrieve value from agent's private memory."""
            async def _get():
                if not self.token:
                    await self.authenticate()

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/mcp/tool/get_memory",
                        headers={"Authorization": f"Bearer {self.token}"},
                        json={"key": key, "session_id": self.session_id}
                    )
                    return response.json()

            result = asyncio.run(_get())
            if result.get("success"):
                return f"Retrieved from memory: {result['value']}"
            return f"Memory key '{key}' not found or error: {result.get('error', 'Unknown error')}"

        def set_agent_memory(key_value: str) -> str:
            """Store value in agent's private memory. Format: 'key:value'"""
            try:
                key, value = key_value.split(":", 1)
                key = key.strip()
                value = value.strip()
            except ValueError:
                return "Invalid format. Use 'key:value' format."

            async def _set():
                if not self.token:
                    await self.authenticate()

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/mcp/tool/set_memory",
                        headers={"Authorization": f"Bearer {self.token}"},
                        json={
                            "key": key,
                            "value": value,
                            "session_id": self.session_id,
                            "metadata": {"source": "langchain", "agent": self.agent_id}
                        }
                    )
                    return response.json()

            result = asyncio.run(_set())
            if result.get("success"):
                return f"Stored in memory: {key} = {value}"
            return f"Failed to store in memory: {result.get('error', 'Unknown error')}"

        return [
            Tool(
                name="add_to_shared_context",
                description="Add information to shared context that other agents can access. Input should be the content to share.",
                func=add_to_shared_context
            ),
            Tool(
                name="search_shared_context",
                description="Search shared context for relevant information from other agents. Input should be the search query.",
                func=search_shared_context
            ),
            Tool(
                name="get_agent_memory",
                description="Retrieve a value from the agent's private memory. Input should be the memory key.",
                func=get_agent_memory
            ),
            Tool(
                name="set_agent_memory",
                description="Store a value in the agent's private memory. Input should be 'key:value' format.",
                func=set_agent_memory
            )
        ]

# Example: Research and Analysis Workflow
async def langchain_research_workflow():
    """Example workflow using LangChain with shared context."""

    # Initialize shared context
    api_key = "your-api-key"

    # Create shared context session
    async with httpx.AsyncClient() as client:
        # Authenticate coordinator
        auth_response = await client.post(
            "http://localhost:23456/mcp/tool/authenticate_agent",
            json={
                "agent_id": "langchain-coordinator",
                "agent_type": "langchain",
                "api_key": api_key,
                "requested_permissions": ["read", "write"]
            }
        )
        token = auth_response.json()["token"]

        # Create session
        session_response = await client.post(
            "http://localhost:23456/mcp/tool/create_session",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "purpose": "LangChain research workflow with shared context",
                "metadata": {"framework": "langchain", "workflow": "research"}
            }
        )
        session_id = session_response.json()["session_id"]
        print(f"Created session: {session_id}")

    # Create specialized agents
    agents = []

    # Research Agent
    research_tool = SharedContextTool(api_key, "researcher")
    await research_tool.authenticate()
    await research_tool.set_session(session_id)

    research_memory = SharedContextMemory(api_key, "researcher")
    await research_memory.authenticate()
    await research_memory.set_session(session_id)

    researcher = initialize_agent(
        tools=research_tool.create_tools(),
        llm=OpenAI(temperature=0, openai_api_key="your-openai-key"),
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        memory=ConversationBufferMemory(memory_key="chat_history")
    )

    # Analysis Agent
    analysis_tool = SharedContextTool(api_key, "analyst")
    await analysis_tool.authenticate()
    await analysis_tool.set_session(session_id)

    analyst = initialize_agent(
        tools=analysis_tool.create_tools(),
        llm=OpenAI(temperature=0, openai_api_key="your-openai-key"),
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        memory=ConversationBufferMemory(memory_key="chat_history")
    )

    # Execute workflow
    print("Starting research phase...")
    research_result = researcher.run(
        "Research the current trends in multi-agent AI systems. Focus on coordination patterns, "
        "shared memory systems, and real-world applications. Add your findings to shared context."
    )

    print("\nStarting analysis phase...")
    analysis_result = analyst.run(
        "Search the shared context for research findings about multi-agent AI systems. "
        "Analyze the trends and provide insights about future directions and opportunities."
    )

    print(f"\nResearch completed: {research_result}")
    print(f"Analysis completed: {analysis_result}")

    # Retrieve full session history
    async with httpx.AsyncClient() as client:
        messages_response = await client.post(
            "http://localhost:23456/mcp/tool/get_messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"session_id": session_id, "limit": 100}
        )
        messages = messages_response.json()
        print(f"\nShared context captured {messages['count']} messages from LangChain workflow")

if __name__ == "__main__":
    asyncio.run(langchain_research_workflow())
```

---

## Custom Agent Integration

### Python SDK Pattern

Build custom agents with direct API integration:

```python
import httpx
import asyncio
from typing import Dict, Any, Optional

class CustomAgentSDK:
    """SDK for custom agent integration with Shared Context MCP Server."""

    def __init__(self, agent_id: str, api_key: str, base_url: str = "http://localhost:23456"):
        self.agent_id = agent_id
        self.api_key = api_key
        self.base_url = base_url
        self.token = None
        self.session_id = None
        self.client = httpx.AsyncClient()

    async def __aenter__(self):
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def authenticate(self) -> Dict[str, Any]:
        """Authenticate agent and obtain JWT token."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/authenticate_agent",
            json={
                "agent_id": self.agent_id,
                "agent_type": "custom",
                "api_key": self.api_key,
                "requested_permissions": ["read", "write", "admin"]
            }
        )
        result = response.json()
        if result.get("success"):
            self.token = result["token"]
            return result
        else:
            raise Exception(f"Authentication failed: {result}")

    async def create_session(self, purpose: str, metadata: Optional[Dict] = None) -> str:
        """Create new collaboration session."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/create_session",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"purpose": purpose, "metadata": metadata or {}}
        )
        result = response.json()
        if result.get("success"):
            self.session_id = result["session_id"]
            return self.session_id
        else:
            raise Exception(f"Session creation failed: {result}")

    async def join_session(self, session_id: str):
        """Join existing session."""
        self.session_id = session_id

    async def add_message(self, content: str, visibility: str = "public",
                         metadata: Optional[Dict] = None) -> int:
        """Add message to current session."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/add_message",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.session_id,
                "content": content,
                "visibility": visibility,
                "metadata": metadata or {}
            }
        )
        result = response.json()
        if result.get("success"):
            return result["message_id"]
        else:
            raise Exception(f"Add message failed: {result}")

    async def get_messages(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get messages from current session."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/get_messages",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"session_id": self.session_id, "limit": limit, "offset": offset}
        )
        return response.json()

    async def search(self, query: str, threshold: float = 60.0) -> Dict[str, Any]:
        """Search session context."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/search_context",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": self.session_id,
                "query": query,
                "fuzzy_threshold": threshold
            }
        )
        return response.json()

    async def set_memory(self, key: str, value: Any, expires_in: Optional[int] = None) -> bool:
        """Store value in agent memory."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/set_memory",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "key": key,
                "value": value,
                "session_id": self.session_id,
                "expires_in": expires_in
            }
        )
        result = response.json()
        return result.get("success", False)

    async def get_memory(self, key: str) -> Any:
        """Retrieve value from agent memory."""
        response = await self.client.post(
            f"{self.base_url}/mcp/tool/get_memory",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"key": key, "session_id": self.session_id}
        )
        result = response.json()
        if result.get("success"):
            return result["value"]
        return None

# Example usage
async def custom_agent_example():
    """Example custom agent workflow."""

    async with CustomAgentSDK("my-custom-agent", "your-api-key") as agent:
        # Create or join session
        session_id = await agent.create_session(
            "Custom agent collaboration example",
            metadata={"agent_type": "custom", "version": "1.0"}
        )
        print(f"Session created: {session_id}")

        # Add initial message
        msg_id = await agent.add_message(
            "Hello! I'm a custom agent ready to collaborate.",
            metadata={"action": "greeting"}
        )
        print(f"Message added: {msg_id}")

        # Store some state in memory
        await agent.set_memory("agent_state", {
            "status": "active",
            "task": "collaboration_example",
            "session": session_id
        })

        # Simulate collaboration workflow
        tasks = [
            "Analyze current project requirements",
            "Identify potential integration points",
            "Propose implementation approach",
            "Create project timeline"
        ]

        for i, task in enumerate(tasks):
            # Add task to shared context
            await agent.add_message(
                f"Task {i+1}: {task}",
                visibility="public",
                metadata={"task_id": i+1, "status": "planned"}
            )

            # Update memory with current task
            await agent.set_memory("current_task", {
                "id": i+1,
                "description": task,
                "status": "in_progress"
            })

            # Simulate task completion
            await asyncio.sleep(1)

            await agent.add_message(
                f"Completed: {task}",
                visibility="public",
                metadata={"task_id": i+1, "status": "completed"}
            )

        # Search for completed tasks
        search_results = await agent.search("completed")
        print(f"Found {len(search_results.get('results', []))} completed tasks")

        # Get final session messages
        messages = await agent.get_messages()
        print(f"Session contains {messages.get('count', 0)} total messages")

if __name__ == "__main__":
    asyncio.run(custom_agent_example())
```

---

## Multi-Agent Coordination Patterns

### Pattern 1: Sequential Workflow

Agents work in sequence, each building on previous work:

```python
async def sequential_workflow(agents: List[CustomAgentSDK], session_id: str):
    """Execute sequential agent workflow."""

    for i, agent in enumerate(agents):
        await agent.join_session(session_id)

        # Get context from previous agents
        if i > 0:
            messages = await agent.get_messages()
            context = f"Previous work: {len(messages.get('messages', []))} messages"
            await agent.add_message(f"Building on: {context}")

        # Perform agent-specific work
        await agent.add_message(f"Agent {agent.agent_id} starting work phase {i+1}")

        # Mark completion
        await agent.set_memory("workflow_status", {
            "phase": i+1,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })
```

### Pattern 2: Parallel Collaboration

Agents work simultaneously with shared context:

```python
async def parallel_collaboration(agents: List[CustomAgentSDK], session_id: str):
    """Execute parallel agent collaboration."""

    # All agents join session
    for agent in agents:
        await agent.join_session(session_id)

    # Create parallel tasks
    async def agent_work(agent, task_description):
        await agent.add_message(f"Starting: {task_description}")

        # Simulate work with periodic updates
        for step in range(3):
            await agent.add_message(f"Progress update {step+1}/3: {task_description}")
            await asyncio.sleep(1)

            # Check for updates from other agents
            recent_messages = await agent.get_messages(limit=10)
            other_updates = [
                msg for msg in recent_messages.get("messages", [])
                if msg["sender"] != agent.agent_id
            ]

            if other_updates:
                await agent.add_message(f"Noted {len(other_updates)} updates from teammates")

        await agent.add_message(f"Completed: {task_description}")
        return f"{agent.agent_id} completed {task_description}"

    # Execute tasks in parallel
    tasks = [
        agent_work(agents[0], "Data analysis and insights"),
        agent_work(agents[1], "Technical architecture design"),
        agent_work(agents[2], "Implementation planning")
    ]

    results = await asyncio.gather(*tasks)
    return results
```

### Pattern 3: Coordinator-Worker Model

One agent coordinates others:

```python
async def coordinator_worker_pattern(coordinator: CustomAgentSDK,
                                   workers: List[CustomAgentSDK],
                                   session_id: str):
    """Coordinator manages worker agents."""

    # Coordinator creates work plan
    await coordinator.join_session(session_id)
    await coordinator.add_message("Coordinator: Creating work plan")

    work_assignments = [
        {"worker": workers[0].agent_id, "task": "Research phase", "priority": "high"},
        {"worker": workers[1].agent_id, "task": "Analysis phase", "priority": "medium"},
        {"worker": workers[2].agent_id, "task": "Implementation phase", "priority": "high"}
    ]

    # Assign tasks
    for assignment in work_assignments:
        await coordinator.add_message(
            f"TASK ASSIGNMENT: {assignment['worker']} -> {assignment['task']} (Priority: {assignment['priority']})",
            metadata=assignment
        )

    # Workers join and check for assignments
    async def worker_process(worker):
        await worker.join_session(session_id)

        # Search for assignments
        assignments = await worker.search(f"TASK ASSIGNMENT: {worker.agent_id}")

        for assignment in assignments.get("results", []):
            task_info = assignment["message"]["metadata"]
            await worker.add_message(f"Acknowledged: {task_info['task']}")

            # Simulate work
            await asyncio.sleep(2)

            await worker.add_message(f"COMPLETED: {task_info['task']}")

            # Report back to coordinator
            await worker.add_message(f"@coordinator: Task '{task_info['task']}' completed by {worker.agent_id}")

    # Execute worker processes
    worker_tasks = [worker_process(worker) for worker in workers]
    await asyncio.gather(*worker_tasks)

    # Coordinator reviews completion
    completed_tasks = await coordinator.search("COMPLETED:")
    await coordinator.add_message(f"Coordinator: {len(completed_tasks.get('results', []))} tasks completed successfully")
```

---

## Production Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application
COPY . .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV LOG_LEVEL=INFO
ENV AUTH_ENABLED=true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["uv", "run", "python", "-m", "shared_context_server.scripts.cli", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  shared-context-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/chat_history.db
      - API_KEY=${API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - LOG_LEVEL=INFO
      - AUTH_ENABLED=true
      - CORS_ORIGINS=*
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - shared-context-server
    restart: unless-stopped
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shared-context-server
  labels:
    app: shared-context-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shared-context-server
  template:
    metadata:
      labels:
        app: shared-context-server
    spec:
      containers:
      - name: shared-context-server
        image: shared-context-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/shared_context"
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: api-key
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: jwt-secret
        - name: LOG_LEVEL
          value: "INFO"
        - name: AUTH_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: shared-context-server-service
spec:
  selector:
    app: shared-context-server
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### Environment Configuration

```bash
# .env.production
DATABASE_URL=postgresql://user:password@localhost:5432/shared_context
API_KEY=your-secure-production-api-key
JWT_SECRET_KEY=your-jwt-secret-key-at-least-32-characters
LOG_LEVEL=WARNING
AUTH_ENABLED=true
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
ADMIN_API_KEY=your-admin-key
```

### Monitoring & Observability

```python
# monitoring.py
import logging
import time
from prometheus_client import Counter, Histogram, Gauge
from functools import wraps

# Metrics
REQUEST_COUNT = Counter('mcp_requests_total', 'Total MCP requests', ['tool', 'status'])
REQUEST_DURATION = Histogram('mcp_request_duration_seconds', 'MCP request duration', ['tool'])
ACTIVE_SESSIONS = Gauge('mcp_active_sessions', 'Number of active sessions')
ACTIVE_AGENTS = Gauge('mcp_active_agents', 'Number of active agents')

def monitor_mcp_tool(tool_name: str):
    """Decorator to monitor MCP tool performance."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(tool=tool_name, status='success').inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(tool=tool_name, status='error').inc()
                logging.error(f"Tool {tool_name} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(tool=tool_name).observe(duration)
        return wrapper
    return decorator

# Usage in your MCP tools
@monitor_mcp_tool("create_session")
async def create_session(...):
    # Tool implementation
    pass
```

---

## Best Practices & Tips

### Performance Optimization

1. **Connection Pooling**: Use the built-in connection pooling for database operations
2. **Caching**: Leverage multi-level caching for frequently accessed data
3. **Batch Operations**: Group multiple operations when possible
4. **Async Patterns**: Use async/await throughout your agent implementations

### Security Best Practices

1. **JWT Token Management**: Store tokens securely, implement token refresh
2. **Input Validation**: Validate all input data before sending to server
3. **Permission Principle**: Request minimal required permissions
4. **API Key Security**: Use environment variables, never hardcode keys

### Error Handling

1. **Retry Logic**: Implement exponential backoff for transient failures
2. **Circuit Breaker**: Prevent cascading failures in multi-agent systems
3. **Graceful Degradation**: Handle server unavailability gracefully
4. **Logging**: Comprehensive logging for debugging and monitoring

### Scalability Considerations

1. **Session Management**: Clean up unused sessions periodically
2. **Memory Usage**: Set appropriate TTL for agent memory
3. **Load Balancing**: Use multiple server instances for high load
4. **Database Scaling**: Consider PostgreSQL for production workloads

---

For additional resources and troubleshooting, see:
- [API Reference](./api-reference.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Performance Tuning Guide](./performance-guide.md)
