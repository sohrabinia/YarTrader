# Universal Artifact Storage

YarTrader now has a single adaptive storage primitive for arbitrary bytes:
text, JSON, images, audio, video, market data, reports, and Brain artifacts.

## Guarantees

- **Lossless only:** the original bytes are always recoverable; no lossy media transcoding is performed.
- **Adaptive compression:** uses Python 3.14's \`compression.zstd\` when available; otherwise falls back to gzip. If compression would increase size, the payload is stored raw.
- **Content addressing:** SHA-256 of the original bytes is the immutable artifact ID. Identical content is stored once.
- **Integrity:** the container stores original size and SHA-256 and verifies both before returning data.
- **Atomic writes:** temporary files are atomically replaced into the object store.
- **Metadata:** media type, filename, and caller metadata are retained separately from the payload.
- **Centralized location:** artifacts live below \`YarTraderStorageManager\` -> \`Data/artifacts\`.

## Runtime contract

Existing runtime data is not silently rewritten in-place. New producers should use:

\`YarTraderStorageManager.get_manager().get_artifact_store().put(...)\`

and retrieve by artifact ID with \`.get(...)\`.

This avoids corrupting existing Brain memory while the storage layer is rolled into producers in controlled steps.
