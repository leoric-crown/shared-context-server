-- Shared Context MCP Server Database Schema
-- Fixed version addressing critical issues identified in consultant review
--
-- Key fixes:
-- 1. Removed REGEXP CHECK constraints (moved to Pydantic validation)
-- 2. Added UPDATE triggers for updated_at fields
-- 3. Added JSON validity checks for metadata fields
-- 4. Added proper indexes for multi-agent performance
-- 5. Optimized PRAGMA settings included in connection setup

-- Enable foreign keys (must be set per connection)
-- This will be handled in database.py connection factory
-- PRAGMA foreign_keys = ON;

-- Performance PRAGMAs (applied per connection in database.py)
-- PRAGMA journal_mode = WAL;
-- PRAGMA synchronous = NORMAL;
-- PRAGMA cache_size = -8000;        -- 8MB cache
-- PRAGMA temp_store = MEMORY;
-- PRAGMA mmap_size = 268435456;     -- 256MB (reduced from 30GB)
-- PRAGMA busy_timeout = 5000;       -- 5 second timeout
-- PRAGMA optimize;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Sessions table: Manages shared context workspaces
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    purpose TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT NOT NULL,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),

    -- Removed REGEXP constraint - validation moved to Pydantic models
    -- Session ID format validation now handled in application layer
    CONSTRAINT sessions_purpose_not_empty CHECK (length(trim(purpose)) > 0),
    CONSTRAINT sessions_created_by_not_empty CHECK (length(trim(created_by)) > 0)
);

-- Messages table: Stores all agent communications
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    sender_type TEXT DEFAULT 'generic',  -- Phase 3: Agent type denormalized for performance
    content TEXT NOT NULL,
    visibility TEXT DEFAULT 'public' CHECK (visibility IN ('public', 'private', 'agent_only', 'admin_only')),
    message_type TEXT DEFAULT 'agent_response',
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_message_id INTEGER,

    CONSTRAINT messages_session_id_not_empty CHECK (length(trim(session_id)) > 0),
    CONSTRAINT messages_sender_not_empty CHECK (length(trim(sender)) > 0),
    CONSTRAINT messages_sender_type_not_empty CHECK (length(trim(sender_type)) > 0),
    CONSTRAINT messages_content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT messages_content_length CHECK (length(content) <= 100000),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- Agent memory table: Private persistent storage
CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,  -- NULL for global memory
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    CONSTRAINT agent_memory_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),
    CONSTRAINT agent_memory_key_not_empty CHECK (length(trim(key)) > 0),
    CONSTRAINT agent_memory_key_length CHECK (length(key) <= 255),
    CONSTRAINT agent_memory_value_not_empty CHECK (length(trim(value)) > 0),
    CONSTRAINT agent_memory_expires_at_future CHECK (expires_at IS NULL OR expires_at > created_at),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Audit log table: Security and debugging
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    resource TEXT,
    action TEXT,
    result TEXT,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata)),

    CONSTRAINT audit_log_event_type_not_empty CHECK (length(trim(event_type)) > 0),
    CONSTRAINT audit_log_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

-- ============================================================================
-- UPDATE TRIGGERS
-- ============================================================================
-- Fix: DEFAULT CURRENT_TIMESTAMP doesn't update on UPDATE operations
-- These triggers ensure updated_at fields are maintained automatically

CREATE TRIGGER IF NOT EXISTS sessions_updated_at_trigger
    AFTER UPDATE ON sessions
    FOR EACH ROW
BEGIN
    UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS agent_memory_updated_at_trigger
    AFTER UPDATE ON agent_memory
    FOR EACH ROW
BEGIN
    UPDATE agent_memory SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================
-- Optimized for multi-agent concurrent access patterns

