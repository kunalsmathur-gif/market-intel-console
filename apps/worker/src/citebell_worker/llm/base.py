"""A provider-neutral model call: prompt in, JSON out (PRD §8.2, §8.12).

Each pipeline step reads its model from settings as "provider:model", so switching vendors
is a settings change. Models never produce numbers; they return placeholders that code fills in.
"""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class LLMError(RuntimeError):
    """A model call failed: transport error, refusal, or output that isn't valid JSON."""


@dataclass(frozen=True)
class ModelRef:
    provider: str
    model: str

    @classmethod
    def parse(cls, spec: str) -> "ModelRef":
        provider, sep, model = spec.partition(":")
        if not sep or not provider or not model:
            raise ValueError(f"model must look like 'provider:model', got {spec!r}")
        return cls(provider, model)

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass(frozen=True)
class LLMRequest:
    system: str  # fixed instructions first, so providers that cache prompts charge less for them
    user: str
    schema_name: str
    json_schema: dict[str, Any]
    temperature: float = 0.0
    # Extended "thinking" helps open-ended writing/classification but adds real latency for a
    # narrow yes/no judgement (verify) where it isn't needed. Backends that don't support the
    # concept (e.g. OpenRouter models without a reasoning toggle) ignore this.
    thinking: bool = True


@dataclass(frozen=True)
class LLMResult:
    model: ModelRef
    data: Any
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float | None = None  # reported by OpenRouter; computed from token prices for Gemini


class Backend(Protocol):
    provider: str

    def complete_json(self, client: httpx.Client, model: str, request: LLMRequest) -> LLMResult: ...
