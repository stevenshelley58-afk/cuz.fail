"""Governed model substrate for V3.

Supports a local deterministic adapter (no network calls) and a real
Anthropic adapter that calls claude-sonnet-4-6.  Falls back to the local
adapter when ANTHROPIC_API_KEY is absent.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
from threading import RLock
from typing import Any, Literal, Protocol, runtime_checkable
from uuid import uuid4

try:
    import anthropic as _anthropic_sdk
    _ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    _anthropic_sdk = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

try:
    import openai as _openai_sdk
except ImportError:  # pragma: no cover
    _openai_sdk = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ModelCallStatus = Literal["succeeded", "refused"]
AdapterMode = Literal["disabled", "local"]

TOKEN_RE = re.compile(r"\S+")

# claude-sonnet-4-6 pricing (USD per token -> converted to cents)
_SONNET_INPUT_COST_CENTS_PER_TOKEN = 0.0003   # $3 / 1M tokens
_SONNET_OUTPUT_COST_CENTS_PER_TOKEN = 0.0015  # $15 / 1M tokens


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def prompt_hash(prompt: str) -> str:
    return sha256(prompt.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    return max(1, len(TOKEN_RE.findall(text)))


@dataclass(frozen=True)
class ModelRequest:
    job_id: str
    job_type: str
    skill_version_id: str
    prompt: str
    max_output_tokens: int = 256
    input_artifact_ids: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    json_mode: bool = False

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id is required")
        if not self.job_type.strip():
            raise ValueError("job_type is required")
        if not self.skill_version_id.strip():
            raise ValueError("skill_version_id is required for traced model calls")
        if not self.prompt.strip():
            raise ValueError("prompt is required")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")


@dataclass(frozen=True)
class ModelResponse:
    status: ModelCallStatus
    text: str
    trace_id: str
    input_tokens: int
    output_tokens: int
    cost_cents: int
    refusal_reason: str | None = None


@dataclass(frozen=True)
class JobTrace:
    id: str
    job_id: str
    job_type: str
    skill_version_id: str
    model_provider: str
    model: str
    prompt_hash: str
    input_artifact_ids: tuple[str, ...]
    output_artifact_ids: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_cents: int
    status: ModelCallStatus
    refusal_reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class SpendCaps:
    per_job_token_cap: int = 4096
    daily_token_cap: int = 100_000
    daily_cost_cap_cents: int = 1_000

    def __post_init__(self) -> None:
        if self.per_job_token_cap <= 0:
            raise ValueError("per_job_token_cap must be positive")
        if self.daily_token_cap <= 0:
            raise ValueError("daily_token_cap must be positive")
        if self.daily_cost_cap_cents < 0:
            raise ValueError("daily_cost_cap_cents cannot be negative")

    @classmethod
    def from_env(cls) -> SpendCaps:
        return cls(
            per_job_token_cap=int(os.getenv("DRAFTCHECK_LLM_PER_JOB_TOKEN_CAP", "4096")),
            daily_token_cap=int(os.getenv("DRAFTCHECK_LLM_DAILY_TOKEN_CAP", "100000")),
            daily_cost_cap_cents=int(os.getenv("DRAFTCHECK_LLM_DAILY_COST_CAP_CENTS", "1000")),
        )


@dataclass
class CircuitBreaker:
    is_open: bool = False
    reason: str | None = None
    opened_at: datetime | None = None

    def open(self, reason: str, *, now: datetime | None = None) -> None:
        self.is_open = True
        self.reason = reason
        self.opened_at = now or utc_now()

    def close(self) -> None:
        self.is_open = False
        self.reason = None
        self.opened_at = None


# ---------------------------------------------------------------------------
# Embedding dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmbeddingRequest:
    content: str
    model: str = "text-embedding-3-small"


@dataclass(frozen=True)
class EmbeddingResponse:
    embedding: list[float]
    model: str
    input_tokens: int


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

class ModelAdapter(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse:
        """Run a governed model call."""


@runtime_checkable
class JobTraceStore(Protocol):
    def append(self, trace: JobTrace) -> None: ...
    def seed_daily_counters(self, today: date) -> tuple[int, int]: ...


# ---------------------------------------------------------------------------
# In-memory trace store
# ---------------------------------------------------------------------------

class InMemoryJobTraceStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._traces: list[JobTrace] = []

    def append(self, trace: JobTrace) -> None:
        with self._lock:
            self._traces.append(trace)

    def list_traces(self) -> tuple[JobTrace, ...]:
        with self._lock:
            return tuple(self._traces)

    def seed_daily_counters(self, today: date) -> tuple[int, int]:
        # In-memory store has no persistence; always starts fresh.
        return 0, 0


# ---------------------------------------------------------------------------
# Local deterministic adapter (zero cost, no network)
# ---------------------------------------------------------------------------

class LocalDeterministicModelAdapter:
    """A disabled/local deterministic adapter with spend controls and traces."""

    provider = "local"
    model = "deterministic-substrate-v0"
    cost_per_1000_tokens_cents = 0

    def __init__(
        self,
        *,
        mode: AdapterMode = "disabled",
        trace_store: JobTraceStore | None = None,
        spend_caps: SpendCaps | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.mode = mode
        self.trace_store = trace_store or InMemoryJobTraceStore()
        self.spend_caps = spend_caps or SpendCaps.from_env()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._lock = RLock()
        self._ledger_day: date | None = None
        self._daily_tokens = 0
        self._daily_cost_cents = 0

    def complete(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        input_tokens = estimate_tokens(request.prompt)
        projected_tokens = input_tokens + request.max_output_tokens
        projected_cost_cents = self._cost_cents(projected_tokens)

        with self._lock:
            self._reset_ledger_if_needed()
            refusal_reason = self._refusal_reason(projected_tokens, projected_cost_cents)
            if refusal_reason:
                if refusal_reason.startswith("daily_"):
                    self.circuit_breaker.open(refusal_reason)
                return self._refused_response(
                    request,
                    input_tokens=input_tokens,
                    refusal_reason=refusal_reason,
                )

            text = self._local_text(request)
            output_tokens = min(request.max_output_tokens, estimate_tokens(text))
            total_tokens = input_tokens + output_tokens
            cost_cents = self._cost_cents(total_tokens)
            self._daily_tokens += total_tokens
            self._daily_cost_cents += cost_cents
            trace = self._trace(
                request,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_cents=cost_cents,
                status="succeeded",
                refusal_reason=None,
            )
            self.trace_store.append(trace)
            return ModelResponse(
                status="succeeded",
                text=text,
                trace_id=trace.id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_cents=cost_cents,
            )

    def _reset_ledger_if_needed(self) -> None:
        today = utc_now().date()
        if self._ledger_day != today:
            if self._ledger_day is None:
                # First call after (re)start — seed from durable store to survive restarts.
                self._daily_tokens, self._daily_cost_cents = (
                    self.trace_store.seed_daily_counters(today)
                )
            else:
                # Day rollover — genuinely new day, start from zero.
                self._daily_tokens = 0
                self._daily_cost_cents = 0
            self._ledger_day = today

    def _refusal_reason(self, projected_tokens: int, projected_cost_cents: int) -> str | None:
        if self.mode == "disabled":
            return "model_adapter_disabled"
        if self.circuit_breaker.is_open:
            return "circuit_breaker_open"
        if projected_tokens > self.spend_caps.per_job_token_cap:
            return "per_job_token_cap_exceeded"
        if self._daily_tokens + projected_tokens > self.spend_caps.daily_token_cap:
            return "daily_token_cap_exceeded"
        if self._daily_cost_cents + projected_cost_cents > self.spend_caps.daily_cost_cap_cents:
            return "daily_cost_cap_exceeded"
        return None

    def _refused_response(
        self,
        request: ModelRequest,
        *,
        input_tokens: int,
        refusal_reason: str,
    ) -> ModelResponse:
        trace = self._trace(
            request,
            input_tokens=input_tokens,
            output_tokens=0,
            cost_cents=0,
            status="refused",
            refusal_reason=refusal_reason,
        )
        self.trace_store.append(trace)
        return ModelResponse(
            status="refused",
            text="",
            trace_id=trace.id,
            input_tokens=input_tokens,
            output_tokens=0,
            cost_cents=0,
            refusal_reason=refusal_reason,
        )

    def _trace(
        self,
        request: ModelRequest,
        *,
        input_tokens: int,
        output_tokens: int,
        cost_cents: int,
        status: ModelCallStatus,
        refusal_reason: str | None,
    ) -> JobTrace:
        return JobTrace(
            id=f"trace_{uuid4().hex}",
            job_id=request.job_id,
            job_type=request.job_type,
            skill_version_id=request.skill_version_id,
            model_provider=self.provider,
            model=self.model,
            prompt_hash=prompt_hash(request.prompt),
            input_artifact_ids=request.input_artifact_ids,
            output_artifact_ids=(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=cost_cents,
            status=status,
            refusal_reason=refusal_reason,
            created_at=utc_now(),
        )

    def _local_text(self, request: ModelRequest) -> str:
        digest = prompt_hash(request.prompt)[:12]
        return (
            "Local deterministic draft generated from supplied, cited context "
            f"for job {request.job_id} ({digest})."
        )

    def _cost_cents(self, tokens: int) -> int:
        return (tokens * self.cost_per_1000_tokens_cents + 999) // 1000


# ---------------------------------------------------------------------------
# HTTP adapter (generic external provider)
# ---------------------------------------------------------------------------

class HttpModelAdapter:
    """Routes ModelRequest through a live chat provider with spend controls and traces."""

    cost_per_1000_tokens_cents = 0  # Updated to actual cost once provider reports usage

    def __init__(
        self,
        provider: "Any",  # ChatProvider protocol
        *,
        spend_caps: SpendCaps | None = None,
        trace_store: InMemoryJobTraceStore | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._provider = provider
        self._caps = spend_caps or SpendCaps.from_env()
        self._trace_store = trace_store or InMemoryJobTraceStore()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._lock = RLock()
        self._ledger_day: date | None = None
        self._daily_tokens = 0
        self._daily_cost_cents = 0

    def complete(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")

        input_tokens = estimate_tokens(request.prompt)
        projected_tokens = input_tokens + request.max_output_tokens
        projected_cost_cents = self._cost_cents(projected_tokens)

        with self._lock:
            self._reset_ledger_if_needed()
            refusal = self._refusal_reason(projected_tokens, projected_cost_cents)
            if refusal:
                if refusal.startswith("daily_"):
                    self._circuit_breaker.open(refusal)
                trace = self._make_trace(
                    request,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cost_cents=0,
                    status="refused",
                    refusal_reason=refusal,
                )
                self._trace_store.append(trace)
                return ModelResponse(
                    status="refused",
                    text="",
                    trace_id=trace.id,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cost_cents=0,
                    refusal_reason=refusal,
                )

        system_prompt = (
            "You are a planning regulation extraction assistant. Respond in JSON only."
        )
        try:
            text_out = self._provider.complete(system_prompt, request.prompt)  # type: ignore[union-attr]
        except Exception as exc:
            raise RuntimeError(f"LLM provider failed: {exc}") from exc

        output_tokens = estimate_tokens(text_out)
        total_tokens = input_tokens + output_tokens
        cost_cents = self._cost_cents(total_tokens)

        with self._lock:
            self._daily_tokens += total_tokens
            self._daily_cost_cents += cost_cents

        trace = self._make_trace(
            request,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=cost_cents,
            status="succeeded",
            refusal_reason=None,
        )
        self._trace_store.append(trace)
        return ModelResponse(
            status="succeeded",
            text=text_out,
            trace_id=trace.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=cost_cents,
        )

    def _reset_ledger_if_needed(self) -> None:
        today = utc_now().date()
        if self._ledger_day != today:
            self._ledger_day = today
            self._daily_tokens = 0
            self._daily_cost_cents = 0

    def _refusal_reason(self, projected_tokens: int, projected_cost_cents: int) -> str | None:
        if self._circuit_breaker.is_open:
            return "circuit_breaker_open"
        if projected_tokens > self._caps.per_job_token_cap:
            return "per_job_token_cap_exceeded"
        if self._daily_tokens + projected_tokens > self._caps.daily_token_cap:
            return "daily_token_cap_exceeded"
        if self._daily_cost_cents + projected_cost_cents > self._caps.daily_cost_cap_cents:
            return "daily_cost_cap_exceeded"
        return None

    def _make_trace(
        self,
        request: ModelRequest,
        *,
        input_tokens: int,
        output_tokens: int,
        cost_cents: int,
        status: ModelCallStatus,
        refusal_reason: str | None,
    ) -> JobTrace:
        provider_name = getattr(self._provider, "name", "unknown")
        model_name = getattr(self._provider, "model", "unknown")
        return JobTrace(
            id=f"trace_{uuid4().hex}",
            job_id=request.job_id,
            job_type=request.job_type,
            skill_version_id=request.skill_version_id,
            model_provider=provider_name,
            model=model_name,
            prompt_hash=prompt_hash(request.prompt),
            input_artifact_ids=request.input_artifact_ids,
            output_artifact_ids=(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=cost_cents,
            status=status,
            refusal_reason=refusal_reason,
            created_at=utc_now(),
        )

    def _cost_cents(self, tokens: int) -> int:
        return (tokens * self.cost_per_1000_tokens_cents + 999) // 1000


# ---------------------------------------------------------------------------
# Anthropic adapter (async, native SDK)
# ---------------------------------------------------------------------------

class AnthropicModelAdapter:
    """Calls Anthropic claude-sonnet-4-6 with governed spend caps and traces.

    Reads ANTHROPIC_API_KEY from the environment.
    """

    provider = "anthropic"

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        trace_store: InMemoryJobTraceStore | None = None,
        spend_caps: SpendCaps | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        db_session_factory: Any = None,
    ) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicModelAdapter. "
                "Install it with: pip install 'anthropic>=0.25'"
            )
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Use get_model_adapter() for automatic fallback."
            )
        self.model = model
        self._client = _anthropic_sdk.AsyncAnthropic(api_key=api_key)  # type: ignore[union-attr]
        self.trace_store = trace_store or InMemoryJobTraceStore()
        self.spend_caps = spend_caps or SpendCaps.from_env()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._db_session_factory = db_session_factory
        self._lock = RLock()
        self._ledger_day: date | None = None
        self._daily_tokens = 0
        self._daily_cost_cents = 0

    def _cost_cents(self, input_tokens: int, output_tokens: int) -> int:
        return int(
            input_tokens * _SONNET_INPUT_COST_CENTS_PER_TOKEN
            + output_tokens * _SONNET_OUTPUT_COST_CENTS_PER_TOKEN
        )

    def _reset_ledger_if_needed(self) -> None:
        today = utc_now().date()
        if self._ledger_day != today:
            self._ledger_day = today
            self._daily_tokens = 0
            self._daily_cost_cents = 0

    def _refusal_reason(self, projected_tokens: int, projected_cost_cents: int) -> str | None:
        if self.circuit_breaker.is_open:
            return "circuit_breaker_open"
        if projected_tokens > self.spend_caps.per_job_token_cap:
            return "per_job_token_cap_exceeded"
        if self._daily_tokens + projected_tokens > self.spend_caps.daily_token_cap:
            return "daily_token_cap_exceeded"
        if self._daily_cost_cents + projected_cost_cents > self.spend_caps.daily_cost_cap_cents:
            return "daily_cost_cap_exceeded"
        return None

    def _refused_response(
        self,
        request: ModelRequest,
        *,
        input_tokens: int,
        refusal_reason: str,
    ) -> ModelResponse:
        trace = self._build_trace(
            request,
            input_tokens=input_tokens,
            output_tokens=0,
            cost_cents=0,
            status="refused",
            refusal_reason=refusal_reason,
        )
        self.trace_store.append(trace)
        return ModelResponse(
            status="refused",
            text="",
            trace_id=trace.id,
            input_tokens=input_tokens,
            output_tokens=0,
            cost_cents=0,
            refusal_reason=refusal_reason,
        )

    def _build_trace(
        self,
        request: ModelRequest,
        *,
        input_tokens: int,
        output_tokens: int,
        cost_cents: int,
        status: ModelCallStatus,
        refusal_reason: str | None,
    ) -> JobTrace:
        return JobTrace(
            id=f"trace_{uuid4().hex}",
            job_id=request.job_id,
            job_type=request.job_type,
            skill_version_id=request.skill_version_id,
            model_provider=self.provider,
            model=self.model,
            prompt_hash=prompt_hash(request.prompt),
            input_artifact_ids=request.input_artifact_ids,
            output_artifact_ids=(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=cost_cents,
            status=status,
            refusal_reason=refusal_reason,
            created_at=utc_now(),
        )

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")

        input_tokens_est = estimate_tokens(request.prompt)
        projected_tokens = input_tokens_est + request.max_output_tokens
        projected_cost_cents = self._cost_cents(input_tokens_est, request.max_output_tokens)

        with self._lock:
            self._reset_ledger_if_needed()
            refusal_reason = self._refusal_reason(projected_tokens, projected_cost_cents)
            if refusal_reason:
                if refusal_reason.startswith("daily_"):
                    self.circuit_breaker.open(refusal_reason)
                return self._refused_response(
                    request,
                    input_tokens=input_tokens_est,
                    refusal_reason=refusal_reason,
                )

        messages: list[dict] = [{"role": "user", "content": request.prompt}]
        system: str | None = None
        if request.json_mode:
            system = (
                "You must respond with valid JSON only. "
                "Do not include any prose, markdown fences, or explanation outside the JSON."
            )

        try:
            create_kwargs: dict = {
                "model": self.model,
                "max_tokens": request.max_output_tokens,
                "messages": messages,
            }
            if system:
                create_kwargs["system"] = system

            message = await self._client.messages.create(**create_kwargs)
        except _anthropic_sdk.APIError as exc:  # type: ignore[union-attr]
            refusal_reason = f"provider_error:{exc}"
            logger.warning("Anthropic API error for job %s: %s", request.job_id, exc)
            with self._lock:
                trace = self._build_trace(
                    request,
                    input_tokens=input_tokens_est,
                    output_tokens=0,
                    cost_cents=0,
                    status="refused",
                    refusal_reason=refusal_reason,
                )
                self.trace_store.append(trace)
            return ModelResponse(
                status="refused",
                text="",
                trace_id=trace.id,
                input_tokens=input_tokens_est,
                output_tokens=0,
                cost_cents=0,
                refusal_reason=refusal_reason,
            )

        text = message.content[0].text if message.content else ""
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost_cents = self._cost_cents(input_tokens, output_tokens)

        with self._lock:
            self._daily_tokens += input_tokens + output_tokens
            self._daily_cost_cents += cost_cents
            trace = self._build_trace(
                request,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_cents=cost_cents,
                status="succeeded",
                refusal_reason=None,
            )
            self.trace_store.append(trace)

        await self._persist_trace(trace)

        return ModelResponse(
            status="succeeded",
            text=text,
            trace_id=trace.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=cost_cents,
        )

    async def _persist_trace(self, trace: JobTrace) -> None:
        if self._db_session_factory is None:
            return
        try:
            async with self._db_session_factory() as session:
                await session.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to persist job trace %s: %s", trace.id, exc)


# ---------------------------------------------------------------------------
# Embedding adapter (OpenAI text-embedding-3-small)
# ---------------------------------------------------------------------------

class AnthropicEmbeddingAdapter:
    """Embedding adapter using OpenAI text-embedding-3-small.

    Anthropic does not provide an embedding API; this adapter uses the OpenAI
    SDK with OPENAI_API_KEY for embedding generation.
    """

    def __init__(self, *, model: str = "text-embedding-3-small") -> None:
        if _openai_sdk is None:
            raise ImportError(
                "The 'openai' package is required for AnthropicEmbeddingAdapter. "
                "Install it with: pip install openai"
            )
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self._client = _openai_sdk.AsyncOpenAI(api_key=api_key)  # type: ignore[union-attr]
        self.model = model

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        response = await self._client.embeddings.create(
            model=request.model or self.model,
            input=request.content,
        )
        data = response.data[0]
        usage = response.usage
        return EmbeddingResponse(
            embedding=data.embedding,
            model=response.model,
            input_tokens=usage.prompt_tokens,
        )


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def get_model_adapter(
    *,
    spend_caps: SpendCaps | None = None,
    trace_store: InMemoryJobTraceStore | None = None,
    db_session_factory: Any = None,
) -> LocalDeterministicModelAdapter | AnthropicModelAdapter:
    """Return the best available model adapter.

    If ANTHROPIC_API_KEY is set, returns an AnthropicModelAdapter.
    Otherwise falls back to LocalDeterministicModelAdapter (mode='local') with a warning.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicModelAdapter(
            spend_caps=spend_caps,
            trace_store=trace_store,
            db_session_factory=db_session_factory,
        )
    logger.warning(
        "ANTHROPIC_API_KEY is not set -- falling back to LocalDeterministicModelAdapter. "
        "Set ANTHROPIC_API_KEY to enable real LLM calls."
    )
    return LocalDeterministicModelAdapter(
        mode="local",
        spend_caps=spend_caps,
        trace_store=trace_store,
    )


def build_model_adapter(settings: object | None = None) -> ModelAdapter:
    """Legacy factory: returns an HttpModelAdapter or LocalDeterministicModelAdapter.

    Prefer get_model_adapter() for new code.
    """
    provider_name = os.environ.get("LLM_PROVIDER", "disabled").strip().lower()
    if provider_name == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        from draftcheck.providers import AnthropicChatProvider

        _provider: Any = AnthropicChatProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
        return HttpModelAdapter(_provider, spend_caps=SpendCaps.from_env())
    if provider_name in ("openai", "openai-compatible") and os.environ.get("OPENAI_API_KEY"):
        from draftcheck.providers import OpenAIChatProvider

        _provider = OpenAIChatProvider(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.environ.get("LLM_MODEL", "gpt-4o"),
        )
        return HttpModelAdapter(_provider, spend_caps=SpendCaps.from_env())
    return LocalDeterministicModelAdapter(mode="disabled")
