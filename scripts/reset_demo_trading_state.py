"""One-time allowlisted purge of legacy YarTrader trading/learning artifacts.

Does not delete source/config/secrets, auth/business application state, or security/audit records.
Stop the YarTrader service and related workers before using --apply.
"""
from __future__ import annotations
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = [
    "runtime_logs/backtest_learning", "runtime_logs/brain_memory",
    "runtime_logs/research_center", "runtime_logs/research_snapshots",
    "storage/Data/artifacts", "storage/Runtime/research_logs",
    "storage/Logs/demo_execution", "history", "reports", "data/research",
    "logs/application", "logs/error", "logs/intelligence", "logs/runtime",
    "logs/service", "logs/watchdog", ".pytest_cache",
]
FILES = [
    "runtime_logs/daily_loss_kill_switch.json", "runtime_logs/demo_trades.json",
    "runtime_logs/learning_history.json", "runtime_logs/fractal_pattern_memory.json",
    "runtime_logs/pending_signals.json", "runtime_logs/autonomous_demo_trader.jsonl",
    "runtime_logs/ci_main_15410.log", "storage/pytest_full_20261001.log",
    "logs/validation.log", "logs/nssm_logs_archive_20260921.zip",
]

def size_and_count(path: Path) -> tuple[int, int]:
    if path.is_file():
        return path.stat().st_size, 1
    if not path.exists():
        return 0, 0
    try:
        files = [p for p in path.rglob("*") if p.is_file()]
        return sum(p.stat().st_size for p in files), len(files)
    except OSError:
        # Corrupt NTFS directory entries can prevent enumeration; still attempt deletion.
        return 0, 0

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform deletion; default is dry-run")
    args = parser.parse_args()
    targets = [ROOT / rel for rel in DIRECTORIES + FILES]
    targets.extend(p for p in (ROOT / "runtime_logs").glob("RESET_BACKUP_*") if p.is_dir())
    targets.extend(p for p in (ROOT / "runtime_logs").glob("external_xauusd_cycle.*.log") if p.is_file())
    # A prior purge found unreadable NTFS entries here; retry physical deletion after filesystem repair.
    targets.extend(p for p in (ROOT / "storage" / "Data").glob("artifacts_corrupt_quarantine_*") if p.is_dir())
    total_bytes = total_files = 0
    errors = []
    for target in targets:
        size, count = size_and_count(target)
        if not target.exists():
            continue
        total_bytes += size
        total_files += count
        print(f"{'DELETE' if args.apply else 'WOULD_DELETE'} {target.relative_to(ROOT)} files={count} bytes={size}")
        if args.apply:
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            except OSError as exc:
                errors.append((target, str(exc)))
                print(f"DELETE_FAILED {target.relative_to(ROOT)}: {exc}")
    if args.apply:
        for rel in ("runtime_logs/backtest_learning", "runtime_logs/brain_memory",
                    "runtime_logs/research_center", "runtime_logs/research_snapshots",
                    "storage/Data/artifacts", "storage/Runtime/research_logs",
                    "storage/Logs/demo_execution", "history", "reports", "data/research"):
            (ROOT / rel).mkdir(parents=True, exist_ok=True)
        print("PURGE_COMPLETE")
    else:
        print("DRY_RUN_ONLY; add --apply after stopping service/workers")
    print(f"TOTAL files={total_files} bytes={total_bytes}")
    print("PRESERVED: source/config/secrets, runtime auth/billing/business state, sessions/tickets, logs/audit, logs/security")
    if errors:
        print("DELETE_ERRORS=" + str(len(errors)))
        for target, error in errors:
            print(f"ERROR {target.relative_to(ROOT)}: {error}")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
