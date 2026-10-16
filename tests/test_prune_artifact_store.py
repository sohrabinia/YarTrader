import json
import os
from pathlib import Path

from scripts.prune_artifact_store import manifest_references, prune_store
from src.Application.Deployment.artifact_store import YarTraderArtifactStore


def test_artifact_pruner_keeps_manifest_refs_and_recent_history(tmp_path: Path):
    store_root = tmp_path / "Data" / "artifacts"
    memory_dir = tmp_path / "runtime" / "brain_memory"
    memory_dir.mkdir(parents=True)
    store = YarTraderArtifactStore(store_root)
    records = []
    for index in range(5):
        record = store.put(
            f"snapshot-{index}".encode(), filename="experiences_memory.json",
            metadata={"producer": "MarketMemorySystem", "layer": "experiences",
                      "legacy_path": str(memory_dir / "experiences_memory.json")},
        )
        records.append(record)
        os.utime(store._object_path(record["id"]), (1000 + index, 1000 + index))
    (memory_dir / "artifact_manifest.json").write_text(
        json.dumps({"experiences": records[0]["id"]}), encoding="utf-8"
    )
    refs = manifest_references([tmp_path / "runtime"])
    assert records[0]["id"] in refs

    dry_run = prune_store(store_root, refs, keep_per_source=2, grace_hours=0,
                          apply=False, backup_dir=None)
    assert dry_run["delete_object_files"] == 2
    assert dry_run["dry_run"] is True
    assert len(list((store_root / "objects").glob("*/*.yarz"))) == 5

    backup = tmp_path / "backup"
    applied = prune_store(store_root, refs, keep_per_source=2, grace_hours=0,
                          apply=True, backup_dir=backup)
    assert applied["files_deleted"] == 2
    index = json.loads((store_root / "index.json").read_text(encoding="utf-8"))
    assert records[0]["id"] in index
    assert records[3]["id"] in index and records[4]["id"] in index
    assert records[1]["id"] not in index and records[2]["id"] not in index
    assert list(backup.glob("*_artifact_index.json"))
