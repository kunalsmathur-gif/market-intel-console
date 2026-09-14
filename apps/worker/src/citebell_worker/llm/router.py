"""Pick the model for a pipeline step, and fall back to its backup when the primary fails."""

import logging
from enum import StrEnum

import httpx

from ..config import Settings
from .base import Backend, LLMError, LLMRequest, LLMResult, ModelRef
from .gemini import GeminiBackend
from .openrouter import OpenRouterBackend

log = logging.getLogger(__name__)


class Step(StrEnum):
    CLASSIFY = "classify"  # sort and group stories
    EXTRACT = "extract"  # split drafts into atomic claims
    VERIFY = "verify"  # judge whether a source supports a claim
    WRITE = "write"  # fill the report template, with placeholders for numbers
    QA = "qa"  # consistency, rounding and attribution checks


class LLMRouter:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=settings.llm_timeout_seconds)
        self._backends: dict[str, Backend] = {}
        if settings.gemini_api_key is not None:
            self._backends["gemini"] = GeminiBackend(settings.gemini_api_key.get_secret_value())
        if settings.openrouter_api_key is not None:
            key = settings.openrouter_api_key.get_secret_value()
            self._backends["openrouter"] = OpenRouterBackend(key)

    def models_for(self, step: Step) -> list[ModelRef]:
        primary = getattr(self._settings, f"llm_{step}")
        backup = getattr(self._settings, f"llm_{step}_backup")
        return [ModelRef.parse(spec) for spec in (primary, backup) if spec]

    def complete_json(self, step: Step, request: LLMRequest) -> LLMResult:
        errors: list[str] = []
        for ref in self.models_for(step):
            backend = self._backends.get(ref.provider)
            if backend is None:
                errors.append(f"{ref}: no API key configured for {ref.provider}")
                continue
            try:
                return backend.complete_json(self._client, ref.model, request)
            except (LLMError, httpx.HTTPError) as exc:
                log.warning("step %s: %s failed: %s", step, ref, exc)
                errors.append(f"{ref}: {exc}")
        raise LLMError(f"step {step}: every model failed: " + "; ".join(errors))
