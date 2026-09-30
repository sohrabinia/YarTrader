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
