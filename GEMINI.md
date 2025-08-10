# Shared Context Server - Gemini CLI Context

This document provides an overview of the `shared-context-server` project, intended to serve as instructional context for the Gemini CLI.

## Project Overview

The `shared-context-server` is a centralized memory store designed to enable collaboration between multiple AI agents (e.g., Claude, Gemini) by providing a shared conversational context. It implements a RESTful "Context as a Service" pattern, adhering to the principles of a blackboard architecture. The project is currently in its early stages (5% complete), with comprehensive planning documentation in place, ready for the Minimum Viable Product (MVP) implementation phase.

## Technology Stack

*   **Language:** Python 3.9+
*   **Web Framework:** FastAPI (for high-performance asynchronous web services)
*   **Data Validation:** Pydantic (for data validation and settings management using type hints)
*   **Database:** SQLite (with `aiosqlite` for asynchronous database operations)
*   **HTTP Client (for testing):** `httpx`
*   **Testing Frameworks:** `pytest` and `pytest-asyncio`

## Building and Running

To set up and run the `shared-context-server` project, follow these steps:

### Prerequisites

*   Python 3.9 or higher
*   `pip` (Python package installer)

### Installation

Install the necessary Python dependencies:

```bash
pip install "fastapi[standard]" aiosqlite pydantic httpx pytest pytest-asyncio
```

### Running the Development Server

To start the FastAPI development server:

```bash
fastapi dev main.py
```

### Running Tests

To execute the project's tests:

```bash
pytest tests/ -v
```

## Development Conventions

The project adheres to the following development standards and guidelines:

*   **Component-Centric Design:** Functionality is built around unified interactive components with persistent state.
*   **Data Preservation:** Emphasis on zero-loss data.
*   **Progressive Enhancement:** Core functionality is built first, with advanced features added incrementally.
*   **UTC Timestamps:** All system operations, especially for message timestamps and session coordination, must use UTC.
*   **File Size Limits:** Maximum 500 lines per code file and 1000 lines per test file.
*   **Testing:** Unit tests are required for all new code.
*   **Code Quality:** Linting and type checking (`{{ QUALITY.LINT_COMMAND }}` and `{{ QUALITY.TYPE_CHECK_COMMAND }}`) must pass before commits. (Note: Specific commands for linting and type checking are placeholders and should be inferred from project setup if available, or defined as TODOs).
*   **PRP Specifications:** Implementations must strictly follow the detailed specifications found in the `PRPs/` directory.
