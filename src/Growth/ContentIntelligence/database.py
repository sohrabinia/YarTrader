import os
import sqlite3
import logging

logger = logging.getLogger("ContentDBManager")

class ContentDBManager:
    """
    Manages connections and schema execution for the isolated Content Intelligence database
    located at runtime_logs/content_intelligence.db.
    """

    def __init__(self, db_path: str = "runtime_logs/content_intelligence.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def up(self) -> None:
        """
        Executes isolated database migrations, creating Content draft storage tables.
        Guarantees that existing core intelligence tables are completely untouched.
        """
        logger.info("Executing isolated content intelligence database migration up()")
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. ContentDraft table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ContentDraft (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    format TEXT NOT NULL,
                    language TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # 2. ContentSource table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ContentSource (
                    content_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    PRIMARY KEY (content_id, source_type, source_reference),
                    FOREIGN KEY (content_id) REFERENCES ContentDraft(id) ON DELETE CASCADE
                )
            """)

            # 3. ContentReview table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ContentReview (
                    content_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    violations TEXT NOT NULL, -- JSON serialized string
                    disclosures TEXT NOT NULL, -- JSON serialized string
                    reviewed_at TEXT NOT NULL,
                    FOREIGN KEY (content_id) REFERENCES ContentDraft(id) ON DELETE CASCADE
                )
            """)

            conn.commit()

    def down(self) -> None:
        """
        Reverses the migrations by dropping the isolated content storage tables cleanly.
        """
        logger.info("Executing content database migration rollback down()")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS ContentReview")
            cursor.execute("DROP TABLE IF EXISTS ContentSource")
            cursor.execute("DROP TABLE IF EXISTS ContentDraft")
            conn.commit()
