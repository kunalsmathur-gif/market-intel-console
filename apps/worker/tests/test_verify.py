from datetime import UTC, date, datetime

import httpx
import respx
from pydantic import SecretStr

from citebell_schemas import (
    Claim,
    ClaimType,
    Evidence,
    EvidenceKind,
    ReportType,
    RunKey,
    SourceTier,
)
from citebell_worker.cli import default_policy
from citebell_worker.config import Settings
from citebell_worker.llm import LLMRouter
from citebell_worker.pipeline.runner import RunContext, Section
from citebell_worker.pipeline.verify import (
    fetch_article,
    make_news_verify_step,
    verify_article_evidence,
)

GEMINI_VERIFY_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
ARTICLE_URL = "https://wire.example/story-1"


def settings(**kw: object) -> Settings:
    base: dict[str, object] = {"gemini_api_key": SecretStr("g-key")}
    return Settings.model_validate(base | kw)


def article_evidence(quote: str = "benchmark indices rallied on strong fii buying") -> Evidence:
    return Evidence(
        kind=EvidenceKind.ARTICLE,
        source_id="example-wire",
        tier=SourceTier.T2,
        url=ARTICLE_URL,
        published_at=datetime.now(UTC),
        fetched_at=datetime.now(UTC),
        quote=quote,
        quote_found=False,
    )


def news_claim(evidence: tuple[Evidence, ...]) -> Claim:
    return Claim(id="claim-1", claim_type=ClaimType.NEWS_EVENT, text="Nifty hit a record high",
                evidence=evidence)


def _gemini_supported(supported: bool) -> httpx.Response:
    return httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": f'{{"supported": {str(supported).lower()}}}'}]},
                       "finishReason": "STOP"}],
    })


@respx.mock
def test_fetch_article_returns_status_and_body_on_non_200() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(404, text="not found"))
    with httpx.Client() as client:
        status, body = fetch_article(client, ARTICLE_URL, retries=0)
    assert status == 404
    assert body == "not found"


def test_fetch_article_returns_none_on_transport_failure() -> None:
    with respx.mock:
        respx.get(ARTICLE_URL).mock(side_effect=httpx.ConnectError("refused"))
        with httpx.Client() as client:
            status, body = fetch_article(client, ARTICLE_URL, retries=0)
    assert status is None
    assert body == ""


@respx.mock
def test_verify_sets_quote_found_true_on_a_literal_match() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(
        200, text="<html><body>Benchmark indices rallied on strong FII buying.</body></html>"))
    respx.post(GEMINI_VERIFY_URL).mock(return_value=_gemini_supported(True))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        updated, reason = verify_article_evidence(client, router, "prompt", "Nifty hit a record high",
                                                   article_evidence())
    assert updated.http_status == 200
    assert updated.quote_found is True
    assert reason is None


@respx.mock
def test_verify_sets_quote_found_false_when_the_quote_is_not_on_the_page() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(
        200, text="<html><body>Something unrelated.</body></html>"))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        updated, reason = verify_article_evidence(client, router, "prompt", "Nifty hit a record high",
                                                   article_evidence())
    assert updated.http_status == 200
    assert updated.quote_found is False
    assert reason is None  # the gate step withholds this evidence on its own; no need for the model


@respx.mock
def test_verify_records_http_status_on_failure_without_calling_the_model() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(404, text="gone"))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        updated, reason = verify_article_evidence(client, router, "prompt", "Nifty hit a record high",
                                                   article_evidence())
    assert updated.http_status == 404
    assert updated.quote_found is False
    assert reason is None


@respx.mock
def test_verify_drops_a_claim_the_model_judges_unsupported() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(
        200, text="<html><body>Benchmark indices rallied on strong FII buying.</body></html>"))
    respx.post(GEMINI_VERIFY_URL).mock(return_value=_gemini_supported(False))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        updated, reason = verify_article_evidence(client, router, "prompt", "Nifty hit a record high",
                                                   article_evidence())
    assert updated.quote_found is True
    assert reason is not None
    assert "does not support" in reason


@respx.mock
def test_verify_fails_open_when_the_model_call_errors() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(
        200, text="<html><body>Benchmark indices rallied on strong FII buying.</body></html>"))
    respx.post(GEMINI_VERIFY_URL).mock(return_value=httpx.Response(503, text="overloaded"))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        updated, reason = verify_article_evidence(client, router, "prompt", "Nifty hit a record high",
                                                   article_evidence())
    assert updated.quote_found is True
    assert reason is None  # fails open: the model being unavailable never drops a claim


def test_verify_article_evidence_rejects_evidence_with_no_url() -> None:
    with httpx.Client() as client:
        updated, reason = verify_article_evidence(client, object(), "prompt", "text",  # type: ignore[arg-type]
                                                   article_evidence().model_copy(update={"url": None}))
    assert reason == "article evidence has no url to verify"
    assert updated.http_status is None


@respx.mock
def test_make_news_verify_step_updates_evidence_and_reassigns_claims() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(
        200, text="<html><body>Benchmark indices rallied on strong FII buying.</body></html>"))
    respx.post(GEMINI_VERIFY_URL).mock(return_value=_gemini_supported(True))
    router = LLMRouter(settings())
    ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
    section = Section(key="news", title="News")
    section.claims.append(news_claim((article_evidence(),)))
    ctx.sections.append(section)

    with httpx.Client() as client:
        step = make_news_verify_step(client, router, "prompt")
        step(ctx)

    assert len(ctx.sections[0].claims) == 1
    assert ctx.sections[0].claims[0].evidence[0].quote_found is True
    assert ctx.trace == []


@respx.mock
def test_make_news_verify_step_drops_unsupported_claims_and_traces() -> None:
    respx.get(ARTICLE_URL).mock(return_value=httpx.Response(
        200, text="<html><body>Benchmark indices rallied on strong FII buying.</body></html>"))
    respx.post(GEMINI_VERIFY_URL).mock(return_value=_gemini_supported(False))
    router = LLMRouter(settings())
    ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
    section = Section(key="news", title="News")
    section.claims.append(news_claim((article_evidence(),)))
    ctx.sections.append(section)

    with httpx.Client() as client:
        step = make_news_verify_step(client, router, "prompt")
        step(ctx)

    assert ctx.sections[0].claims == []
    assert len(ctx.trace) == 1
    assert ctx.trace[0]["step"] == "verify:failures"


def test_make_news_verify_step_leaves_non_news_claims_untouched() -> None:
    ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
    section = Section(key="market", title="Market")
    market_claim = Claim(id="market-1", claim_type=ClaimType.MARKET_NUMBER, text="x")
    section.claims.append(market_claim)
    ctx.sections.append(section)

    step = make_news_verify_step(object(), object(), "prompt")  # type: ignore[arg-type]
    step(ctx)

    assert ctx.sections[0].claims == [market_claim]


def _run_key() -> RunKey:
    return RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 1, 1))
