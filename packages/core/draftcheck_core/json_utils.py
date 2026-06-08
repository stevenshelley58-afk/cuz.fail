from __future__ import annotations

import json
from hashlib import sha256 as _sha256
from typing import Any, TypeVar

T = TypeVar("T")


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def from_json(value: str | None, fallback: T) -> T:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def hash_text(value: str) -> str:
    return _sha256(value.encode("utf-8")).hexdigest()


def hash_bytes(value: bytes) -> str:
    return _sha256(value).hexdigest()


def normalize_text(value: str) -> str:
    return "\n".join(line.strip() for line in value.replace("\r\n", "\n").splitlines()).strip()


def word_limited_quote(value: str, limit: int = 80) -> str:
    words = value.split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit])
