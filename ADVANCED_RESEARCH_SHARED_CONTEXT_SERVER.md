# Advanced Research: Shared Memory Store for Multi-Agent AI Systems

## 1. Executive Summary

This document provides a comprehensive overview of the architectural patterns, advanced features, and security considerations for building a **Shared Memory Store**. Our research confirms that a centralized, external memory service is the standard and most robust architectural pattern for enabling collaboration between heterogeneous, sandboxed AI agents (e.g., Claude sub-agents, Gemini models).

This approach, where the server acts as a "blackboard," decouples agents from the conversational state, allowing for greater flexibility, scalability, and control. It is not "reinventing the wheel" but rather building the necessary foundation for any serious multi-agent workflow. This document is intended to serve as a springboard for the design and development of a production-grade memory store, building upon the MVP outlined in the main patterns document.

---

## 2. Core Implementation Patterns & Data Models

A shared memory store is a modern implementation of the classic **Blackboard System**, a well-established AI pattern.

### a. Persistence Layer Analysis

The choice of a persistence layer has significant implications for performance, scalability, and complexity.

| Technology | Strengths | Weaknesses | Best For |
| :--- | :--- | :--- | :--- |
| **SQLite** | Zero-dependency, simple, fast for single-node access. | Poor concurrency, not easily scalable. | **MVP / Prototyping:** As outlined in the primary plan. |
| **PostgreSQL/MySQL** | High concurrency, robust querying, mature and reliable. | Higher operational overhead. | **Production General-Purpose:** When reliability and concurrent access are key. |
| **Redis** | Extremely fast (in-memory), ideal for caching. | Not a permanent store by default, requires persistence strategy. | **Working Memory:** Caching short-term session data for low-latency access. |
| **Vector DB** | Efficient semantic similarity search (RAG). | Not a general-purpose database. | **Advanced Context:** Augmenting the primary store for RAG and semantic retrieval. |

### b. Advanced Data Schema

To support advanced features, the database schema should capture not just the content, but also the context and causality of each message.

```sql
CREATE TABLE message_history (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    correlation_id TEXT, -- To group related messages/actions across different agents
    agent_id TEXT NOT NULL, -- Unique identifier for the agent (e.g., 'claude-code-v1', 'gemini-pro-1.5')
    agent_role TEXT, -- e.g., 'CodeGenerator', 'RefactorAgent', 'Summarizer'
    message_type TEXT NOT NULL, -- 'human_input', 'agent_response', 'system_status', 'distilled_summary', 'tool_output'
    content TEXT NOT NULL,
    content_embedding BLOB, -- For vector search in RAG
    metadata JSON, -- For storing confidence scores, token counts, source files, etc.
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    parent_message_id INTEGER, -- To create explicit conversational threads
    FOREIGN KEY (parent_message_id) REFERENCES message_history(id)
);
```

---

## 3. Advanced Memory Architectures

A production-grade system should evolve beyond a simple message log to a multi-layered memory architecture.

### a. Tiered Memory (Private vs. Shared)

This is a powerful pattern for reducing noise and enhancing security.

*   **Private Memory (Scratchpad):** Each agent has its own private, temporary memory space for internal reasoning, planning, and drafting responses. This data is not visible to other agents.
*   **Shared Memory:** Once an agent finalizes a piece of information, it **promotes** it from its private scratchpad to the shared memory store, making it available for collaboration.
*   **Benefit:** This prevents the shared space from being cluttered with intermediate "thoughts" and allows for better data isolation and security.

### b. Memory Distillation

This is a more advanced form of summarization. Instead of just shortening the history, a dedicated background process analyzes conversations to extract and structure key information.

*   **Process:** A non-blocking task runs periodically to read recent messages.
*   **Extraction:** It identifies key facts, entities, user preferences, decisions, and outcomes.
*   **Output:** It writes a structured `distilled_memory` entry (e.g., a JSON object) back to the store. This provides a much richer and more queryable context than a simple text summary.

### c. Procedural Memory (Skills Library)

The system can learn from its own successful operations.

*   **Concept:** When a sequence of agent interactions successfully solves a problem (e.g., "refactor a Python function to use async"), the workflow itself (the sequence of agents, prompts, and tools) can be saved as a "skill."
*   **Storage:** This "skill" is stored in a dedicated library within the memory store.
*   **Benefit:** In the future, an orchestrator can query this library for a relevant skill and execute it directly, making the system more efficient, reliable, and capable over time.

---

## 4. Security & Access Control Framework

When multiple agents, especially from different vendors, access a shared resource, a robust security model is non-negotiable.

### a. Authentication (Agent Identity)

Every API call to the memory store must be authenticated to verify the agent's identity.

*   **Method:** Use a robust Machine-to-Machine (M2M) authentication scheme like **OAuth 2.0** with the Client Credentials flow. Each registered agent (e.g., `claude-code-v1`) should have its own unique `client_id` and `secret`.
*   **Avoid:** Do not use simple, non-expiring static API keys in production.

### b. Authorization (Agent Permissions)

Once authenticated, an agent must be authorized. The **Principle of Least Privilege** is critical.

*   **Method:** Implement **Role-Based Access Control (RBAC)**. An agent's role should determine what data it can access.
*   **Example:** A `BillingAgent` role should not be able to read or write to a `CodeGeneration` session. This can be enforced by creating access policies based on `session_id` and the agent's role, which is encoded in its access token.
*   **Implementation:** Your API endpoints must validate the agent's access token to ensure it has the required permissions (e.g., a `scope` of `read:session:123`) before processing any request.

### c. Data Integrity & Auditing

*   **Input Sanitization:** Treat all data written by an agent as untrusted. Sanitize inputs to prevent **prompt injection** or **data poisoning**, where one compromised agent could corrupt the memory for all others.
*   **Immutable Audit Trail:** Maintain a separate, immutable log of every read and write operation. The log must record the `agent_id`, `session_id`, `timestamp`, the specific data accessed, and the outcome of the operation. This is essential for security forensics and debugging.
