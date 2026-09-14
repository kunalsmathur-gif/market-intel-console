"""OpenRouter's OpenAI-compatible API: used for the bake-off and for backup models (PRD §8.12)."""

import json
import time

import httpx

from .base import LLMError, LLMRequest, LLMResult, ModelRef

BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterBackend:
    provider = "openrouter"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def complete_json(self, client: httpx.Client, model: str, request: LLMRequest) -> LLMResult:
        body = {
            "model": model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.json_schema,
                },
            },
            # Only route to providers that honour the JSON schema and temperature.
            "provider": {"require_parameters": True},
        }
        started = time.monotonic()
        response = client.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=body,
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        if response.status_code != 200:
            raise LLMError(f"openrouter {model}: HTTP {response.status_code}: {response.text[:300]}")

        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise LLMError(f"openrouter {model}: no choices ({payload.get('error')})")
        content = choices[0].get("message", {}).get("content") or ""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            finish = choices[0].get("finish_reason")
            raise LLMError(f"openrouter {model}: invalid JSON (finish_reason={finish})") from exc

        usage = payload.get("usage", {})
        return LLMResult(
            model=ModelRef(self.provider, model),
            data=data,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            cost_usd=usage.get("cost"),
        )
