from pathlib import Path

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
        (b"\x00\x01\x02\xff" * 4096, "application/octet-stream"),
        (b"\x89PNG\r\n" + b"\x00" * 8192, "image/png"),
        (b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8192, "video/mp4"),
    ],
)
def test_binary_round_trip_without_loss(tmp_path: Path, payload: bytes, media_type: str):
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
