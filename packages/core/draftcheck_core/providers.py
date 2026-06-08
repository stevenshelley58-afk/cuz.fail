from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from draftcheck_core.config import Settings, get_settings

MOCK_EMBEDDING_DIMENSIONS = 16
MOCK_EMBEDDING_MODEL = "mock-hash-v1"
OPENAI_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

_EMBEDDING_SYNONYMS = {
    "bulk": "dominance",
    "bulky": "dominance",
    "car": "garage",
    "cars": "garage",
    "front": "street",
    "parking": "garage",
    "vehicle": "garage",
    "vehicles": "garage",
}


class LlmProvider(Protocol):
    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def rerank(self, query: str, candidates: list[str]) -> list[int]:
        ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class MockLlmProvider:
    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "answer": "Mock provider output. Human review required.",
            "prompt_excerpt": prompt[:200],
            "schema_keys": sorted(schema.keys()),
            "human_review_required": True,
        }

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_mock_embedding(text) for text in texts]

    def rerank(self, query: str, candidates: list[str]) -> list[int]:
        terms = {term.lower() for term in query.split()}
        scored = [
            (index, sum(1 for term in terms if term in candidate.lower()))
            for index, candidate in enumerate(candidates)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [index for index, _score in scored]


@dataclass(frozen=True)
class OpenAIEmbeddingProvider:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    dimensions: int = 0
    timeout_seconds: int = 30

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")
        if not texts:
            return []

        vectors: list[list[float]] = []
        for batch in _batched(texts, 256):
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        body: dict[str, Any] = {
            "input": [_embedding_input_value(text) for text in texts],
            "model": self.model,
            "encoding_format": "float",
        }
        if self.dimensions > 0:
            body["dimensions"] = self.dimensions

        request = Request(
            f"{self.base_url.rstrip('/')}/embeddings",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI embeddings request failed with HTTP {exc.code}: {_clip_error(detail)}") from exc
        except (OSError, URLError) as exc:
            raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc

        data = payload.get("data")
        if not isinstance(data, list):
            raise RuntimeError("OpenAI embeddings response did not include a data list.")
        ordered = sorted(data, key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0)
        vectors: list[list[float]] = []
        for item in ordered:
            if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                raise RuntimeError("OpenAI embeddings response included an invalid embedding item.")
            try:
                vectors.append([float(value) for value in item["embedding"]])
            except (TypeError, ValueError) as exc:
                raise RuntimeError("OpenAI embeddings response included a non-numeric embedding value.") from exc
        if len(vectors) != len(texts):
            raise RuntimeError("OpenAI embeddings response count did not match the request count.")
        return vectors


def get_llm_provider() -> LlmProvider:
    return MockLlmProvider()


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    active_settings = settings or get_settings()
    provider = embedding_provider_name(active_settings)
    if provider in {"mock", "mock-hash"}:
        return MockLlmProvider()
    if provider in {"openai", "openai-compatible"}:
        return OpenAIEmbeddingProvider(
            api_key=active_settings.openai_api_key,
            model=embedding_model_name(active_settings),
            base_url=active_settings.openai_base_url,
            dimensions=active_settings.embedding_dimensions,
            timeout_seconds=active_settings.embedding_timeout_seconds,
        )
    raise RuntimeError(f"Unsupported EMBEDDING_PROVIDER={active_settings.embedding_provider!r}.")


def embedding_provider_name(settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    return (active_settings.embedding_provider or "mock").strip().lower()


def embedding_model_name(settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    configured = active_settings.embedding_model.strip()
    if configured:
        return configured
    if embedding_provider_name(active_settings) in {"openai", "openai-compatible"}:
        return OPENAI_DEFAULT_EMBEDDING_MODEL
    return MOCK_EMBEDDING_MODEL


def _mock_embedding(text: str) -> list[float]:
    vector = [0.0] * MOCK_EMBEDDING_DIMENSIONS
    for token in _embedding_tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % MOCK_EMBEDDING_DIMENSIONS
        vector[index] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def _embedding_tokens(text: str) -> list[str]:
    tokens = []
    for raw_token in re.findall(r"[a-z0-9]+", text.lower()):
        token = _EMBEDDING_SYNONYMS.get(raw_token, raw_token)
        if len(token) >= 3:
            tokens.append(token)
    return tokens


def _batched(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _embedding_input_value(text: str) -> str:
    normalized = text.strip()
    return normalized if normalized else "missing text"


def _clip_error(value: str, limit: int = 500) -> str:
    return value if len(value) <= limit else f"{value[:limit]}..."
