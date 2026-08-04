import json
import sqlite3
import datetime
from typing import Dict, Any, List, Optional
from src.Growth.ContentIntelligence.database import ContentDBManager

class ContentRepository:
    """
    CRUD repository for storing and retrieving Content drafts, lineage source tracings,
    and Trust review audit logs.
    """

    def __init__(self, db_manager: Optional[ContentDBManager] = None) -> None:
        self.db_manager = db_manager or ContentDBManager()
        # Initialize schema automatically
        self.db_manager.up()

    def create_draft(self, draft_id: str, title: str, body: str, format_type: str, language: str, status: str, source_id: str, symbols: List[str]) -> Dict[str, Any]:
        """
        Inserts a new content draft and links its source lineage metrics securely.
        """
        now_str = datetime.datetime.now(datetime.UTC).isoformat() + "Z"
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Insert draft
            cursor.execute("""
                INSERT INTO ContentDraft (id, title, body, format, language, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (draft_id, title, body, format_type, language, status, now_str))

            # Link source lineage references
            # Standard sources: source_intelligence_id
            cursor.execute("""
                INSERT INTO ContentSource (content_id, source_type, source_reference)
                VALUES (?, 'INTEL_ID', ?)
            """, (draft_id, source_id))

            # Link symbols
            for symbol in symbols:
                cursor.execute("""
                    INSERT INTO ContentSource (content_id, source_type, source_reference)
                    VALUES (?, 'SYMBOL', ?)
                """, (draft_id, symbol))

            conn.commit()

        return {
            "id": draft_id,
            "title": title,
            "body": body,
            "format": format_type,
            "language": language,
            "status": status,
            "created_at": now_str,
            "source_intelligence_id": source_id,
            "symbols": symbols
        }

    def save_review(self, content_id: str, status: str, violations: List[Dict[str, Any]], disclosures: List[str]) -> None:
        """
        Inserts or replaces a Trust Review log for the given content draft, changing draft status.
        """
        now_str = datetime.datetime.now(datetime.UTC).isoformat() + "Z"
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Insert or replace review log
            cursor.execute("""
                INSERT OR REPLACE INTO ContentReview (content_id, status, violations, disclosures, reviewed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (content_id, status, json.dumps(violations), json.dumps(disclosures), now_str))

            # Update the draft status accordingly
            cursor.execute("""
                UPDATE ContentDraft
                SET status = ?
                WHERE id = ?
            """, (status, content_id))

            conn.commit()

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed draft metadata, source lineages, and trust audit logs.
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Fetch draft details
            cursor.execute("SELECT * FROM ContentDraft WHERE id = ?", (draft_id,))
            draft_row = cursor.fetchone()
            if not draft_row:
                return None

            draft = dict(draft_row)

            # Fetch source traces
            cursor.execute("SELECT * FROM ContentSource WHERE content_id = ?", (draft_id,))
            source_rows = cursor.fetchall()

            source_id = None
            symbols = []
            for r in source_rows:
                if r["source_type"] == "INTEL_ID":
                    source_id = r["source_reference"]
                elif r["source_type"] == "SYMBOL":
                    symbols.append(r["source_reference"])

            draft["source_intelligence_id"] = source_id
            draft["symbols"] = symbols

            # Fetch review audits
            cursor.execute("SELECT * FROM ContentReview WHERE content_id = ?", (draft_id,))
            review_row = cursor.fetchone()
            if review_row:
                draft["review"] = {
                    "status": review_row["status"],
                    "violations": json.loads(review_row["violations"]),
                    "disclosures": json.loads(review_row["disclosures"]),
                    "reviewed_at": review_row["reviewed_at"]
                }
            else:
                draft["review"] = None

            return draft

    def list_drafts(self, status: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Queries and lists stored drafts with clean filters on status and underlying symbols.
        """
        query = "SELECT * FROM ContentDraft"
        params = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if symbol:
            conditions.append("""
                id IN (
                    SELECT content_id FROM ContentSource
                    WHERE source_type = 'SYMBOL' AND source_reference = ?
                )
            """)
            params.append(symbol.upper())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        drafts = []
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for r in rows:
                drafts.append(self.get_draft(r["id"]))

        return drafts
