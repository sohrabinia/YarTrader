import gzip
import json
import sqlite3

import pytest

from src.Application.Deployment.sqlite_event_store import (
    EventIdentityConflict,
    SQLiteEventStore,
)


def test_append_is_idempotent_and_reopens_durably(tmp_path):
    path = tmp_path / "events.sqlite3"
    event = {"event_id": "evt-1", "event": "position_closed", "symbol": "XAUUSD", "pnl": 2.5}
    store = SQLiteEventStore(path)
    assert store.append_event(event) is True
    assert store.append_event(event) is False
    reopened = SQLiteEventStore(path)
    assert reopened.count_events() == 1
    assert list(reopened.iter_events()) == [event]
    assert reopened.integrity_check() == "ok"


def test_explicit_event_id_cannot_be_reused_for_different_payload(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    store.append_event({"event_id": "same-id", "event": "order_sent", "symbol": "XAUUSD"})
    with pytest.raises(EventIdentityConflict):
        store.append_event({"event_id": "same-id", "event": "order_failed", "symbol": "XAUUSD"})
    assert store.count_events() == 1


def test_implicit_identity_deduplicates_exact_payload_only(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    first = {"event": "observation", "symbol": "EURUSD", "timestamp_utc": "2026-10-17T10:00:00Z"}
    second = {**first, "timestamp_utc": "2026-10-17T10:01:00Z"}
    assert store.append_event(first) is True
    assert store.append_event(first) is False
    assert store.append_event(second) is True
    assert store.count_events() == 2


def test_import_jsonl_and_gzip_is_atomic_and_idempotent(tmp_path):
    source = tmp_path / "events.jsonl"
    events = [
        {"event_id": "a", "event": "decision", "symbol": "XAUUSD"},
        {"event_id": "b", "event": "trade_closed", "symbol": "EURUSD"},
    ]
    source.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    store = SQLiteEventStore(tmp_path / "canonical.sqlite3")
    assert store.import_jsonl_file(source) == {"rows": 2, "imported": 2, "duplicates": 0}
    assert store.import_jsonl_file(source) == {"rows": 2, "imported": 0, "duplicates": 2}

    compressed = tmp_path / "events.jsonl.gz"
    with gzip.open(compressed, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(events[1]) + "\n")
        handle.write(json.dumps({"event_id": "c", "event": "risk_block", "symbol": "XAUUSD"}) + "\n")
    assert store.import_jsonl_file(compressed) == {"rows": 2, "imported": 1, "duplicates": 1}
    assert store.count_events() == 3
    assert store.integrity_check() == "ok"


def test_malformed_source_rolls_back_whole_file(tmp_path):
    source = tmp_path / "broken.jsonl"
    source.write_text(
        json.dumps({"event_id": "valid", "event": "ok"}) + "\nnot-json\n",
        encoding="utf-8",
    )
    store = SQLiteEventStore(tmp_path / "canonical.sqlite3")
    with pytest.raises(ValueError, match="Invalid JSON"):
        store.import_jsonl_file(source)
    assert store.count_events() == 0


def test_backup_uses_consistent_database_copy(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    store.append_event({"event_id": "one", "event": "decision"})
    backup = store.backup_to(tmp_path / "backup" / "events-copy.sqlite3")
    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_import_legacy_trade_journal_snapshot(tmp_path):
    snapshot = tmp_path / "trade_journal.json"
    record = {
        "trade_id": "TR-LEGACY-1",
        "decision_id": "DEC-LEGACY-1",
        "symbol": "XAUUSD",
        "trade_type": "DEMO",
        "strategy_style": "BASE_HIERARCHY",
        "result": "WIN",
    }
    snapshot.write_text(json.dumps([record]), encoding="utf-8")
    store = SQLiteEventStore(tmp_path / "canonical.sqlite3")
    assert store.import_trade_journal_snapshot(snapshot) == {
        "rows": 1, "imported": 1, "duplicates": 0
    }
    event = list(store.iter_events())[0]
    assert event["event"] == "trade_record_created"
    assert event["trade_id"] == "TR-LEGACY-1"
    assert event["record"] == record
