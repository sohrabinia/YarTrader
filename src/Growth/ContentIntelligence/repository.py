import json
import sqlite3
import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.Growth.ContentIntelligence.database import ContentDBManager

class ContentRepository:
    """
    CRUD repository for storing and retrieving Content drafts, lineage source tracings,
    Trust review audit logs, Articles (P1), and Article Audit records.
    """

    def __init__(self, db_manager: Optional[ContentDBManager] = None) -> None:
        self.db_manager = db_manager or ContentDBManager()
        # Initialize schema automatically
        self.db_manager.up()

    # ==========================================
    # Phase P0 - Content Draft Operations
    # ==========================================
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

    # ==========================================
    # Phase P1 - Content Article & Audit Operations
    # ==========================================
    def create_article(self, article_id: str, title: str, body: str, html: str, format_type: str, language: str, status: str, version: str, category: str, symbols: List[str], timeframes: List[str], sentiment: str, risk_level: str, source_intelligence_id: str) -> Dict[str, Any]:
        """
        Creates and stores a new Content Article in Phase P1.
        """
        now_str = datetime.datetime.now(datetime.UTC).isoformat() + "Z"
        symbols_str = ",".join(symbols)
        timeframes_str = ",".join(timeframes)

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ContentArticle (
                    id, title, body, html, format, language, status, version, category,
                    symbols_str, timeframes_str, sentiment, risk_level, source_intelligence_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article_id, title, body, html, format_type, language, status, version, category,
                symbols_str, timeframes_str, sentiment, risk_level, source_intelligence_id, now_str
            ))
            conn.commit()

        return self.get_article(article_id)

    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves full nested details of an Article including audit logs and lineage matrix.
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ContentArticle WHERE id = ?", (article_id,))
            row = cursor.fetchone()
            if not row:
                return None

            article = dict(row)
            article["symbols"] = [s.strip() for s in article["symbols_str"].split(",") if s.strip()]
            article["timeframes"] = [t.strip() for t in article["timeframes_str"].split(",") if t.strip()]

            # Fetch audit records
            cursor.execute("SELECT * FROM ArticleAuditRecord WHERE article_id = ? ORDER BY timestamp DESC", (article_id,))
            article["audit_history"] = [dict(r) for r in cursor.fetchall()]

            # Fetch related ContentReview if exists
            cursor.execute("SELECT * FROM ContentReview WHERE content_id = ?", (article_id,))
            review_row = cursor.fetchone()
            if review_row:
                article["review"] = {
                    "status": review_row["status"],
                    "violations": json.loads(review_row["violations"]),
                    "disclosures": json.loads(review_row["disclosures"]),
                    "reviewed_at": review_row["reviewed_at"]
                }
            else:
                article["review"] = None

            return article

    def list_articles(self, status: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Queries and lists stored Articles with optional category and status filters.
        """
        query = "SELECT id FROM ContentArticle"
        params = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if category:
            conditions.append("category = ?")
            params.append(category.upper())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        articles = []
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for r in rows:
                articles.append(self.get_article(r["id"]))

        return articles

    def update_article(self, article_id: str, title: str, body: str, html: str, status: str, version: str) -> None:
        """
        Updates Article draft body/title content and sets its version level.
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ContentArticle
                SET title = ?, body = ?, html = ?, status = ?, version = ?
                WHERE id = ?
            """, (title, body, html, status, version, article_id))
            conn.commit()

    def record_audit(self, article_id: str, previous_state: str, new_state: str, actor_id: str, comment: str) -> Dict[str, Any]:
        """
        Logs a workflow status-change audit entry inside ArticleAuditRecord.
        """
        audit_id = f"aud-{uuid.uuid4().hex[:8]}"
        now_str = datetime.datetime.now(datetime.UTC).isoformat() + "Z"

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ArticleAuditRecord (id, article_id, previous_state, new_state, actor_id, comment, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (audit_id, article_id, previous_state, new_state, actor_id, comment, now_str))

            # Sync ContentArticle status automatically
            cursor.execute("""
                UPDATE ContentArticle
                SET status = ?
                WHERE id = ?
            """, (new_state, article_id))

            conn.commit()

        return {
            "id": audit_id,
            "article_id": article_id,
            "previous_state": previous_state,
            "new_state": new_state,
            "actor_id": actor_id,
            "comment": comment,
            "timestamp": now_str
        }
