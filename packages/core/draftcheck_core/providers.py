from __future__ import annotations

from typing import Any, Protocol


class LlmProvider(Protocol):
    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def rerank(self, query: str, candidates: list[str]) -> list[int]:
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
        return [[float(len(text) % 17), float(len(text.split()))] for text in texts]

    def rerank(self, query: str, candidates: list[str]) -> list[int]:
        terms = {term.lower() for term in query.split()}
        scored = [
            (index, sum(1 for term in terms if term in candidate.lower()))
            for index, candidate in enumerate(candidates)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [index for index, _score in scored]


def get_llm_provider() -> LlmProvider:
    return MockLlmProvider()
