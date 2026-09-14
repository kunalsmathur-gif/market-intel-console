import httpx
import pytest
import respx
from pydantic import SecretStr

from citebell_worker.config import Settings
from citebell_worker.llm import LLMError, LLMRequest, LLMRouter, ModelRef, Step

REQUEST = LLMRequest(system="rules", user="article", schema_name="claims",
                     json_schema={"type": "object", "properties": {"claims": {"type": "array"}}})
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def settings(**kw: object) -> Settings:
    base: dict[str, object] = {
        "gemini_api_key": SecretStr("g-key"),
        "openrouter_api_key": SecretStr("or-key"),
        "llm_extract": "gemini:gemini-2.5-flash-lite",
        "llm_extract_backup": "openrouter:deepseek/deepseek-v4-flash",
    }
    return Settings.model_validate(base | kw)


def test_model_ref_parsing() -> None:
    assert ModelRef.parse("openrouter:google/gemini-2.5-flash") == ModelRef(
        "openrouter", "google/gemini-2.5-flash")
    with pytest.raises(ValueError):
        ModelRef.parse("gemini-2.5-flash")


@respx.mock
def test_gemini_call_returns_parsed_json_and_usage() -> None:
    route = respx.post(GEMINI_URL).mock(return_value=httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": '{"claims": []}'}]}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 8, "thoughtsTokenCount": 4},
    }))
    result = LLMRouter(settings()).complete_json(Step.EXTRACT, REQUEST)
    assert result.data == {"claims": []}
    assert (result.input_tokens, result.output_tokens) == (120, 12)
    sent = route.calls.last.request
    assert sent.headers["x-goog-api-key"] == "g-key"
    assert b'"responseMimeType":"application/json"' in sent.content


@respx.mock
def test_falls_back_to_the_backup_model_when_the_primary_fails() -> None:
    respx.post(GEMINI_URL).mock(return_value=httpx.Response(503, text="overloaded"))
    route = respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json={
        "choices": [{"message": {"content": '{"claims": [1]}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 5, "cost": 0.00002},
    }))
    result = LLMRouter(settings()).complete_json(Step.EXTRACT, REQUEST)
    assert result.model == ModelRef("openrouter", "deepseek/deepseek-v4-flash")
    assert result.cost_usd == pytest.approx(0.00002)
    assert b'"require_parameters":true' in route.calls.last.request.content


@respx.mock
def test_invalid_json_everywhere_raises() -> None:
    respx.post(GEMINI_URL).mock(return_value=httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": "not json"}]}, "finishReason": "MAX_TOKENS"}],
    }))
    with pytest.raises(LLMError, match="every model failed"):
        LLMRouter(settings(llm_extract_backup=None)).complete_json(Step.EXTRACT, REQUEST)


def test_missing_key_is_reported_not_called() -> None:
    router = LLMRouter(settings(gemini_api_key=None, llm_extract_backup=None))
    with pytest.raises(LLMError, match="no API key configured for gemini"):
        router.complete_json(Step.EXTRACT, REQUEST)
