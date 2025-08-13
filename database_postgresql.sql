-- Shared Context MCP Server Database Schema - PostgreSQL
-- Optimized for PostgreSQL with native data types and performance features
--
-- Key PostgreSQL optimizations:
-- 1. SERIAL and BIGSERIAL for auto-increment primary keys
-- 2. JSONB for metadata fields with native JSON operations
-- 3. Native timestamp handling with timezone support
-- 4. Optimized constraints and indexes for PostgreSQL
-- 5. Proper varchar sizing and text fields

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Sessions table: Manages shared context workspaces
CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    purpose TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(255) NOT NULL,
    metadata JSONB,

    CONSTRAINT sessions_purpose_not_empty CHECK (length(trim(purpose)) > 0),
    CONSTRAINT sessions_created_by_not_empty CHECK (length(trim(created_by)) > 0)
);

-- Messages table: Stores all agent communications
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    sender_type VARCHAR(50) DEFAULT 'generic',
    content TEXT NOT NULL,
    visibility VARCHAR(20) DEFAULT 'public' CHECK (visibility IN ('public', 'private', 'agent_only', 'admin_only')),
    message_type VARCHAR(50) DEFAULT 'agent_response',
    metadata JSONB,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    parent_message_id BIGINT,

    CONSTRAINT messages_session_id_not_empty CHECK (length(trim(session_id)) > 0),
    CONSTRAINT messages_sender_not_empty CHECK (length(trim(sender)) > 0),
    CONSTRAINT messages_sender_type_not_empty CHECK (length(trim(sender_type)) > 0),
    CONSTRAINT messages_content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT messages_content_length CHECK (length(content) <= 100000),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- Agent memory table: Private persistent storage
CREATE TABLE agent_memory (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),  -- NULL for global memory
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,

    CONSTRAINT agent_memory_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),
    CONSTRAINT agent_memory_key_not_empty CHECK (length(trim(key)) > 0),
    CONSTRAINT agent_memory_key_length CHECK (length(key) <= 255),
    CONSTRAINT agent_memory_value_not_empty CHECK (length(trim(value)) > 0),
    CONSTRAINT agent_memory_expires_at_future CHECK (expires_at IS NULL OR expires_at > created_at),

    UNIQUE(agent_id, session_id, key),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Audit log table: Security and debugging
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    resource VARCHAR(255),
    action VARCHAR(100),
    result VARCHAR(100),
    metadata JSONB,

    CONSTRAINT audit_log_event_type_not_empty CHECK (length(trim(event_type)) > 0),
    CONSTRAINT audit_log_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

-- ============================================================================
-- UPDATE TRIGGERS (PostgreSQL Function + Trigger approach)
-- ============================================================================

-- Function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic updated_at maintenance
CREATE TRIGGER sessions_updated_at_trigger
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER agent_memory_updated_at_trigger
    BEFORE UPDATE ON agent_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================
-- Optimized for PostgreSQL multi-agent concurrent access patterns

-- Primary message access patterns
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_session_time ON messages(session_id, timestamp);
CREATE INDEX idx_messages_sender_timestamp ON messages(sender, timestamp);
CREATE INDEX idx_messages_visibility_session ON messages(visibility, session_id);
CREATE INDEX idx_messages_parent_id ON messages(parent_message_id) WHERE parent_message_id IS NOT NULL;
CREATE INDEX idx_messages_sender_type ON messages(sender_type, timestamp);

-- Agent memory access patterns with PostgreSQL optimizations
CREATE INDEX idx_agent_memory_lookup ON agent_memory(agent_id, session_id, key);
CREATE INDEX idx_agent_memory_agent_global ON agent_memory(agent_id) WHERE session_id IS NULL;
CREATE INDEX idx_agent_memory_expiry ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_agent_memory_session ON agent_memory(session_id) WHERE session_id IS NOT NULL;

-- Audit log access patterns
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_agent_time ON audit_log(agent_id, timestamp);
CREATE INDEX idx_audit_log_session_time ON audit_log(session_id, timestamp) WHERE session_id IS NOT NULL;
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type, timestamp);

-- Session access patterns
CREATE INDEX idx_sessions_created_by ON sessions(created_by);
CREATE INDEX idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at);

-- JSONB indexes for metadata fields (PostgreSQL-specific)
CREATE INDEX idx_messages_metadata_gin ON messages USING GIN (metadata);
CREATE INDEX idx_sessions_metadata_gin ON sessions USING GIN (metadata);
CREATE INDEX idx_agent_memory_metadata_gin ON agent_memory USING GIN (metadata);
CREATE INDEX idx_audit_log_metadata_gin ON audit_log USING GIN (metadata);

-- ============================================================================
-- CLEANUP VIEWS
-- ============================================================================

-- Active sessions with recent activity
CREATE VIEW active_sessions_with_activity AS
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
CREATE VIEW agent_memory_summary AS
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
CREATE VIEW audit_activity_summary AS
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

CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- ============================================================================
-- SECURE TOKEN AUTHENTICATION (PRP-006)
-- ============================================================================

CREATE TABLE secure_tokens (
    id BIGSERIAL PRIMARY KEY,
    token_id VARCHAR(255) UNIQUE NOT NULL,
    encrypted_jwt BYTEA NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT secure_tokens_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),
    CONSTRAINT secure_tokens_token_id_not_empty CHECK (length(trim(token_id)) > 0)
);

-- Indexes for efficient multi-agent access
CREATE INDEX idx_token_id ON secure_tokens(token_id);
CREATE INDEX idx_agent_expires ON secure_tokens(agent_id, expires_at);
CREATE INDEX idx_expires_cleanup ON secure_tokens(expires_at);

-- Insert current schema version
INSERT INTO schema_version (version, description)
VALUES (3, 'PRP-010: PostgreSQL schema with JSONB, TIMESTAMPTZ, and optimized indexes')
ON CONFLICT (version) DO UPDATE SET
    description = EXCLUDED.description,
    applied_at = CURRENT_TIMESTAMP;
