import json
import subprocess
import sys
from pathlib import Path


def test_partial_migration_never_deletes_any_source(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    runtime_root = tmp_path / "runtime_logs"
    runtime_root.mkdir()
    good_source = runtime_root / "autonomous_demo_trader.jsonl"
    bad_source = runtime_root / "trade_journal_events_v2.jsonl"
    database = runtime_root / "yartrader_events.sqlite3"

    good_source.write_text(
        json.dumps({
            "event_id": "good-1",
            "event": "trade_outcome_learned",
            "trade_id": "TR-GOOD",
            "symbol": "XAUUSD",
            "result": "WIN",
        }) + "\n",
        encoding="utf-8",
    )
    bad_source.write_text(
        json.dumps({
            "event_id": "bad-1",
            "event": "trade_outcome_learned",
            "trade_id": "TR-BAD",
            "symbol": "XAUUSD",
            "result": "LOSS",
        }) + "\nnot-json\n",
        encoding="utf-8",
    )

    script = repo_root / "scripts" / "migrate_runtime_journal_to_sqlite.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--runtime-root", str(runtime_root),
            "--database", str(database),
            "--apply",
            "--delete-sources",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Refusing source deletion" in result.stdout
    assert good_source.exists(), "A successfully imported source must remain if any source fails."
    assert bad_source.exists(), "The failed source must remain available for repair."
    assert database.exists()
