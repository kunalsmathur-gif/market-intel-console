"""Gemini API with a direct key, paid tier (PRD §9.1). Free-tier keys must not be used in production."""

import json
import time

import httpx

from .base import LLMError, LLMRequest, LLMResult, ModelRef

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiBackend:
    provider = "gemini"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def complete_json(self, client: httpx.Client, model: str, request: LLMRequest) -> LLMResult:
        body = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.user}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "responseMimeType": "application/json",
                "responseJsonSchema": request.json_schema,
                # Thinking adds real latency for a narrow judgement call; skip it when the
                # caller doesn't need deep reasoning (LLMRequest.thinking=False).
                "thinkingConfig": {"thinkingBudget": 0} if not request.thinking else {},
            },
        }
        started = time.monotonic()
        response = client.post(
            f"{BASE_URL}/models/{model}:generateContent",
            headers={"x-goog-api-key": self._api_key},
            json=body,
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        if response.status_code != 200:
            raise LLMError(f"gemini {model}: HTTP {response.status_code}: {response.text[:300]}")

        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            reason = payload.get("promptFeedback", {}).get("blockReason", "no candidates")
            raise LLMError(f"gemini {model}: {reason}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            finish = candidates[0].get("finishReason")
            raise LLMError(f"gemini {model}: invalid JSON (finishReason={finish})") from exc

        usage = payload.get("usageMetadata", {})
        return LLMResult(
            model=ModelRef(self.provider, model),
            data=data,
            input_tokens=usage.get("promptTokenCount", 0),
            # Thinking tokens are billed as output.
            output_tokens=usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0),
            latency_ms=latency_ms,
        )
