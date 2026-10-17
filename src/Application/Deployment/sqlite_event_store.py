"""Canonical, idempotent SQLite event ledger for YarTrader runtime evidence.

The ledger is the authoritative store for important lifecycle events. JSONL files
remain import-only compatibility inputs; production writers should append here.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sqlite3
import zlib
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class EventIdentityConflict(RuntimeError):
    """Raised when one explicit event ID is reused for different event content."""


IMPORTANT_EVENT_NAMES = {
    "trade_record_created", "trade_record_updated", "backtest_trade_closed",
    "trade_outcome_learned", "trade_outcome_learning_failed", "entry_execution_outcome",
    "execution_reconciliation_required", "strategy_position_exit", "base_position_exit",
    "base_position_exit_reconciliation", "strategy_structural_trailing_stop",
    "strategy_take_profit_extended", "base_structural_profit_protection",
    "strategy_learning_sync", "strategy_learning_sync_unavailable",
    "pending_order_replacement_completed", "pending_order_cancel_result",
    "watch_only_existing_pending_order_cancelled",
    "watch_only_existing_pending_order_cancel_failed", "duplicate_pending_order_reconciled",
    "trade_review_started", "trade_style_transition", "post_exit_price_tracking_completed",
    "post_exit_price_tracking_incomplete", "post_exit_price_tracking_started",
    "entry_blocked_invalid_risk_sizing_facts", "entry_rejected_crossed_trigger",
    "entry_rejected_excessive_drift", "reentry_blocked_identical_closed_setup",
    "demo_strategy_exploration_selected", "demo_exploration_rr_floor_applied",
    "setup_zone_watch_state_transition", "setup_zone_watch_only",
}
LOW_VALUE_EVENT_NAMES = {
    "cycle_status", "pending_order_review_cycle", "heartbeat", "worker_heartbeat",
    "market_snapshot", "analysis_snapshot", "research_snapshot",
}
_EVENT_NAME_PATTERN = re.compile(r'"(?:event|event_type)"\s*:\s*"([^"]+)"')
_EVENT_ID_PATTERN = re.compile(
    r'"(?:trade_id|order_ticket|deal_ticket|broker_order_id|'
    r'position_id|execution_id|reconciliation_id)"\s*:'
)


def is_important_event_line(line: str) -> bool:
    """Cheaply skip known low-value telemetry before decoding huge JSON payloads."""
    match = _EVENT_NAME_PATTERN.search(line)
    if not match:
        # Unknown/malformed framing must be parsed so corruption is not silently hidden.
        return True
    name = match.group(1).strip().lower()
    has_lifecycle_id = bool(_EVENT_ID_PATTERN.search(line))
    if name in LOW_VALUE_EVENT_NAMES and not has_lifecycle_id:
        return False
    if name in IMPORTANT_EVENT_NAMES or has_lifecycle_id:
        return True
    return any(
        token in name
        for token in (
            "trade", "order", "execution", "risk", "kill_switch", "learning",
            "decision", "position", "reconcil", "entry_blocked", "entry_rejected",
            "reentry_blocked", "stop", "profit", "take_profit",
        )
    )


def is_important_event(event: dict[str, Any]) -> bool:
    """Keep decision/execution/risk/trade/learning evidence, not periodic telemetry."""
    if not isinstance(event, dict):
        return False
    name = str(event.get("event") or event.get("event_type") or "").strip().lower()
    has_execution_or_trade_id = any(
        event.get(key)
        for key in (
            "trade_id", "order_ticket", "deal_ticket", "broker_order_id",
            "position_id", "execution_id", "reconciliation_id",
        )
    )
    if name in LOW_VALUE_EVENT_NAMES and not has_execution_or_trade_id:
        return False
    if name in IMPORTANT_EVENT_NAMES or has_execution_or_trade_id:
        return True
    return any(
        token in name
        for token in (
            "trade", "order", "execution", "risk", "kill_switch", "learning",
            "decision", "position", "reconcil", "entry_blocked", "entry_rejected",
            "reentry_blocked", "stop", "profit", "take_profit",
        )
    )


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    """Drop repeated bulky analysis blobs while retaining lifecycle and outcome facts."""
    if any(key in event for key in ("record", "updated_record")):
        return dict(event)
    compact = dict(event)
    removed_context = False
    for key in (
        "base_plan", "plan", "base_analysis", "hierarchy_structure", "structure",
        "historical_structure_analysis", "structural_levels", "structural_hierarchy",
        "level_reaction_evidence", "entry_level_context", "breakout_rejection_outcome",
        "market_structure_snapshot", "indicator_snapshot", "raw_candles",
    ):
        if key in compact:
            compact.pop(key, None)
            removed_context = True
    if removed_context:
        compact["storage_compaction"] = "large_redundant_context_omitted"
    return compact


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
                    payload_blob BLOB NOT NULL,
                    payload_codec TEXT NOT NULL CHECK(payload_codec IN ('raw', 'zlib')),
                    payload_size INTEGER NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    source_line INTEGER NOT NULL,
                    created_at_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp_utc);
                CREATE INDEX IF NOT EXISTS idx_events_type_timestamp
                    ON events(event_type, timestamp_utc);
                CREATE INDEX IF NOT EXISTS idx_events_symbol_timestamp
                    ON events(symbol, timestamp_utc);
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
        # Resolve duplicates before compression; legacy archives can repeat millions
        # of events across rotated files, and recompressing duplicates wastes CPU.
        existing = connection.execute(
            "SELECT payload_sha256 FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if existing is not None:
            if existing["payload_sha256"] != digest:
                raise EventIdentityConflict(
                    f"event_id {event_id!r} already exists with different content."
                )
            return False

        raw_payload = payload.encode("utf-8")
        compressed_payload = zlib.compress(raw_payload, level=1)
        if len(compressed_payload) < len(raw_payload):
            payload_blob, payload_codec = compressed_payload, "zlib"
        else:
            payload_blob, payload_codec = raw_payload, "raw"
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO events
                (event_id, event_type, symbol, timestamp_utc, payload_blob,
                 payload_codec, payload_size, payload_sha256, source_file,
                 source_line, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, event_type, symbol, timestamp, payload_blob, payload_codec,
             len(raw_payload), digest, str(source_file), int(source_line), now),
        )
        if cursor.rowcount == 1:
            return True
        # A concurrent writer may have inserted between the lookup and insert.
        row = connection.execute(
            "SELECT payload_sha256 FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError("Event insert did not create or resolve a durable row.")
        if row["payload_sha256"] != digest:
            raise EventIdentityConflict(
                f"event_id {event_id!r} already exists with different content."
            )
        return False

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

    def append_important_event(self, event: dict[str, Any], *, source: str = "runtime") -> bool:
        """Persist only material lifecycle evidence, with repeated bulky context removed."""
        if not is_important_event(event):
            return False
        return self.append_event(compact_event(event), source=source)

    def import_jsonl_file(
        self,
        source_path: str | os.PathLike[str],
        *,
        important_only: bool = False,
    ) -> dict[str, int]:
        """Import one JSONL/gzip file atomically; optionally discard non-material telemetry.

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
                        if important_only and not is_important_event_line(line):
                            rows += 1
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
                        if important_only and not is_important_event(event):
                            continue
                        if important_only:
                            event = compact_event(event)
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

    def import_trade_journal_snapshot(self, source_path: str | os.PathLike[str]) -> dict[str, int]:
        """Import the legacy trade_journal.json array as canonical lifecycle events."""
        source = Path(source_path).resolve()
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to parse trade journal snapshot: {source}") from exc
        if isinstance(raw, dict):
            raw = raw.get("records")
        if not isinstance(raw, list):
            raise ValueError(f"Trade journal snapshot must contain a list of records: {source}")
        imported = duplicates = rows = 0
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for line_number, record in enumerate(raw, start=1):
                    if not isinstance(record, dict) or not record.get("trade_id"):
                        raise ValueError(
                            f"Invalid trade record at {source}:record {line_number}"
                        )
                    event = {
                        "event": "trade_record_created",
                        "trade_type": record.get("trade_type", "UNKNOWN"),
                        "trade_id": record["trade_id"],
                        "decision_id": record.get("decision_id"),
                        "symbol": record.get("symbol", "UNKNOWN"),
                        "strategy_style": record.get("strategy_style", "UNKNOWN"),
                        "record": record,
                    }
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
            return int(connection.execute(
                "SELECT COUNT(DISTINCT source_file) FROM events"
            ).fetchone()[0])

    def integrity_check(self) -> str:
        with closing(self._connect()) as connection:
            rows = connection.execute("PRAGMA integrity_check").fetchall()
        result = "; ".join(str(row[0]) for row in rows)
        if result.lower() != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
        return result

    def iter_events(
        self,
        *,
        event_types: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> Iterable[dict[str, Any]]:
        query = (
            "SELECT payload_blob, payload_codec, payload_size, payload_sha256 "
            "FROM events"
        )
        params_list: list[Any] = []
        if event_types is not None:
            types = tuple(str(value) for value in event_types)
            if not types:
                query += " WHERE 0"
            else:
                placeholders = ",".join("?" for _ in types)
                query += f" WHERE event_type IN ({placeholders})"
                params_list.extend(types)
        query += " ORDER BY rowid"
        if limit is not None:
            query += " LIMIT ?"
            params_list.append(max(0, int(limit)))
        params = tuple(params_list)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        for row in rows:
            blob = bytes(row["payload_blob"])
            raw = zlib.decompress(blob) if row["payload_codec"] == "zlib" else blob
            if len(raw) != int(row["payload_size"]):
                raise RuntimeError("SQLite event payload size verification failed.")
            if hashlib.sha256(raw).hexdigest() != row["payload_sha256"]:
                raise RuntimeError("SQLite event payload checksum verification failed.")
            yield json.loads(raw.decode("utf-8"))

    def backup_to(self, destination: str | os.PathLike[str]) -> Path:
        """Create a consistent SQLite backup using SQLite's backup API (not file copy)."""
        target = Path(destination).expanduser().resolve()
        if target == self.path:
            raise ValueError("Backup destination must differ from the live database.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as source, closing(sqlite3.connect(str(target))) as backup:
            source.backup(backup)
        return target
