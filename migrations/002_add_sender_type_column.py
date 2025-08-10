#!/usr/bin/env python3
"""
Migration 002: Add sender_type column to messages table

This migration adds a sender_type column to the messages table for Phase 3
multi-agent features. This denormalizes agent type data to avoid complex joins
in visibility filtering queries.

Changes:
- Add sender_type column to messages table with default 'generic'
- Add index on sender_type for performance
- Update schema version to 2
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.shared_context_server.database import get_db_connection

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

logger = logging.getLogger(__name__)


async def migrate_up() -> None:
    """Apply migration to add sender_type column."""

    async with get_db_connection() as conn:
        # Check current schema version
        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cursor.fetchone()
        current_version = row[0] if row and row[0] is not None else 0

        if current_version >= 2:
            logger.info("Migration 002 already applied, skipping")
            return

        logger.info("Applying migration 002: Add sender_type column")

        # Add sender_type column to messages table
        await conn.execute("""
            ALTER TABLE messages
            ADD COLUMN sender_type TEXT DEFAULT 'generic'
        """)

        # Add constraint for sender_type
        # Note: SQLite doesn't support ADD CONSTRAINT, so we'll validate this in application code

        # Add index for sender_type
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_sender_type
            ON messages(sender_type, timestamp)
        """)

        # Update existing records to have sender_type = 'generic' (already set by DEFAULT)
        # This is just for safety and documentation
        await conn.execute("""
            UPDATE messages
            SET sender_type = 'generic'
            WHERE sender_type IS NULL
        """)

        # Update schema version
        await conn.execute(
            """
            INSERT OR REPLACE INTO schema_version (version, description, applied_at)
            VALUES (2, 'Phase 3: Added sender_type column to messages table for agent type denormalization', ?)
        """,
            (datetime.now(timezone.utc).isoformat(),),
        )

        await conn.commit()

        logger.info("Migration 002 applied successfully")


async def migrate_down() -> None:
    """Rollback migration (remove sender_type column)."""

    async with get_db_connection() as conn:
        logger.info("Rolling back migration 002: Remove sender_type column")

        # SQLite doesn't support DROP COLUMN, so we need to recreate the table
        # This is a simplified rollback - in production, you'd want more careful handling

        # Drop the index first
        await conn.execute("DROP INDEX IF EXISTS idx_messages_sender_type")

        # Note: Full rollback would require table recreation, which is complex
        # For now, we'll just mark the schema version as rolled back
        await conn.execute(
            """
            INSERT OR REPLACE INTO schema_version (version, description, applied_at)
            VALUES (1, 'Rollback: Removed sender_type column references', ?)
        """,
            (datetime.now(timezone.utc).isoformat(),),
        )

        await conn.commit()

        logger.warning(
            "Migration 002 rollback completed (sender_type column still exists but unused)"
        )


async def main():
    """Run migration."""
    logging.basicConfig(level=logging.INFO)

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "down":
        await migrate_down()
    else:
        await migrate_up()


if __name__ == "__main__":
    asyncio.run(main())
