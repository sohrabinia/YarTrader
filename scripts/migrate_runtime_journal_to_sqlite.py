"""Idempotently migrate legacy YarTrader event JSONL/gzip files into SQLite.

Dry-run is the default. Use --apply to import. Source deletion is a separate,
explicit opt-in and only applies after a successful import plus integrity check.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.Application.Deployment.sqlite_event_store import SQLiteEventStore


def _sources(runtime_root: Path) -> list[Path]:
    candidates = []
    for path in runtime_root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if not (name.endswith(".jsonl") or name.endswith(".jsonl.gz") or name.endswith(".gz")):
            continue
        if any(token in name for token in ("trade_journal_events", "autonomous_demo_trader", "legacy_autonomous_demo")):
            candidates.append(path)
    return sorted(set(candidates))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=Path("runtime_logs"))
    parser.add_argument("--database", type=Path, default=Path("runtime_logs/yartrader_events.sqlite3"))
    parser.add_argument(
        "--snapshot", action="append", type=Path, default=[],
        help="Legacy trade_journal.json snapshot to import; may be supplied more than once.",
    )
    parser.add_argument("--apply", action="store_true", help="Import into SQLite; default is read-only inventory.")
    parser.add_argument(
        "--delete-sources", action="store_true",
        help="Delete only successfully imported source files after all integrity checks pass.",
    )
    args = parser.parse_args()
    runtime_root = args.runtime_root.resolve()
    database = args.database.resolve()
    if args.delete_sources and not args.apply:
        parser.error("--delete-sources requires --apply")
    if not runtime_root.is_dir():
        parser.error(f"Runtime root does not exist: {runtime_root}")
    sources = _sources(runtime_root)
    default_snapshots = [
        runtime_root / "trade_journal.json",
        runtime_root.parent / "storage" / "Logs" / "trade_journal.json",
    ]
    snapshots = sorted({
        path.resolve() for path in [*default_snapshots, *args.snapshot]
        if path.is_file()
    })
    print(f"Runtime root: {runtime_root}")
    print(f"Target database: {database}")
    print(f"JSONL/gzip source candidates: {len(sources)}")
    print(f"Trade snapshot candidates: {len(snapshots)}")
    if not args.apply:
        for source in sources:
            print(f"WOULD_IMPORT_JSONL bytes={source.stat().st_size} {source}")
        for source in snapshots:
            print(f"WOULD_IMPORT_SNAPSHOT bytes={source.stat().st_size} {source}")
        print("Dry-run only; no data changed.")
        return 0

    store = SQLiteEventStore(database)
    successful: list[Path] = []
    failures: list[tuple[Path, str]] = []
    totals = {"rows": 0, "imported": 0, "duplicates": 0}
    for source in sources:
        try:
            result = store.import_jsonl_file(source, important_only=True)
        except Exception as exc:
            failures.append((source, str(exc)))
            print(f"FAILED_JSONL {source}: {type(exc).__name__}: {exc}")
            continue
        successful.append(source)
        for key in totals:
            totals[key] += result[key]
        print(
            f"IMPORTED_JSONL {source} rows={result['rows']} "
            f"new={result['imported']} duplicates={result['duplicates']} skipped={result['rows'] - result['imported'] - result['duplicates']}"
        )
    for source in snapshots:
        try:
            result = store.import_trade_journal_snapshot(source)
        except Exception as exc:
            failures.append((source, str(exc)))
            print(f"FAILED_SNAPSHOT {source}: {type(exc).__name__}: {exc}")
            continue
        successful.append(source)
        for key in totals:
            totals[key] += result[key]
        print(
            f"IMPORTED_SNAPSHOT {source} rows={result['rows']} "
            f"new={result['imported']} duplicates={result['duplicates']}"
        )
    print(f"TOTAL {totals}")
    print(f"EVENTS={store.count_events()} SOURCES={store.count_sources()}")
    print(f"INTEGRITY={store.integrity_check()}")
    print(f"FAILED_SOURCES={len(failures)}")
    if args.delete_sources:
        # Fail closed for the entire source set. If any candidate failed import,
        # keep every source so the operator can inspect and retry without partial cleanup.
        if failures:
            print("Refusing source deletion: one or more source files failed import; all sources preserved.")
        elif store.integrity_check() != "ok":
            raise RuntimeError("Refusing source deletion: SQLite integrity check did not pass.")
        else:
            for source in successful:
                source.unlink()
            print(f"DELETED_IMPORTED_SOURCES={len(successful)}")
    if failures:
        print("Some sources were not migrated completely; they were preserved.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
