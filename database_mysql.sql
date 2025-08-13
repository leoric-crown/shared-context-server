-- Shared Context MCP Server Database Schema - MySQL
-- Optimized for MySQL with native data types and InnoDB performance features
--
-- Key MySQL optimizations:
-- 1. AUTO_INCREMENT for primary keys with proper data types
-- 2. JSON data type for metadata fields with native JSON operations
-- 3. Proper charset and collation settings (utf8mb4)
-- 4. InnoDB engine with optimized indexes and constraints
-- 5. Appropriate VARCHAR sizing and TEXT fields

-- Set charset and collation for the session
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Sessions table: Manages shared context workspaces
CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    purpose TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(255) NOT NULL,
    metadata JSON,

    CONSTRAINT sessions_purpose_not_empty CHECK (CHAR_LENGTH(TRIM(purpose)) > 0),
    CONSTRAINT sessions_created_by_not_empty CHECK (CHAR_LENGTH(TRIM(created_by)) > 0),
    CONSTRAINT sessions_metadata_valid CHECK (metadata IS NULL OR JSON_VALID(metadata))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Messages table: Stores all agent communications
CREATE TABLE messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    sender_type VARCHAR(50) DEFAULT 'generic',
    content TEXT NOT NULL,
    visibility ENUM('public', 'private', 'agent_only', 'admin_only') DEFAULT 'public',
    message_type VARCHAR(50) DEFAULT 'agent_response',
    metadata JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_message_id BIGINT,

    CONSTRAINT messages_session_id_not_empty CHECK (CHAR_LENGTH(TRIM(session_id)) > 0),
    CONSTRAINT messages_sender_not_empty CHECK (CHAR_LENGTH(TRIM(sender)) > 0),
    CONSTRAINT messages_sender_type_not_empty CHECK (CHAR_LENGTH(TRIM(sender_type)) > 0),
    CONSTRAINT messages_content_not_empty CHECK (CHAR_LENGTH(TRIM(content)) > 0),
    CONSTRAINT messages_content_length CHECK (CHAR_LENGTH(content) <= 100000),
    CONSTRAINT messages_metadata_valid CHECK (metadata IS NULL OR JSON_VALID(metadata)),

    INDEX idx_session_id (session_id),
    INDEX idx_parent_message_id (parent_message_id),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agent memory table: Private persistent storage
CREATE TABLE agent_memory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NULL,  -- NULL for global memory
    key_name VARCHAR(255) NOT NULL,  -- 'key' is reserved in MySQL
    value TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,

    CONSTRAINT agent_memory_agent_id_not_empty CHECK (CHAR_LENGTH(TRIM(agent_id)) > 0),
    CONSTRAINT agent_memory_key_not_empty CHECK (CHAR_LENGTH(TRIM(key_name)) > 0),
    CONSTRAINT agent_memory_key_length CHECK (CHAR_LENGTH(key_name) <= 255),
    CONSTRAINT agent_memory_value_not_empty CHECK (CHAR_LENGTH(TRIM(value)) > 0),
    CONSTRAINT agent_memory_expires_at_future CHECK (expires_at IS NULL OR expires_at > created_at),
    CONSTRAINT agent_memory_metadata_valid CHECK (metadata IS NULL OR JSON_VALID(metadata)),

    UNIQUE KEY unique_agent_session_key (agent_id, session_id, key_name),
    INDEX idx_session_id (session_id),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit log table: Security and debugging
CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NULL,
    resource VARCHAR(255) NULL,
    action VARCHAR(100) NULL,
    result VARCHAR(100) NULL,
    metadata JSON,

    CONSTRAINT audit_log_event_type_not_empty CHECK (CHAR_LENGTH(TRIM(event_type)) > 0),
    CONSTRAINT audit_log_agent_id_not_empty CHECK (CHAR_LENGTH(TRIM(agent_id)) > 0),
    CONSTRAINT audit_log_metadata_valid CHECK (metadata IS NULL OR JSON_VALID(metadata)),

    INDEX idx_session_id (session_id),

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================
-- Optimized for MySQL/InnoDB multi-agent concurrent access patterns

-- Primary message access patterns
CREATE INDEX idx_messages_session_time ON messages(session_id, timestamp);
CREATE INDEX idx_messages_sender_timestamp ON messages(sender, timestamp);
CREATE INDEX idx_messages_visibility_session ON messages(visibility, session_id);
CREATE INDEX idx_messages_sender_type ON messages(sender_type, timestamp);

-- Agent memory access patterns with MySQL optimizations
CREATE INDEX idx_agent_memory_lookup ON agent_memory(agent_id, session_id, key_name);
CREATE INDEX idx_agent_memory_agent_global ON agent_memory(agent_id, session_id) WHERE session_id IS NULL;
CREATE INDEX idx_agent_memory_expiry ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_agent_memory_session ON agent_memory(session_id) WHERE session_id IS NOT NULL;

-- Audit log access patterns
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_agent_time ON audit_log(agent_id, timestamp);
CREATE INDEX idx_audit_log_session_time ON audit_log(session_id, timestamp);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type, timestamp);

-- Session access patterns
CREATE INDEX idx_sessions_created_by ON sessions(created_by);
CREATE INDEX idx_sessions_active ON sessions(is_active);
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at);

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
GROUP BY s.id, s.purpose, s.created_at, s.updated_at, s.is_active, s.created_by, s.metadata
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
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SECURE TOKEN AUTHENTICATION (PRP-006)
-- ============================================================================

CREATE TABLE secure_tokens (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    token_id VARCHAR(255) UNIQUE NOT NULL,
    encrypted_jwt LONGBLOB NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT secure_tokens_agent_id_not_empty CHECK (CHAR_LENGTH(TRIM(agent_id)) > 0),
    CONSTRAINT secure_tokens_token_id_not_empty CHECK (CHAR_LENGTH(TRIM(token_id)) > 0),

    INDEX idx_token_id (token_id),
    INDEX idx_agent_expires (agent_id, expires_at),
    INDEX idx_expires_cleanup (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert current schema version
INSERT INTO schema_version (version, description)
VALUES (3, 'PRP-010: MySQL schema with JSON, AUTO_INCREMENT, and InnoDB optimizations')
ON DUPLICATE KEY UPDATE
    description = VALUES(description),
    applied_at = CURRENT_TIMESTAMP;
