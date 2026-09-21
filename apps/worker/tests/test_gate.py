from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from citebell_schemas import Badge, Claim, ClaimType, Evidence, EvidenceKind, SourceTier, Verdict
from citebell_worker.pipeline.gate import GatePolicy, Tolerance, decide

NOW = datetime(2026, 9, 15, 2, 45, tzinfo=UTC)  # 08:15 IST
POLICY = GatePolicy(now=NOW, stale_before=NOW - timedelta(hours=24))


def feed(source: str, tier: SourceTier, value: str, **kw: object) -> Evidence:
    fields: dict[str, object] = {
        "kind": EvidenceKind.FEED, "source_id": source, "tier": tier,
        "fetched_at": NOW, "value": Decimal(value), "as_of": NOW - timedelta(minutes=5),
    }
    return Evidence.model_validate(fields | kw)


def article(source: str, tier: SourceTier, value: str | None = None, **kw: Any) -> Evidence:
    fields: dict[str, object] = {
        "kind": EvidenceKind.ARTICLE, "source_id": source, "tier": tier,
        "url": f"https://{source}.example/story", "fetched_at": NOW, "http_status": 200,
        "published_at": NOW - timedelta(hours=1), "quote": "Nifty closed higher",
        "quote_found": True, "value": None if value is None else Decimal(value),
    }
    return Evidence.model_validate(fields | kw)


def number(value: str, *evidence: Evidence, unit: str = "index_points") -> Claim:
    return Claim(id="c1", claim_type=ClaimType.MARKET_NUMBER, text="Nifty 50 closed at …",
                 field="nifty50.close", unit=unit, value=Decimal(value),
                 as_of=NOW - timedelta(hours=17), evidence=evidence)


def event(*evidence: Evidence) -> Claim:
    return Claim(id="e1", claim_type=ClaimType.NEWS_EVENT, text="RBI kept the repo rate unchanged",
                 evidence=evidence)


class TestMarketNumbers:
    def test_t1_feed_match_is_primary_data(self) -> None:
        decision = decide(number("25100.50", feed("exchange", SourceTier.T1, "25100.50")), POLICY)
        assert (decision.verdict, decision.badge) == (Verdict.PUBLISH, Badge.PRIMARY_DATA)

    def test_index_tolerance_is_a_hundredth_of_a_percent(self) -> None:
        inside = number("25100.00", feed("exchange", SourceTier.T1, "25102.50"))
        outside = number("25100.00", feed("exchange", SourceTier.T1, "25103.00"))
        assert decide(inside, POLICY).verdict is Verdict.PUBLISH
        assert decide(outside, POLICY).verdict is Verdict.WITHHOLD

    def test_flows_must_match_to_a_paisa_crore(self) -> None:
        ok = number("-1234.56", feed("nse-file", SourceTier.T1, "-1234.57"), unit="inr_crore")
        off = number("-1234.56", feed("nse-file", SourceTier.T1, "-1234.58"), unit="inr_crore")
        assert decide(ok, POLICY).verdict is Verdict.PUBLISH
        assert decide(off, POLICY).verdict is Verdict.WITHHOLD

    def test_unknown_unit_needs_an_exact_match(self) -> None:
        claim = number("83.12", feed("broker", SourceTier.T1, "83.1201"), unit="inr_per_usd")
        assert decide(claim, POLICY).verdict is Verdict.WITHHOLD

    def test_two_independent_feeds_agreeing_is_primary_data(self) -> None:
        claim = number("62000", feed("coingecko", SourceTier.T2, "62000"),
                       feed("exchange-b", SourceTier.T2, "62000"), unit="usd")
        assert decide(claim, POLICY).badge is Badge.PRIMARY_DATA

    def test_two_news_reports_agreeing_is_news_reported(self) -> None:
        claim = number("25080", article("wire", SourceTier.T2, "25080"),
                       article("daily", SourceTier.T2, "25080"))
        decision = decide(claim, POLICY)
        assert (decision.badge, decision.independent_sources) == (Badge.NEWS_REPORTED, 2)

    def test_syndicated_copies_count_once(self) -> None:
        claim = number("25080", article("site-a", SourceTier.T2, "25080", syndication_group="pti:991"),
                       article("site-b", SourceTier.T2, "25080", syndication_group="pti:991"))
        assert decide(claim, POLICY).verdict is Verdict.WITHHOLD

    def test_any_disagreeing_source_withholds(self) -> None:
        claim = number("25100.50", feed("exchange", SourceTier.T1, "25100.50"),
                       article("daily", SourceTier.T2, "25150"))
        decision = decide(claim, POLICY)
        assert decision.verdict is Verdict.WITHHOLD
        assert "disagree" in decision.reasons[-1]

    def test_two_data_feeds_disagreeing_withholds(self) -> None:
        """The realistic production conflict: two connectors (e.g. FRED vs CoinGecko) disagree."""
        claim = number("62000", feed("coingecko", SourceTier.T2, "62000"),
                       feed("exchange-b", SourceTier.T2, "61500"), unit="usd")
        decision = decide(claim, POLICY)
        assert decision.verdict is Verdict.WITHHOLD
        assert "disagree" in decision.reasons[-1]

    def test_one_outlier_among_three_sources_still_withholds(self) -> None:
        """No majority vote: even 2-of-3 agreeing doesn't publish if one source disagrees."""
        claim = number("25100.50", feed("exchange", SourceTier.T1, "25100.50"),
                       article("wire", SourceTier.T2, "25100.50"),
                       article("daily", SourceTier.T2, "25200.00"))
        decision = decide(claim, POLICY)
        assert decision.verdict is Verdict.WITHHOLD
        assert "daily=25200.00" in decision.reasons[-1]

    def test_single_source_is_withheld_unless_policy_allows_it(self) -> None:
        claim = number("25080", article("wire", SourceTier.T2, "25080"))
        assert decide(claim, POLICY).verdict is Verdict.WITHHOLD
        lenient = GatePolicy(now=NOW, stale_before=POLICY.stale_before, allow_single_source=True)
        assert decide(claim, lenient).badge is Badge.SINGLE_SOURCE

    def test_missing_as_of_time_withholds(self) -> None:
        claim = Claim(id="c2", claim_type=ClaimType.MARKET_NUMBER, text="…", unit="index_points",
                      value=Decimal("1"), evidence=(feed("exchange", SourceTier.T1, "1"),))
        assert decide(claim, POLICY).verdict is Verdict.WITHHOLD

    def test_t3_sources_do_not_count(self) -> None:
        claim = number("25080", article("blog", SourceTier.T3, "25080"),
                       article("forum", SourceTier.T3, "25080"))
        assert decide(claim, POLICY).verdict is Verdict.WITHHOLD