-- Primary message access patterns
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_sender_timestamp ON messages(sender, timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_visibility_session ON messages(visibility, session_id);
CREATE INDEX IF NOT EXISTS idx_messages_parent_id ON messages(parent_message_id) WHERE parent_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_sender_type ON messages(sender_type, timestamp);  -- Phase 3: Agent type filtering

-- Agent memory access patterns
CREATE INDEX IF NOT EXISTS idx_agent_memory_lookup ON agent_memory(agent_id, session_id, key);
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_global ON agent_memory(agent_id) WHERE session_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_agent_memory_expiry ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_agent_memory_session ON agent_memory(session_id) WHERE session_id IS NOT NULL;

-- Agent memory uniqueness constraints (SQLite partial index approach)
-- Global memory: enforce unique (agent_id, key) when session_id IS NULL
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_memory_unique_global ON agent_memory(agent_id, key) WHERE session_id IS NULL;
-- Session memory: enforce unique (agent_id, session_id, key) when session_id IS NOT NULL  
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_memory_unique_session ON agent_memory(agent_id, session_id, key) WHERE session_id IS NOT NULL;

-- Audit log access patterns
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_agent_time ON audit_log(agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_session_time ON audit_log(session_id, timestamp) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type, timestamp);

-- Session access patterns
CREATE INDEX IF NOT EXISTS idx_sessions_created_by ON sessions(created_by);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at);

-- ============================================================================
-- CLEANUP VIEWS
-- ============================================================================
-- Helpful views for monitoring and maintenance

-- Active sessions with recent activity
CREATE VIEW IF NOT EXISTS active_sessions_with_activity AS
SELECT
    s.*,
    COUNT(m.id) as message_count,
    MAX(m.timestamp) as last_message_at,
    COUNT(DISTINCT m.sender) as unique_agents
FROM sessions s
LEFT JOIN messages m ON s.id = m.session_id
WHERE s.is_active = TRUE
GROUP BY s.id
ORDER BY last_message_at DESC;

-- Agent memory usage summary
CREATE VIEW IF NOT EXISTS agent_memory_summary AS
SELECT
    agent_id,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN session_id IS NULL THEN 1 END) as global_entries,
    COUNT(CASE WHEN session_id IS NOT NULL THEN 1 END) as session_entries,
    COUNT(CASE WHEN expires_at IS NOT NULL THEN 1 END) as expiring_entries,
    MIN(created_at) as first_entry,
    MAX(updated_at) as last_updated
FROM agent_memory
GROUP BY agent_id
ORDER BY total_entries DESC;

-- Audit activity summary
CREATE VIEW IF NOT EXISTS audit_activity_summary AS
SELECT
    agent_id,
    event_type,
    COUNT(*) as event_count,
    MIN(timestamp) as first_event,
    MAX(timestamp) as last_event
FROM audit_log
GROUP BY agent_id, event_type
ORDER BY agent_id, event_count DESC;

-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================
-- Track schema version for migration purposes

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- ============================================================================
-- SECURE TOKEN AUTHENTICATION (PRP-006)
-- ============================================================================
-- Protected token storage with Fernet encryption for JWT hiding

CREATE TABLE IF NOT EXISTS secure_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id TEXT UNIQUE NOT NULL,
    encrypted_jwt BLOB NOT NULL,
    agent_id TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure data consistency for concurrent access
    CONSTRAINT secure_tokens_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),
    CONSTRAINT secure_tokens_token_id_not_empty CHECK (length(trim(token_id)) > 0)
);

-- Indexes for efficient multi-agent access
CREATE INDEX IF NOT EXISTS idx_token_id ON secure_tokens(token_id);
CREATE INDEX IF NOT EXISTS idx_agent_expires ON secure_tokens(agent_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_expires_cleanup ON secure_tokens(expires_at);

-- Insert current schema version
INSERT OR REPLACE INTO schema_version (version, description)
VALUES (3, 'PRP-006: Added secure_tokens table with Fernet encryption for JWT hiding');

-- ============================================================================
-- INITIAL DATA VALIDATION
-- ============================================================================
-- Optional: Insert test data to validate schema works correctly

-- Test session (commented out for production)
-- INSERT INTO sessions (id, purpose, created_by, metadata)
-- VALUES ('session_test_validation', 'Schema validation test', 'system', '{"test": true}');

-- Test message (commented out for production)
-- INSERT INTO messages (session_id, sender, content, visibility, metadata)
-- VALUES ('session_test_validation', 'system', 'Schema validation message', 'public', '{"validation": true}');

-- Test agent memory (commented out for production)
-- INSERT INTO agent_memory (agent_id, key, value, metadata)
-- VALUES ('system', 'test_key', '{"test": "validation"}', '{"type": "validation"}');

-- Test audit log (commented out for production)
-- INSERT INTO audit_log (event_type, agent_id, action, result, metadata)
-- VALUES ('schema_validation', 'system', 'CREATE_TABLES', 'SUCCESS', '{"validation": true}');
