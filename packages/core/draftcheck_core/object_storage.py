from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from draftcheck_core.config import get_settings
from draftcheck_core.json_utils import hash_text


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    content_sha256: str
    byte_size: int


class LocalObjectStorage:
    """Small S3/MinIO-shaped local storage adapter for tests and dev."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or get_settings().object_storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredObject(
            object_key=str(path),
            content_sha256=hash_text(content.decode("latin1")),
            byte_size=len(content),
        )

    def get_bytes(self, key: str) -> bytes:
        return Path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return Path(key).exists()
