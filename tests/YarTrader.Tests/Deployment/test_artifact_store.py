from pathlib import Path
import hashlib

import pytest

from src.Application.Deployment.artifact_store import YarTraderArtifactStore


def test_round_trip_text_and_dedup(tmp_path: Path):
    store = YarTraderArtifactStore(tmp_path)
    payload = ("YarTrader Brain memory " * 1000).encode("utf-8")
    first = store.put(payload, media_type="text/plain", filename="memory.txt")
    second = store.put(payload, media_type="text/plain", filename="memory-copy.txt")
    assert first["id"] == second["id"]
    assert store.get(first["id"]) == payload
    assert first["stored_size"] < first["original_size"]


@pytest.mark.parametrize(
    "payload,media_type",
    [
        pytest.param(
            b"\x00\x01\x02\xff" * 4096,
            "application/octet-stream",
            id="binary",
        ),
        pytest.param(
            b"\x89PNG\r\n" + b"\x00" * 8192,
            "image/png",
            id="png",
        ),
        pytest.param(
            b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8192,
            "video/mp4",
            id="mp4",
        ),
    ],
)
def test_binary_round_trip_without_loss(
    tmp_path: Path, payload: bytes, media_type: str
):
    store = YarTraderArtifactStore(tmp_path)
    record = store.put(payload, media_type=media_type)
    assert store.get(record["id"]) == payload
    assert record["original_size"] == len(payload)


def test_corruption_is_detected(tmp_path: Path):
    store = YarTraderArtifactStore(tmp_path)
    record = store.put(b"important Brain evidence" * 100)
    path = store._object_path(record["id"])
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 0xFF
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        store.get(record["id"])


def test_concurrent_puts_preserve_every_index_entry(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor
    import json

    store = YarTraderArtifactStore(tmp_path)
    payloads = [f"artifact-{i}-".encode() + bytes([i]) * 1024 for i in range(32)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        records = list(pool.map(lambda payload: store.put(payload, filename="parallel.bin"), payloads))

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(index) == len(payloads)
    assert set(index) == {record["id"] for record in records}
    for record, payload in zip(records, payloads):
        assert store.get(record["id"]) == payload


def _process_put_batch(args):
    root, start, count = args
    store = YarTraderArtifactStore(root)
    return [store.put(f"process-artifact-{i}".encode(), filename="process.bin")["id"]
            for i in range(start, start + count)]


def test_cross_process_puts_do_not_lose_index_entries(tmp_path: Path):
    from concurrent.futures import ProcessPoolExecutor
    import json

    batches = [(str(tmp_path), start, 8) for start in (0, 8, 16, 24)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        ids = [item for batch in pool.map(_process_put_batch, batches) for item in batch]

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(index) == 32
    assert set(index) == set(ids)
    store = YarTraderArtifactStore(tmp_path)
    for artifact_id in ids:
        assert store.get(artifact_id) == next(
            f"process-artifact-{i}".encode() for i in range(32)
            if hashlib.sha256(f"process-artifact-{i}".encode()).hexdigest() == artifact_id
        )
