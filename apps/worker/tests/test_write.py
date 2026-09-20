from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import respx
from pydantic import SecretStr

from citebell_schemas import (
    Badge,
    Claim,
    ClaimType,
    Evidence,
    EvidenceKind,
    GateDecision,
    ReportType,
    RunKey,
    SourceTier,
    Verdict,
)
from citebell_worker.config import Settings
from citebell_worker.llm import LLMRouter
from citebell_worker.pipeline.runner import RunContext, Section
from citebell_worker.pipeline.templates import REPORT_TEMPLATES, ReportTemplate, SectionTemplate
from citebell_worker.pipeline.write import (
    claim_value_text,
    make_write_step,
    render_section,
)

GEMINI_WRITE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"


def settings(**kw: object) -> Settings:
    base: dict[str, object] = {"gemini_api_key": SecretStr("g-key")}
    return Settings.model_validate(base | kw)


def feed_evidence(source_id: str = "nse") -> Evidence:
    return Evidence(
        kind=EvidenceKind.FEED, source_id=source_id, tier=SourceTier.T1,
        url="https://nse.example/data", fetched_at=datetime.now(UTC),
    )


def market_claim(claim_id: str, field: str, value: str, unit: str | None = None) -> Claim:
    return Claim(id=claim_id, claim_type=ClaimType.MARKET_NUMBER, text=f"{field} is {value}",
                field=field, unit=unit, value=Decimal(value), evidence=(feed_evidence(),))


def news_claim(claim_id: str, text: str = "Nifty hit a record high") -> Claim:
    return Claim(id=claim_id, claim_type=ClaimType.NEWS_EVENT, text=text,
                evidence=(feed_evidence("example-wire"),))


def published_section(key: str, claims: list[Claim]) -> Section:
    section = Section(key=key, title=key)
    section.claims = claims
    section.decisions = [
        GateDecision(claim_id=c.id, verdict=Verdict.PUBLISH, badge=Badge.PRIMARY_DATA) for c in claims
    ]
    return section


def _run_key() -> RunKey:
    return RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 1, 1))


def _gemini_paragraph(paragraph: str) -> httpx.Response:
    return httpx.Response(200, json={
        "candidates": [{
            "content": {"parts": [{"text": '{"paragraph": ' + repr(paragraph).replace("'", '"') + "}"}]},
            "finishReason": "STOP",
        }],
    })


def testclaim_value_text_renders_percent_suffix() -> None:
    claim = market_claim("c1", "india_vix.ltp", "14.5", unit="percent")
    assert claim_value_text(claim) == "14.5%"


def testclaim_value_text_renders_inr_crore_suffix() -> None:
    claim = market_claim("c1", "fii.net_cash_cr", "1200", unit="inr_crore")
    assert claim_value_text(claim) == "1200 Cr"


def testclaim_value_text_renders_plain_value_with_no_unit() -> None:
    claim = market_claim("c1", "nifty50.close", "24500")
    assert claim_value_text(claim) == "24500"


def testclaim_value_text_falls_back_to_claim_text_for_news() -> None:
    claim = news_claim("c1", "Nifty hit a record high")
    assert claim_value_text(claim) == "Nifty hit a record high"


def test_render_section_withholds_when_no_slots_available() -> None:
    template = SectionTemplate("data_outlook", "Data Outlook")
    router = LLMRouter(settings())
    result = render_section(template, {}, set(), router, "prompt")
    assert result.text is None
    assert result.withheld_reason == "no published claims for this section yet"


@respx.mock
def test_render_section_resolves_placeholders_and_builds_citations() -> None:
    respx.post(GEMINI_WRITE_URL).mock(
        return_value=_gemini_paragraph("Nifty closed at {{c1}} today.")
    )
    template = SectionTemplate("india_setup_and_flows", "India Setup & Flows",
                               market_fields=("nifty50.close",))
    claim = market_claim("c1", "nifty50.close", "24500")
    router = LLMRouter(settings())
    result = render_section(template, {"c1": claim}, set(), router, "prompt")
    assert result.text == "Nifty closed at 24500 today."
    assert result.withheld_reason is None
    assert len(result.citations) == 1
    assert result.citations[0].claim_id == "c1"
    assert result.citations[0].source_id == "nse"


@respx.mock
def test_render_section_withholds_when_model_cites_unknown_placeholder() -> None:
    respx.post(GEMINI_WRITE_URL).mock(
        return_value=_gemini_paragraph("Nifty closed at {{made-up}} today.")
    )
    template = SectionTemplate("india_setup_and_flows", "India Setup & Flows",
                               market_fields=("nifty50.close",))
    claim = market_claim("c1", "nifty50.close", "24500")
    router = LLMRouter(settings())
    result = render_section(template, {"c1": claim}, set(), router, "prompt")
    assert result.text is None
    assert result.withheld_reason is not None
    assert "made-up" in result.withheld_reason


@respx.mock
def test_render_section_withholds_when_llm_call_fails() -> None:
    respx.post(GEMINI_WRITE_URL).mock(return_value=httpx.Response(503, text="overloaded"))
    template = SectionTemplate("india_setup_and_flows", "India Setup & Flows",
                               market_fields=("nifty50.close",))
    claim = market_claim("c1", "nifty50.close", "24500")
    router = LLMRouter(settings())
    result = render_section(template, {"c1": claim}, set(), router, "prompt")
    assert result.text is None
    assert "writer model unavailable" in (result.withheld_reason or "")


@respx.mock
def test_make_write_step_populates_rendered_sections_and_traces_withheld() -> None:
    respx.post(GEMINI_WRITE_URL).mock(
        return_value=_gemini_paragraph("Nifty closed at {{c1}} today.")
    )
    report_template = ReportTemplate(ReportType.MORNING, (
        SectionTemplate("india_setup_and_flows", "India Setup & Flows",
                        market_fields=("nifty50.close",)),
        SectionTemplate("data_outlook", "Data Outlook"),  # no fields -> always withheld
    ))
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("market", [market_claim("c1", "nifty50.close", "24500")]))

    router = LLMRouter(settings())
    step = make_write_step(report_template, router, "prompt")
    step(ctx)

    assert len(ctx.rendered_sections) == 2
    written, withheld = ctx.rendered_sections
    assert written.key == "india_setup_and_flows"
    assert written.text == "Nifty closed at 24500 today."
    assert withheld.key == "data_outlook"
    assert withheld.text is None

    assert len(ctx.trace) == 1
    assert ctx.trace[0]["step"] == "write:withheld"
    assert "data_outlook" in ctx.trace[0]["detail"]


@respx.mock
def test_make_write_step_dedupes_news_claims_across_sections() -> None:
    respx.post(GEMINI_WRITE_URL).mock(
        return_value=_gemini_paragraph("Big news: {{n1}}.")
    )
    report_template = ReportTemplate(ReportType.MORNING, (
        SectionTemplate("s1", "Section One", include_news=True),
        SectionTemplate("s2", "Section Two", include_news=True),
    ))
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("news", [news_claim("n1")]))

    router = LLMRouter(settings())
    step = make_write_step(report_template, router, "prompt")
    step(ctx)

    # only the first section in template order gets the single available news claim;
    # the second has nothing left to write about and is withheld with no LLM call made.
    assert ctx.rendered_sections[1].withheld_reason == "no published claims for this section yet"


def test_report_templates_cover_every_report_type() -> None:
    for report_type in ReportType:
        assert report_type in REPORT_TEMPLATES
        template = REPORT_TEMPLATES[report_type]
        assert template.report_type is report_type
        assert len(template.sections) > 0
