import json
from typing import Any

from draftcheck.config import Settings
from draftcheck.providers import OpenAIResponsesProvider, get_chat_provider


class _FakeOpenAIResponse:
    def __enter__(self) -> "_FakeOpenAIResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Useful answer."}],
                    }
                ]
            }
        ).encode("utf-8")


def test_openai_responses_provider_uses_responses_api(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout: int):
        calls.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return _FakeOpenAIResponse()

    monkeypatch.setattr("draftcheck.providers.urlopen", fake_urlopen)
    provider = OpenAIResponsesProvider(
        api_key="sk-test",
        model="gpt-5.5",
        timeout_seconds=12,
        max_output_tokens=500,
    )

    answer = provider.complete_chat("System prompt", [{"role": "user", "content": "Question"}])

    assert answer == "Useful answer."
    assert calls[0]["url"] == "https://api.openai.com/v1/responses"
    assert calls[0]["timeout"] == 12
    assert calls[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert calls[0]["body"] == {
        "model": "gpt-5.5",
        "instructions": "System prompt",
        "input": [{"role": "user", "content": "Question"}],
        "max_output_tokens": 500,
        "reasoning": {"effort": "medium"},
        "text": {"verbosity": "medium"},
    }


def test_openai_provider_defaults_to_latest_responses_model() -> None:
    provider = get_chat_provider(Settings(llm_provider="openai", openai_api_key="sk-test"))

    assert isinstance(provider, OpenAIResponsesProvider)
    assert provider.model == "gpt-5.5"
