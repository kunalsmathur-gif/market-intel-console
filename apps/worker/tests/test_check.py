from datetime import UTC, date, datetime
from decimal import Decimal

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
from citebell_worker.pipeline.check import _rounded_value_text, make_check_step
from citebell_worker.pipeline.runner import Citation, RenderedSection, RunContext, Section


def feed_evidence(source_id: str = "nse") -> Evidence:
    return Evidence(
        kind=EvidenceKind.FEED, source_id=source_id, tier=SourceTier.T1,
        url="https://nse.example/data", fetched_at=datetime.now(UTC),
    )


def market_claim(claim_id: str, field: str, value: str, unit: str | None = None) -> Claim:
    return Claim(id=claim_id, claim_type=ClaimType.MARKET_NUMBER, text=f"{field} is {value}",
                field=field, unit=unit, value=Decimal(value), evidence=(feed_evidence(),))


def forecast_claim(claim_id: str, attributed_to: str | None, text: str) -> Claim:
    return Claim(id=claim_id, claim_type=ClaimType.FORECAST, text=text, attributed_to=attributed_to,
                evidence=(feed_evidence(),))


def published_section(key: str, claims: list[Claim]) -> Section:
    section = Section(key=key, title=key)
    section.claims = claims
    section.decisions = [
        GateDecision(claim_id=c.id, verdict=Verdict.PUBLISH, badge=Badge.PRIMARY_DATA) for c in claims
    ]
    return section


def _run_key() -> RunKey:
    return RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 1, 1))


def test_rounded_value_text_rounds_a_percent_value_beyond_two_decimals() -> None:
    claim = market_claim("c1", "india_vix.ltp", "14.5678", unit="percent")
    assert _rounded_value_text(claim) == "14.57%"


def test_rounded_value_text_returns_none_when_already_within_the_convention() -> None:
    claim = market_claim("c1", "india_vix.ltp", "14.5", unit="percent")
    assert _rounded_value_text(claim) is None


def test_rounded_value_text_returns_none_for_a_unit_with_no_display_convention() -> None:
    claim = market_claim("c1", "nifty50.close", "24500.123456")
    assert _rounded_value_text(claim) is None


def test_make_check_step_rounds_excess_precision_in_the_rendered_text() -> None:
    claim = market_claim("c1", "india_vix.ltp", "14.5678", unit="percent")
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("market", [claim]))
    ctx.rendered_sections = [
        RenderedSection("india_setup_and_flows", "India Setup & Flows",
                        text="VIX stood at 14.5678% today.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),)),
    ]

    step = make_check_step()
    step(ctx)

    assert ctx.rendered_sections[0].text == "VIX stood at 14.57% today."


def test_make_check_step_withholds_sections_with_conflicting_field_values() -> None:
    claim_a = market_claim("c1", "nifty50.close", "24500")
    claim_b = market_claim("c2", "nifty50.close", "24600")
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("market", [claim_a, claim_b]))
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="Nifty closed at 24500 today.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),)),
        RenderedSection("s2", "Section Two", text="Nifty closed at 24600 today.",
                        citations=(Citation(claim_id="c2", source_id="nse", url=None),)),
    ]

    step = make_check_step()
    step(ctx)

    assert all(s.text is None for s in ctx.rendered_sections)
    assert all(s.withheld_reason and "nifty50.close" in s.withheld_reason for s in ctx.rendered_sections)
    assert len(ctx.trace) == 1
    assert ctx.trace[0]["step"] == "check:withheld"


def test_make_check_step_leaves_consistent_sections_untouched() -> None:
    claim = market_claim("c1", "nifty50.close", "24500")
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("market", [claim]))
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="Nifty closed at 24500 today.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),)),
        RenderedSection("s2", "Section Two", text="Also 24500 for Nifty.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),)),
    ]

    step = make_check_step()
    step(ctx)

    assert ctx.rendered_sections[0].text == "Nifty closed at 24500 today."
    assert ctx.rendered_sections[1].text == "Also 24500 for Nifty."
    assert ctx.trace == []


def test_make_check_step_withholds_a_forecast_with_no_attribution_in_the_text() -> None:
    claim = forecast_claim("c1", "Brokerage X", "Nifty will rally")
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("news", [claim]))
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="Analysts expect a rally.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),)),
    ]

    step = make_check_step()
    step(ctx)

    assert ctx.rendered_sections[0].text is None
    assert "no attribution" in (ctx.rendered_sections[0].withheld_reason or "")
    assert len(ctx.trace) == 1
    assert ctx.trace[0]["step"] == "check:withheld"


def test_make_check_step_keeps_a_forecast_that_names_its_source_in_the_text() -> None:
    claim = forecast_claim("c1", "Brokerage X", "Nifty will rally")
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.sections.append(published_section("news", [claim]))
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="Brokerage X expects a rally.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),)),
    ]

    step = make_check_step()
    step(ctx)

    assert ctx.rendered_sections[0].text == "Brokerage X expects a rally."


def test_make_check_step_ignores_sections_already_withheld_by_write() -> None:
    ctx = RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text=None, withheld_reason="no claims yet"),
    ]

    step = make_check_step()
    step(ctx)

    assert ctx.rendered_sections[0].text is None
    assert ctx.trace == []
