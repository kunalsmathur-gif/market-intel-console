import json
from datetime import UTC, date, datetime

import httpx
import pytest
import respx
from pydantic import SecretStr

from citebell_schemas import ClaimType, EvidenceKind, ReportType, RunKey, Source, SourceKind, SourceTier
from citebell_worker.cli import default_policy
from citebell_worker.config import Settings
from citebell_worker.data import FeedItem
from citebell_worker.llm import LLMError, LLMRouter
from citebell_worker.pipeline.extract import (
    extract_claims_from_item,
    extract_news_claims,
    make_extract_step,
)
from citebell_worker.pipeline.runner import RunContext, Section

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

SOURCE = Source(id="example-wire", name="Example Wire", domain="wire.example", tier=SourceTier.T2,
                kind=SourceKind.RSS, url="https://wire.example/markets.rss")

RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Nifty closes at a record high</title>
      <link>https://wire.example/story-1</link>
      <description>Benchmark indices rallied on strong FII buying.</description>
      <pubDate>Mon, 15 Sep 2026 10:30:00 +0530</pubDate>
    </item>
  </channel>
</rss>
"""


def settings(**kw: object) -> Settings:
    base: dict[str, object] = {"gemini_api_key": SecretStr("g-key")}
    return Settings.model_validate(base | kw)


def item(
    title: str = "Nifty closes at a record high",
    summary: str | None = "Benchmark indices rallied on strong FII buying.",
) -> FeedItem:
    return FeedItem(source_id=SOURCE.id, title=title, link="https://wire.example/story-1",
                    summary=summary, published_at=datetime.now(UTC))


def _gemini_claims(*claims: dict[str, str]) -> httpx.Response:
    return httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": json.dumps({"claims": list(claims)})}]},
                       "finishReason": "STOP"}],
    })


@respx.mock
def test_extract_keeps_a_claim_whose_quote_is_in_the_source_text() -> None:
    respx.post(GEMINI_URL).mock(return_value=_gemini_claims(
        {"text": "Nifty hit a record high", "quote": "Benchmark indices rallied on strong FII buying."}))
    router = LLMRouter(settings())
    claims = extract_claims_from_item(router, "prompt", SOURCE, item(), "run:example-wire:0")
    assert len(claims) == 1
    assert claims[0].claim_type is ClaimType.NEWS_EVENT
    assert claims[0].evidence[0].kind is EvidenceKind.ARTICLE
    assert claims[0].evidence[0].quote == "Benchmark indices rallied on strong FII buying."
    assert claims[0].evidence[0].quote_found is False
    assert claims[0].evidence[0].http_status is None


@respx.mock
def test_extract_drops_a_claim_whose_quote_is_invented() -> None:
    respx.post(GEMINI_URL).mock(return_value=_gemini_claims(
        {"text": "Nifty hit a record high", "quote": "a quote that never appeared anywhere"}))
    router = LLMRouter(settings())
    claims = extract_claims_from_item(router, "prompt", SOURCE, item(), "run:example-wire:0")
    assert claims == []


@respx.mock
def test_extract_drops_a_claim_missing_text_or_quote() -> None:
    respx.post(GEMINI_URL).mock(return_value=_gemini_claims(
        {"text": "", "quote": "Benchmark indices rallied on strong FII buying."}))
    router = LLMRouter(settings())
    claims = extract_claims_from_item(router, "prompt", SOURCE, item(), "run:example-wire:0")
    assert claims == []


@respx.mock
def test_extract_news_claims_isolates_a_failing_source() -> None:
    respx.post(GEMINI_URL).mock(return_value=_gemini_claims(
        {"text": "Nifty hit a record high", "quote": "Benchmark indices rallied on strong FII buying."}))
    respx.get(SOURCE.url).mock(return_value=httpx.Response(200, content=RSS_XML))
    bad_source = Source(id="example-daily", name="Example Daily", domain="daily.example",
                        tier=SourceTier.T2, kind=SourceKind.RSS, url="https://daily.example/rss")
    respx.get(bad_source.url).mock(side_effect=httpx.ConnectError("refused"))

    router = LLMRouter(settings())
    with httpx.Client() as client:
        result = extract_news_claims(client, router, "prompt", [SOURCE, bad_source], run_id="run1")

    assert len(result.claims) == 1
    assert len(result.failures) == 1
    assert result.failures[0].startswith("example-daily:")


def test_extract_news_claims_isolates_a_failing_item(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_feed(client: httpx.Client, source: Source) -> list[FeedItem]:
        return [item()]

    def boom(*args: object, **kwargs: object) -> None:
        raise LLMError("model refused")

    monkeypatch.setattr("citebell_worker.pipeline.extract.fetch_feed", fake_fetch_feed)
    monkeypatch.setattr("citebell_worker.pipeline.extract.extract_claims_from_item", boom)

    with httpx.Client() as client:
        result = extract_news_claims(client, object(), "prompt", [SOURCE], run_id="run1")  # type: ignore[arg-type]

    assert result.claims == []
    assert result.failures == ["example-wire[0]: model refused"]


@respx.mock
def test_make_extract_step_creates_a_section_and_records_failures() -> None:
    respx.post(GEMINI_URL).mock(return_value=httpx.Response(503, text="overloaded"))
    respx.get(SOURCE.url).mock(return_value=httpx.Response(200, content=RSS_XML))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        step = make_extract_step(client, router, "prompt", [SOURCE])
        ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
        step(ctx)

    assert [s.key for s in ctx.sections] == ["news"]
    assert ctx.sections[0].claims == []
    assert len(ctx.trace) == 1
    assert ctx.trace[0]["step"] == "extract:failures"


@respx.mock
def test_make_extract_step_appends_to_an_existing_section() -> None:
    respx.post(GEMINI_URL).mock(return_value=_gemini_claims(
        {"text": "Nifty hit a record high", "quote": "Benchmark indices rallied on strong FII buying."}))
    respx.get(SOURCE.url).mock(return_value=httpx.Response(200, content=RSS_XML))
    router = LLMRouter(settings())
    with httpx.Client() as client:
        step = make_extract_step(client, router, "prompt", [SOURCE], section_key="news")
        ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
        ctx.sections.append(Section(key="news", title="News"))
        step(ctx)

    assert len(ctx.sections) == 1
    assert len(ctx.sections[0].claims) == 1


def _run_key() -> RunKey:
    return RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 1, 1))
