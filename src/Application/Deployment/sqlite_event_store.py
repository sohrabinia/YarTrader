"""Canonical, idempotent SQLite event ledger for YarTrader runtime evidence.

The ledger is the authoritative store for important lifecycle events. JSONL files
remain import-only compatibility inputs; production writers should append here.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class EventIdentityConflict(RuntimeError):
    """Raised when one explicit event ID is reused for different event content."""


class SQLiteEventStore:
    """Append-only event ledger with durable commits and content-aware deduplication."""

    def __init__(self, path: str | os.PathLike[str], *, busy_timeout_ms: int = 5000) -> None:
        self.path = Path(path).expanduser().resolve()
        self.busy_timeout_ms = max(100, int(busy_timeout_ms))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path),
            timeout=self.busy_timeout_ms / 1000.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp_utc);
                CREATE INDEX IF NOT EXISTS idx_events_type_timestamp
                    ON events(event_type, timestamp_utc);
                CREATE INDEX IF NOT EXISTS idx_events_symbol_timestamp
                    ON events(symbol, timestamp_utc);
                CREATE TABLE IF NOT EXISTS event_sources (
                    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
                    source_file TEXT NOT NULL,
                    source_line INTEGER NOT NULL,
                    imported_at_utc TEXT NOT NULL,
                    PRIMARY KEY(event_id, source_file, source_line)
                );
                """
            )

    @staticmethod
    def _serialize(event: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
        if not isinstance(event, dict):
            raise TypeError("A journal event must be a JSON object.")
        try:
            payload = json.dumps(
                event, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                default=str, allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Journal event is not valid finite JSON.") from exc
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        explicit_id = event.get("event_id")
        if explicit_id is None:
            explicit_id = event.get("eventId")
        event_id = str(explicit_id).strip() if explicit_id is not None else ""
        if not event_id:
            event_id = digest
        event_type = str(event.get("event") or event.get("event_type") or "unclassified")
        symbol = str(event.get("symbol") or "UNKNOWN").strip().upper() or "UNKNOWN"
        timestamp = str(
            event.get("timestamp_utc")
            or event.get("timestamp")
            or datetime.now(timezone.utc).isoformat()
        )
        return event_id, event_type, symbol, timestamp, payload, digest

    @staticmethod
    def _insert(
        connection: sqlite3.Connection,
        event: dict[str, Any],
        *,
        source_file: str = "runtime",
        source_line: int = 0,
    ) -> bool:
        event_id, event_type, symbol, timestamp, payload, digest = SQLiteEventStore._serialize(event)
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO events
                (event_id, event_type, symbol, timestamp_utc, payload_json,
                 payload_sha256, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, event_type, symbol, timestamp, payload, digest, now),
        )
        row = connection.execute(
            "SELECT payload_sha256 FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError("Event insert did not create or resolve a durable row.")
        if row["payload_sha256"] != digest:
            raise EventIdentityConflict(
                f"event_id {event_id!r} already exists with different content."
            )
        connection.execute(
            """
            INSERT OR IGNORE INTO event_sources
                (event_id, source_file, source_line, imported_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (event_id, str(source_file), int(source_line), now),
        )
        return cursor.rowcount == 1

    def append_event(self, event: dict[str, Any], *, source: str = "runtime") -> bool:
        """Append one event; return False for an exact/idempotent duplicate."""
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                inserted = self._insert(connection, event, source_file=source, source_line=0)
                connection.commit()
                return inserted
            except Exception:
                connection.rollback()
                raise

    def import_jsonl_file(self, source_path: str | os.PathLike[str]) -> dict[str, int]:
        """Import one JSONL or gzip-compressed JSONL atomically and idempotently.

        Any malformed non-empty line rolls back the entire file import. Callers
        must not delete a source unless this method succeeds and integrity_check passes.
        """
        source = Path(source_path).resolve()
        opener = gzip.open if source.name.lower().endswith(".gz") else open
        imported = duplicates = rows = 0
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                with opener(source, "rt", encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise ValueError(
                                f"Invalid JSON at {source}:{line_number}"
                            ) from exc
                        if not isinstance(event, dict):
                            raise ValueError(
                                f"Expected a JSON object at {source}:{line_number}"
                            )
                        rows += 1
                        inserted = self._insert(
                            connection, event, source_file=str(source), source_line=line_number
                        )
                        if inserted:
                            imported += 1
                        else:
                            duplicates += 1
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {"rows": rows, "imported": imported, "duplicates": duplicates}

    def count_events(self) -> int:
        with closing(self._connect()) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def count_sources(self) -> int:
        with closing(self._connect()) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM event_sources").fetchone()[0])

    def integrity_check(self) -> str:
        with closing(self._connect()) as connection:
            rows = connection.execute("PRAGMA integrity_check").fetchall()
        result = "; ".join(str(row[0]) for row in rows)
        if result.lower() != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
        return result

    def iter_events(self, *, limit: int | None = None) -> Iterable[dict[str, Any]]:
        query = "SELECT payload_json FROM events ORDER BY timestamp_utc, event_id"
        params: tuple[Any, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (max(0, int(limit)),)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        for row in rows:
            yield json.loads(row["payload_json"])

    def backup_to(self, destination: str | os.PathLike[str]) -> Path:
        """Create a consistent SQLite backup using SQLite's backup API (not file copy)."""
        target = Path(destination).expanduser().resolve()
        if target == self.path:
            raise ValueError("Backup destination must differ from the live database.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as source, closing(sqlite3.connect(str(target))) as backup:
            source.backup(backup)
        return target
