"""Chat and LLM providers for V3.

Mirrors the provider logic from the legacy packages/core, using the V3 Settings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from draftcheck.config import Settings, get_settings


OPENAI_DEFAULT_CHAT_MODEL = "gpt-5.5"
OPENROUTER_DEFAULT_CHAT_MODEL = "openai/gpt-5.5"


class ChatProvider(Protocol):
    name: str
    model: str
    is_live: bool

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class MockChatProvider:
    name = "mock"
    model = "mock-chat-v1"
    is_live = False

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "The live assistant model is not configured in this environment."


@dataclass(frozen=True)
class OpenAIChatProvider:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 30
    max_output_tokens: int = 700
    name: str = "openai"
    error_label: str = "OpenAI"
    extra_headers: dict[str, str] | None = None
    is_live: bool = True

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(f"API key is required when LLM_PROVIDER={self.name}.")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": self.max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **(self.extra_headers or {}),
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"{self.error_label} chat request failed with HTTP {exc.code}: {_clip_error(detail)}"
            ) from exc
        except (OSError, URLError) as exc:
            raise RuntimeError(f"{self.error_label} chat request failed: {exc}") from exc

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"{self.error_label} chat response did not include any choices.")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{self.error_label} chat response contained no text content.")
        return content.strip()


def get_chat_provider(settings: Settings | None = None) -> ChatProvider:
    active_settings = settings or get_settings()
    provider = (active_settings.llm_provider or "mock").strip().lower()
    if provider in {"openai", "openai-compatible"} and active_settings.openai_api_key:
        model = active_settings.llm_model.strip() or OPENAI_DEFAULT_CHAT_MODEL
        return OpenAIChatProvider(
            api_key=active_settings.openai_api_key,
            model=model,
            base_url=active_settings.openai_base_url,
            timeout_seconds=active_settings.llm_timeout_seconds,
            max_output_tokens=active_settings.llm_max_output_tokens,
        )
    if provider == "openrouter" and active_settings.openrouter_api_key:
        model = active_settings.llm_model.strip()
        if not model or model == OPENAI_DEFAULT_CHAT_MODEL:
            model = OPENROUTER_DEFAULT_CHAT_MODEL
        extra_headers: dict[str, str] = {}
        if active_settings.openrouter_site_url.strip():
            extra_headers["HTTP-Referer"] = active_settings.openrouter_site_url.strip()
        if active_settings.openrouter_app_name.strip():
            extra_headers["X-Title"] = active_settings.openrouter_app_name.strip()
        return OpenAIChatProvider(
            api_key=active_settings.openrouter_api_key,
            model=model,
            base_url=active_settings.openrouter_base_url,
            timeout_seconds=active_settings.llm_timeout_seconds,
            max_output_tokens=active_settings.llm_max_output_tokens,
            name="openrouter",
            error_label="OpenRouter",
            extra_headers=extra_headers or None,
        )
    return MockChatProvider()


def _clip_error(value: str, limit: int = 500) -> str:
    return value if len(value) <= limit else f"{value[:limit]}..."


# Keep a re export so external tooling that checks the module can find the regex
_EMBEDDING_SYNONYMS = {
    "bulk": "dominance",
    "car": "garage",
    "cars": "garage",
    "front": "street",
    "parking": "garage",
    "vehicle": "garage",
    "vehicles": "garage",
}

_KNOWN_PROVIDERS = re.compile(r"^(mock|openai|openai-compatible|openrouter)$")