class TestNewsEvents:
    def test_one_t1_source_verifies(self) -> None:
        assert decide(event(article("rbi", SourceTier.T1)), POLICY).badge is Badge.VERIFIED

    def test_two_independent_t2_sources_verify(self) -> None:
        decision = decide(event(article("wire", SourceTier.T2), article("daily", SourceTier.T2)),
                          POLICY)
        assert (decision.badge, decision.independent_sources) == (Badge.VERIFIED, 2)

    def test_tx_sources_never_count(self) -> None:
        decision = decide(event(article("wire", SourceTier.T2), article("telegram", SourceTier.TX)),
                          POLICY)
        assert decision.verdict is Verdict.WITHHOLD
        assert any("TX" in reason for reason in decision.reasons)

    def test_contradictory_single_sourced_reports_both_withhold(self) -> None:
        """If two outlets report different, single-sourced versions of the same event
        (e.g. 'RBI held rates' vs 'RBI cut rates'), neither meets the 2-independent-source
        bar on its own, so both fail closed by default rather than one publishing unchecked."""
        held = event(article("wire-a", SourceTier.T2))
        cut = event(article("wire-b", SourceTier.T2))
        assert decide(held, POLICY).verdict is Verdict.WITHHOLD
        assert decide(cut, POLICY).verdict is Verdict.WITHHOLD

    @pytest.mark.parametrize(
        ("change", "reason"),
        [
            ({"http_status": 404}, "link check failed"),
            ({"quote_found": False}, "quote not found"),
            ({"published_at": NOW - timedelta(days=3)}, "stale"),
            ({"published_at": NOW + timedelta(hours=1)}, "future"),
            ({"published_at": None}, "no publish time"),
        ],
    )
    def test_broken_evidence_is_excluded(self, change: dict[str, Any], reason: str) -> None:
        decision = decide(event(article("rbi", SourceTier.T1, **change)), POLICY)
        assert decision.verdict is Verdict.WITHHOLD
        assert reason in decision.reasons[0]


class TestAttributedViews:
    def test_forecast_needs_an_author(self) -> None:
        claim = Claim(id="f1", claim_type=ClaimType.FORECAST, text="Nifty to reach …",
                      evidence=(article("daily", SourceTier.T2),))
        assert decide(claim, POLICY).verdict is Verdict.WITHHOLD

    def test_attributed_forecast_with_a_page_is_published_as_a_view(self) -> None:
        claim = Claim(id="f2", claim_type=ClaimType.FORECAST, text="Brokerage X expects …",
                      attributed_to="Brokerage X", evidence=(article("daily", SourceTier.T2),))
        assert decide(claim, POLICY).badge is Badge.ATTRIBUTED_VIEW


def test_tolerance_without_bounds_is_exact() -> None:
    assert Tolerance().agrees(Decimal("1.0"), Decimal("1.00"))
    assert not Tolerance().agrees(Decimal("1.0"), Decimal("1.01"))


def test_quotes_longer_than_25_words_are_rejected() -> None:
    with pytest.raises(ValidationError):
        article("daily", SourceTier.T2, quote=" ".join(["word"] * 26))
