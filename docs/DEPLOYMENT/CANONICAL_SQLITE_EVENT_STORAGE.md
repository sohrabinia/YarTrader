# Canonical SQLite event storage

## Authority and retention

`runtime_logs/yartrader_events.sqlite3` is the canonical append-only ledger for production autonomous DEMO, trade-journal, and honest walk-forward backtest events. The database uses SQLite WAL, `synchronous=FULL`, a bounded busy timeout, explicit identity conflict checks, and content-derived IDs when an event does not provide a stable `event_id`.

Do not write the same production lifecycle event to multiple JSONL streams. Custom journal paths used by tests can continue to use JSONL fixtures.

## Migration procedure

1. Stop or pause writers during the final migration window; do not migrate while a producer is appending to the same legacy file.
2. Run a read-only inventory first:

   ```powershell
python scripts/migrate_runtime_journal_to_sqlite.py --runtime-root runtime_logs --database runtime_logs/yartrader_events.sqlite3
```

3. Import the source files:

   ```powershell
python scripts/migrate_runtime_journal_to_sqlite.py --runtime-root runtime_logs --database runtime_logs/yartrader_events.sqlite3 --apply
```

4. Confirm event counts and `PRAGMA integrity_check` returns `ok`. Re-run the import if needed; it is idempotent.
5. Only after reconciliation, and only when intentionally discarding the old event streams, run with `--apply --delete-sources`. This removes only matching journal JSONL/gzip source files that were imported successfully. It does not clean unrelated datasets, state files, or application logs.
6. Use `SQLiteEventStore.backup_to()` for a consistent backup. Do not copy the live database file directly while it is open.

## What must not be removed by generic cleanup

Keep current execution/reconciliation state, kill-switch state, pending learning signals, validated learning memory, and any SQLite databases that are still read by the running code. Large raw historical datasets, temporary backtest outputs, and old diagnostic logs should have a separate retention policy after their consumers have been identified.

The migration script is dry-run by default. It never deletes files unless `--apply --delete-sources` is supplied explicitly.
