from pathlib import Path

from src.Application.Deployment.artifact_store import YarTraderArtifactStore
from src.Research.Brain.memory import MarketMemorySystem


def test_brain_memory_persists_layers_to_universal_artifact_store(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    artifact_root = tmp_path / "artifacts"
    store = YarTraderArtifactStore(artifact_root)
    memory = MarketMemorySystem(
        storage_dir=str(legacy_dir),
        artifact_store=store,
    )

    memory._save_layer("events")

    manifest = memory.get_artifact_manifest()
    assert "events" in manifest
    artifact_id = manifest["events"]
    assert store.get(artifact_id) == b"[]"
    assert (legacy_dir / "events_memory.json").exists()


def test_artifact_snapshots_are_throttled_but_can_be_flushed(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("YARTRADER_ARTIFACT_SNAPSHOT_EVERY", "3")
    legacy_dir = tmp_path / "legacy"
    store = YarTraderArtifactStore(tmp_path / "artifacts")
    memory = MarketMemorySystem(storage_dir=str(legacy_dir), artifact_store=store)
    original_put = store.put
    writes = []

    def counted_put(*args, **kwargs):
        writes.append(kwargs.get("filename"))
        return original_put(*args, **kwargs)

    monkeypatch.setattr(store, "put", counted_put)
    for _ in range(4):
        memory._save_layer("events")
    assert writes == ["events_memory.json", "events_memory.json"]
    assert (legacy_dir / "events_memory.json").exists()

    memory.flush_artifact_snapshots()
    assert writes.count("events_memory.json") == 3
    assert set(memory.get_artifact_manifest()) == {"events", "experiences", "patterns", "concepts"}


def test_custom_memory_directory_uses_isolated_artifact_store(tmp_path: Path):
    legacy_dir = tmp_path / "isolated-memory"
    memory = MarketMemorySystem(storage_dir=str(legacy_dir))
    assert Path(memory._artifact_store.root) == legacy_dir / "artifacts"
