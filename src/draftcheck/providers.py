"""Chat and LLM providers for V3.

Mirrors the provider logic from the legacy packages/core, using the V3 Settings.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol, Sequence, TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from draftcheck.config import Settings, get_settings


OPENAI_DEFAULT_CHAT_MODEL = "gpt-4o"
OPENROUTER_DEFAULT_CHAT_MODEL = "openai/gpt-4o"
MINIMAX_DEFAULT_CHAT_MODEL = "MiniMax-M3"
MINIMAX_DEFAULT_BASE_URL = "https://api.minimax.chat/v1"


class ChatMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class ChatProvider(Protocol):
    name: str
    model: str
    is_live: bool

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Single-turn wrapper. Default impl routes to complete_chat."""
        ...

    def complete_chat(self, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        """Multi-turn chat. Default impl falls back to complete() with the last user msg."""
        ...


class MockChatProvider:
    name = "mock"
    model = "mock-chat-v1"
    is_live = False

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "The live assistant model is not configured in this environment."

    def complete_chat(self, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        return self.complete(system_prompt, _last_user_message(messages))


def _last_user_message(messages: Sequence[ChatMessage]) -> str:
    """Pull the most recent user-role message; used as the default single-turn fallback."""
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    # If no user message, concatenate everything as a single user turn (last resort).
    return "\n".join(str(message.get("content", "")) for message in messages)


def _normalise_messages(
    system_prompt: str,
    messages: Sequence[ChatMessage],
) -> list[dict[str, str]]:
    """Coalesce any system-role messages into a single leading system turn."""
    system_parts: list[str] = [system_prompt] if system_prompt else []
    out: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", ""))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in {"user", "assistant"}:
            out.append({"role": role, "content": content})
    if system_parts:
        joined = "\n\n".join(part for part in system_parts if part)
        out.insert(0, {"role": "system", "content": joined})
    return out


@dataclass
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
        return self.complete_chat(system_prompt, [{"role": "user", "content": user_prompt}])

    def complete_chat(self, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        if not self.api_key:
            raise RuntimeError(f"API key is required when LLM_PROVIDER={self.name}.")
        normalised = _normalise_messages(system_prompt, messages)
        if not any(msg["role"] == "user" for msg in normalised):
            raise RuntimeError(f"{self.error_label} chat request requires at least one user message.")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": normalised,
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


ANTHROPIC_DEFAULT_CHAT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class AnthropicChatProvider:
    api_key: str
    model: str = ANTHROPIC_DEFAULT_CHAT_MODEL
    timeout_seconds: int = 30
    max_output_tokens: int = 700
    name: str = "anthropic"
    is_live: bool = True

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.complete_chat(system_prompt, [{"role": "user", "content": user_prompt}])

    def complete_chat(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("API key is required when LLM_PROVIDER=anthropic.")
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": self.max_output_tokens,
                "system": system_prompt,
                "messages": messages,
            }
        ).encode("utf-8")
        req = Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        delays = [1.0, 2.0, 4.0]
        last_exc: Exception | None = None
        for delay in [0.0, *delays]:
            if delay:
                time.sleep(delay)
            try:
                with urlopen(req, timeout=self.timeout_seconds) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content_blocks = data.get("content", [])
                text = "".join(
                    block.get("text", "")
                    for block in content_blocks
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                if not text.strip():
                    raise RuntimeError("Anthropic chat response contained no text content.")
                return text.strip()
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_exc = RuntimeError(
                    f"Anthropic chat request failed with HTTP {exc.code}: {_clip_error(detail)}"
                )
            except (OSError, URLError) as exc:
                last_exc = RuntimeError(f"Anthropic chat request failed: {exc}")
        raise RuntimeError(f"Anthropic API failed after retries: {last_exc}") from last_exc


def get_chat_provider(settings: Settings | None = None) -> ChatProvider:
    active_settings = settings or get_settings()
    provider = (active_settings.llm_provider or "mock").strip().lower()
    if provider == "anthropic" and active_settings.anthropic_api_key:
        model = active_settings.llm_model.strip() or ANTHROPIC_DEFAULT_CHAT_MODEL
        return AnthropicChatProvider(
            api_key=active_settings.anthropic_api_key,
            model=model,
            timeout_seconds=active_settings.llm_timeout_seconds,
            max_output_tokens=active_settings.llm_max_output_tokens,
        )
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
    if provider == "minimax" and active_settings.minimax_api_key:
        model = active_settings.llm_model.strip() or MINIMAX_DEFAULT_CHAT_MODEL
        return OpenAIChatProvider(
            api_key=active_settings.minimax_api_key,
            model=model,
            base_url=active_settings.minimax_base_url,
            timeout_seconds=active_settings.llm_timeout_seconds,
            max_output_tokens=active_settings.llm_max_output_tokens,
            name="minimax",
            error_label="MiniMax",
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

_KNOWN_PROVIDERS = re.compile(r"^(mock|openai|openai-compatible|openrouter|minimax|anthropic)$")


# Alias used by substrate.build_model_adapter and callers that only need a provider.
build_chat_provider = get_chat_provider
