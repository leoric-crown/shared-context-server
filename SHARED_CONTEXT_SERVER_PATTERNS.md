# MVP Implementation: Shared Context Server

**Note on Future Development:** This document outlines a strict Minimum Viable Product (MVP) to be developed in accordance with YAGNI/KISS principles. For a comprehensive overview of advanced architectures, security models, and future-facing features, please consult the [**Advanced Research: Shared Memory Store for Multi-Agent AI Systems**](./ADVANCED_RESEARCH_SHARED_CONTEXT_SERVER.md) document.

## 1. Executive Summary (The "Why")

This document outlines a lean plan for building a **Shared Context Server**. The server's purpose is to act as a central "memory store," enabling multiple, independent AI agents (e.g., Gemini, Claude) to collaborate on complex tasks by managing a single, shared source of conversational truth.

---

## 2. Core Architectural Decisions (The "What")

To ensure rapid and robust development, the following architectural patterns are recommended. These choices prioritize simplicity, performance, and alignment with modern Python standards.

| Component | Recommended Pattern | Rationale |
| :--- | :--- | :--- |
| **Architecture** | **RESTful API (Context as a Service)** | Standard, stateless, and easy to integrate with any agent/client. |
| **Framework** | **FastAPI with Pydantic** | High performance, automatic data validation, and self-generating API docs. |
| **Persistence** | **SQLite** | Serverless, file-based, and built into Python. No extra infrastructure needed. |

---

## 3. Actionable Implementation Plan (The "How")

### MVP Implementation: Core API & State Management

**Goal:** A functional server that can create sessions, accept messages, and retrieve raw chat history.

- [ ] **Project Setup:**
    - Initialize a new FastAPI project.
    - Add `fastapi`, `uvicorn`, and `pydantic` to dependencies.

- [ ] **Database Schema (SQLite):**
    - Create a single table `chat_history` with the following schema:
      ```sql
      CREATE TABLE chat_history (
          id INTEGER PRIMARY KEY,
          session_id TEXT NOT NULL,
          sender TEXT NOT NULL,
          content TEXT NOT NULL,
          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      ```

- [ ] **API Endpoints (V1):**
    - Implement the three core endpoints as defined in the API Reference below.
    - `POST /sessions`: Creates a new session ID.
    - `POST /sessions/{session_id}/messages`: Appends a message to the history.
    - `GET /sessions/{session_id}`: Retrieves the full, raw message history.

- [ ] **Success Criteria:**
    - Agents can create a session, send multiple messages, and retrieve the complete history for that session.

---

## 4. API Endpoint Reference

| Endpoint | Method | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `/sessions` | `POST` | Creates a new, empty chat session. | `None` | `{"session_id": "unique-id"}` |
| `/sessions/{id}/messages`| `POST` | Adds a new message to a session. | `{"sender": "agent_name", "content": "..."}` | `{"status": "message added"}` |
| `/sessions/{id}` | `GET` | Retrieves context for a session. | `None` | `{"history": [...]}` |

---

## 5. Agent Integration Pattern (Client-Side)

This reference snippet shows how a client agent should interact with the server.

```python
import httpx

class AgentClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.session_id = None

    def start_session(self):
        """Starts a new session with the server."""
        response = httpx.post(f"{self.base_url}/sessions", headers=self.headers)
        response.raise_for_status()
        self.session_id = response.json()["session_id"]
        print(f"Started new context session: {self.session_id}")

    def add_message(self, sender: str, content: str):
        """Sends a message to the current session."""
        if not self.session_id:
            raise ValueError("Session not started.")

        payload = {"sender": sender, "content": content}
        response = httpx.post(
            f"{self.base_url}/sessions/{self.session_id}/messages",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()

    def get_history(self) -> list:
        """Retrieves the full message history for the current session."""
        if not self.session_id:
            return []

        response = httpx.get(
            f"{self.base_url}/sessions/{self.session_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("history", [])

```
