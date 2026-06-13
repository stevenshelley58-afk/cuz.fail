"""Governed local model substrate for V3.

This module is intentionally provider-neutral and performs no network calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
import os
import re
from threading import RLock
from typing import Any, Literal, Protocol, runtime_checkable
from uuid import uuid4


ModelCallStatus = Literal["succeeded", "refused"]
AdapterMode = Literal["disabled", "local"]


TOKEN_RE = re.compile(r"\S+")


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


class ModelAdapter(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse:
        """Run a governed model call."""


@runtime_checkable
class JobTraceStore(Protocol):
    def append(self, trace: JobTrace) -> None: ...
    def contains(self, trace_id: str) -> bool: ...
    def seed_daily_counters(self, today: date) -> tuple[int, int]: ...


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

    def contains(self, trace_id: str) -> bool:
        with self._lock:
            return any(trace.id == trace_id for trace in self._traces)

    def seed_daily_counters(self, today: date) -> tuple[int, int]:
        # In-memory store has no persistence; always starts fresh.
        return 0, 0


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


class HttpModelAdapter:
    """Routes ModelRequest through a live chat provider with spend controls and traces."""

    cost_per_1000_tokens_cents = 0  # Updated to actual cost once provider reports usage

    def __init__(
        self,
        provider: "Any",  # ChatProvider protocol
        *,
        spend_caps: SpendCaps | None = None,
        trace_store: JobTraceStore | None = None,
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

    @property
    def trace_store(self) -> JobTraceStore:
        return self._trace_store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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


def build_model_adapter(settings: object | None = None) -> ModelAdapter:
    """Factory: returns an HttpModelAdapter backed by the configured provider, or
    a LocalDeterministicModelAdapter in disabled mode if no live provider is configured.
    """
    import os

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
