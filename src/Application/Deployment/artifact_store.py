"""Adaptive, lossless, content-addressed artifact storage for YarTrader.

The store accepts arbitrary bytes (text, JSON, images, audio, video, market
data, etc.). It never performs lossy transcoding. Compressors are selected
adaptively: zstd when available, otherwise gzip; incompressible data is kept
raw. Every object is addressed by SHA-256 of the original bytes and verified
again on read.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import struct
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional


MAGIC = b"YARZ"
VERSION = 1
_HEADER = struct.Struct(">4sBBQQ32s")
_CODEC_RAW = 0
_CODEC_ZSTD = 1
_CODEC_GZIP = 2


_INDEX_LOCK_GUARD = threading.RLock()
_INDEX_LOCKS: dict[str, threading.RLock] = {}


@contextmanager
def _index_file_lock(index: Path):
    key = str(index.resolve())
    with _INDEX_LOCK_GUARD:
        thread_lock = _INDEX_LOCKS.setdefault(key, threading.RLock())
    with thread_lock:
        lock_path = index.with_suffix(index.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a+b") as lock_handle:
            if os.name == "nt":
                import msvcrt
                lock_handle.seek(0)
                lock_handle.write(b"\\0")
                lock_handle.flush()
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    import msvcrt
                    lock_handle.seek(0)
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _zstd_module():
    try:
        from compression import zstd  # Python 3.14+
        return zstd
    except Exception:
        return None


def _compress(data: bytes) -> tuple[int, bytes]:
    zstd = _zstd_module()
    if zstd is not None:
        try:
            packed = zstd.compress(data, level=3)
            if len(packed) < len(data):
                return _CODEC_ZSTD, packed
        except Exception:
            pass
    packed = gzip.compress(data, compresslevel=6, mtime=0)
    if len(packed) < len(data):
        return _CODEC_GZIP, packed
    return _CODEC_RAW, data


def _decompress(codec: int, data: bytes, expected_size: int) -> bytes:
    if codec == _CODEC_RAW:
        result = data
    elif codec == _CODEC_ZSTD:
        zstd = _zstd_module()
        if zstd is None:
            raise RuntimeError("zstd artifact requires Python compression.zstd")
        try:
            result = zstd.decompress(data)
        except Exception as exc:
            raise ValueError("Artifact decompression failed") from exc
    elif codec == _CODEC_GZIP:
        try:
            result = gzip.decompress(data)
        except (OSError, EOFError) as exc:
            raise ValueError("Artifact decompression failed") from exc
    else:
        raise ValueError(f"Unknown YarTrader artifact codec: {codec}")
    if len(result) != expected_size:
        raise ValueError("Artifact size verification failed")
    return result


class YarTraderArtifactStore:
    """Content-addressed, adaptive, lossless storage for arbitrary bytes."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.index = self.root / "index.json"
        self.objects.mkdir(parents=True, exist_ok=True)

    def _object_path(self, digest: str) -> Path:
        return self.objects / digest[:2] / f"{digest}.yarz"

    def put(
        self,
        data: bytes,
        *,
        media_type: str = "application/octet-stream",
        filename: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        target = self._object_path(digest)
        target.parent.mkdir(parents=True, exist_ok=True)

        codec, payload = _compress(data)
        if not target.exists():
            tmp = target.with_suffix(".tmp")
            header = _HEADER.pack(
                MAGIC, VERSION, codec, len(data), len(payload), bytes.fromhex(digest)
            )
            with open(tmp, "wb") as handle:
                handle.write(header)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)

        record = {
            "id": digest,
            "format": "YARZ1",
            "codec": {0: "raw", 1: "zstd", 2: "gzip"}[codec],
            "original_size": len(data),
            "stored_size": target.stat().st_size,
            "media_type": media_type,
            "filename": filename,
            "metadata": metadata or {},
        }
        self._write_index_entry(record)
        return record

    def get(self, artifact_id: str) -> bytes:
        target = self._object_path(artifact_id)
        with open(target, "rb") as handle:
            header = handle.read(_HEADER.size)
            magic, version, codec, original_size, payload_size, digest = _HEADER.unpack(header)
            if magic != MAGIC or version != VERSION:
                raise ValueError("Invalid YarTrader artifact header")
            if digest.hex() != artifact_id:
                raise ValueError("Artifact identity verification failed")
            payload = handle.read(payload_size)
            if len(payload) != payload_size:
                raise ValueError("Artifact payload is truncated")
        result = _decompress(codec, payload, original_size)
        if hashlib.sha256(result).digest() != digest:
            raise ValueError("Artifact checksum verification failed")
        return result

    def _write_index_entry(self, record: dict[str, Any]) -> None:
        with _index_file_lock(self.index):
            entries: dict[str, Any] = {}
            if self.index.exists():
                try:
                    entries = json.loads(self.index.read_text(encoding="utf-8"))
                except OSError as exc:
                    raise RuntimeError("Artifact index could not be read safely") from exc
                except json.JSONDecodeError as exc:
                    raise RuntimeError("Artifact index is corrupted; refusing to overwrite it") from exc
            entries[record["id"]] = record
            tmp = self.index.with_suffix(self.index.suffix + ".tmp")
            tmp.write_text(
                json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(tmp, self.index)
