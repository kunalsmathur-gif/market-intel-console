from datetime import UTC, date, datetime
from decimal import Decimal

from citebell_schemas import Evidence, EvidenceKind, ReportType, RunKey, SourceTier
from citebell_worker.cli import default_policy
from citebell_worker.data import DataSourceError, Observation
from citebell_worker.pipeline.collect import (
    CollectorSpec,
    collect,
    make_collect_step,
    market_number_claim,
)
from citebell_worker.pipeline.runner import RunContext, Section


def make_observation(field: str, value: str) -> Observation:
    evidence = Evidence(
        kind=EvidenceKind.FEED,
        source_id="fred",
        tier=SourceTier.T1,
        fetched_at=datetime.now(UTC),
        value=Decimal(value),
        as_of=datetime.now(UTC),
    )
    return Observation(field=field, evidence=evidence)


def test_market_number_claim_copies_the_observation_through() -> None:
    obs = make_observation("us10y.yield", "4.08")
    claim = market_number_claim("run:fred:0", obs)
    assert claim.id == "run:fred:0"
    assert claim.field == "us10y.yield"
    assert claim.unit == "percent"
    assert claim.value == Decimal("4.08")
    assert claim.as_of == obs.evidence.as_of
    assert claim.evidence == (obs.evidence,)


def test_market_number_claim_falls_back_to_no_unit_for_unknown_fields() -> None:
    obs = make_observation("mystery.field", "1")
    claim = market_number_claim("run:x:0", obs)
    assert claim.unit is None


def test_market_number_claim_respects_an_explicit_unit_override() -> None:
    obs = make_observation("us10y.yield", "4.08")
    claim = market_number_claim("run:fred:0", obs, unit="custom_unit")
    assert claim.unit == "custom_unit"


def test_collect_runs_every_spec_and_numbers_claims_per_spec() -> None:
    spec = CollectorSpec(name="fred.us10y", fetch=lambda: [make_observation("us10y.yield", "4.08")])
    result = collect([spec], run_id="run1")
    assert [c.id for c in result.claims] == ["run1:fred.us10y:0"]
    assert result.failures == []


def test_collect_withholds_only_the_failing_specs_claims() -> None:
    ok_spec = CollectorSpec(name="fred.us10y", fetch=lambda: [make_observation("us10y.yield", "4.08")])

    def boom() -> list[Observation]:
        raise DataSourceError("connection refused")

    bad_spec = CollectorSpec(name="coingecko.prices", fetch=boom)
    result = collect([ok_spec, bad_spec], run_id="run1")
    assert [c.id for c in result.claims] == ["run1:fred.us10y:0"]
    assert result.failures == ["coingecko.prices: connection refused"]


def test_make_collect_step_creates_a_new_section_when_none_exists() -> None:
    spec = CollectorSpec(name="fred.us10y", fetch=lambda: [make_observation("us10y.yield", "4.08")])
    step = make_collect_step([spec])
    ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
    step(ctx)
    assert [s.key for s in ctx.sections] == ["market"]
    assert len(ctx.sections[0].claims) == 1
    assert ctx.trace == []


def test_make_collect_step_appends_to_an_existing_section() -> None:
    spec = CollectorSpec(name="fred.us10y", fetch=lambda: [make_observation("us10y.yield", "4.08")])
    step = make_collect_step([spec], section_key="market")
    ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
    ctx.sections.append(Section(key="market", title="Market"))
    step(ctx)
    assert len(ctx.sections) == 1
    assert len(ctx.sections[0].claims) == 1


def test_make_collect_step_records_a_trace_entry_only_on_failures() -> None:
    def boom() -> list[Observation]:
        raise DataSourceError("timeout")

    step = make_collect_step([CollectorSpec(name="coingecko.prices", fetch=boom)])
    ctx = RunContext(key=_run_key(), policy=default_policy(datetime.now(UTC)))
    step(ctx)
    assert len(ctx.trace) == 1
    assert ctx.trace[0]["step"] == "collect:failures"
    assert ctx.trace[0]["ok"] is False
    assert "coingecko.prices: timeout" in ctx.trace[0]["detail"]


def _run_key() -> RunKey:
    return RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 1, 1))
