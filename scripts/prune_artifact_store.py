"""Safely prune redundant MarketMemorySystem artifact snapshots.

Defaults to dry-run. Use --apply only after reviewing the planned counts/bytes.
Referenced IDs in artifact_manifest.json are always retained. The JSON memory
mirrors remain the source of truth; this store is a recovery checkpoint cache.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.Application.Deployment.artifact_store import _exclusive_file_lock


def manifest_references(roots: list[Path]) -> set[str]:
    refs: set[str] = set()
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("artifact_manifest.json"):
            if any(part in {".git", ".venv", ".venv-mt5verify", "node_modules"} for part in path.parts):
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(value, dict):
                    refs.update(str(v) for v in value.values() if isinstance(v, str) and len(v) == 64)
            except (OSError, ValueError):
                continue
    return refs


def prune_store(root: Path, refs: set[str], keep_per_source: int, grace_hours: float,
                apply: bool, backup_dir: Path | None) -> dict:
    index_path = root / "index.json"
    objects_root = root / "objects"
    if not index_path.exists() or not objects_root.exists():
        return {"root": str(root), "skipped": True, "reason": "index or objects missing"}
    if apply and backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(index_path, backup_dir / (root.parent.parent.name + "_artifact_index.json"))
    with _exclusive_file_lock(root / ".index.lock"):
        index = json.loads(index_path.read_text(encoding="utf-8-sig"))
        if not isinstance(index, dict):
            raise RuntimeError(f"Invalid artifact index root: {index_path}")
        objects: dict[str, tuple[Path, int, float]] = {}
        for path in objects_root.glob("*/*.yarz"):
            try:
                stat = path.stat()
                objects[path.stem] = (path, stat.st_size, stat.st_mtime)
            except OSError:
                continue
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        keep: set[str] = set(refs)
        for artifact_id, record in index.items():
            metadata = record.get("metadata") if isinstance(record, dict) else None
            if (isinstance(metadata, dict)
                    and metadata.get("producer") == "MarketMemorySystem"
                    and metadata.get("legacy_path") and metadata.get("layer")):
                groups[(str(metadata["legacy_path"]), str(metadata["layer"]))].append(str(artifact_id))
            else:
                keep.add(str(artifact_id))
        for ids in groups.values():
            ids.sort(key=lambda item: objects.get(item, (None, 0, 0.0))[2], reverse=True)
            keep.update(ids[:keep_per_source])
        # Keep manifest-referenced objects even if index bookkeeping lost their entries.
        for artifact_id in refs:
            if artifact_id in objects:
                keep.add(artifact_id)
        missing_unreferenced = {aid for aid in index if aid not in objects and aid not in refs}
        keep.difference_update(missing_unreferenced)
        drop_index_ids = set(index) - keep
        now = time.time()
        grace_seconds = max(0.0, grace_hours) * 3600
        drop_unindexed_paths = []
        for artifact_id, (path, size, mtime) in objects.items():
            if artifact_id not in index and artifact_id not in refs and now - mtime >= grace_seconds:
                drop_unindexed_paths.append((artifact_id, path, size))
        delete_paths = []
        total_delete_bytes = 0
        for artifact_id in drop_index_ids:
            if artifact_id in objects and artifact_id not in refs:
                path, size, _ = objects[artifact_id]
                delete_paths.append(path)
                total_delete_bytes += size
        for _, path, size in drop_unindexed_paths:
            delete_paths.append(path)
            total_delete_bytes += size
        result = {
            "root": str(root), "index_entries_before": len(index),
            "objects_before": len(objects), "manifest_refs": len(refs),
            "keep_per_source": keep_per_source, "drop_index_entries": len(drop_index_ids),
            "drop_missing_index_entries": len(missing_unreferenced),
            "delete_object_files": len(delete_paths),
            "delete_gb_estimate": round(total_delete_bytes / (1024 ** 3), 3),
            "unindexed_files_eligible": len(drop_unindexed_paths),
            "dry_run": not apply,
        }
        if not apply:
            return result
        retained_index = {key: value for key, value in index.items() if key in keep and key not in missing_unreferenced}
        tmp = index_path.with_name(f"{index_path.name}.{os.getpid()}.gc.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(retained_index, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, index_path)
        finally:
            tmp.unlink(missing_ok=True)
        deleted = 0
        errors = 0
        for path in delete_paths:
            try:
                path.unlink(missing_ok=True)
                deleted += 1
            except OSError:
                errors += 1
        result.update({"index_entries_after": len(retained_index), "files_deleted": deleted,
                       "delete_errors": errors, "dry_run": False})
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True, help="Artifact store root; repeat for multiple stores")
    parser.add_argument("--manifest-root", action="append", default=[], help="Root(s) to scan for artifact_manifest.json")
    parser.add_argument("--keep-per-source", type=int, default=20)
    parser.add_argument("--unindexed-grace-hours", type=float, default=24.0)
    parser.add_argument("--apply", action="store_true", help="Actually update indexes and delete unreachable objects")
    parser.add_argument("--backup-dir", default=None, help="Directory for index backups (recommended with --apply)")
    args = parser.parse_args()
    roots = [Path(p).resolve() for p in args.root]
    manifest_roots = [Path(p).resolve() for p in args.manifest_root]
    refs = manifest_references(manifest_roots)
    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else None
    print(json.dumps({"manifest_reference_count": len(refs), "results": [
        prune_store(root, refs, max(1, args.keep_per_source), args.unindexed_grace_hours,
                    args.apply, backup_dir) for root in roots
    ]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
