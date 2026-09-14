from datetime import UTC, date, datetime, timedelta

from citebell_schemas import (
    Claim,
    ClaimType,
    Evidence,
    EvidenceKind,
    ReportType,
    RunKey,
    RunStatus,
    SourceTier,
)
from citebell_worker.pipeline.gate import GatePolicy
from citebell_worker.pipeline.runner import V0_STEPS, RunContext, Section, run_pipeline

NOW = datetime(2026, 9, 15, 2, 45, tzinfo=UTC)


def context() -> RunContext:
    return RunContext(key=RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 9, 15)),
                      policy=GatePolicy(now=NOW, stale_before=NOW - timedelta(hours=24)))


def verified_event() -> Claim:
    evidence = Evidence(kind=EvidenceKind.ARTICLE, source_id="rbi", tier=SourceTier.T1,
                        url="https://rbi.example/press", fetched_at=NOW, http_status=200,
                        published_at=NOW - timedelta(hours=2), quote_found=True)
    return Claim(id="e1", claim_type=ClaimType.NEWS_EVENT, text="…", evidence=(evidence,))


def test_a_run_with_nothing_to_publish_is_withheld() -> None:
    outcome = run_pipeline(context())
    assert outcome.status is RunStatus.WITHHELD
    assert [record["step"] for record in outcome.trace] == ["gate"]


def test_sections_that_pass_publish_and_the_rest_make_it_partial() -> None:
    ctx = context()
    unsupported = Claim(id="e2", claim_type=ClaimType.NEWS_EVENT, text="rumour")
    ctx.sections = [Section("domestic_triggers", "Domestic triggers", [verified_event()]),
                    Section("geopolitics", "Geopolitics", [unsupported])]
    assert run_pipeline(ctx).status is RunStatus.PARTIAL


def test_a_failing_step_fails_the_run_and_is_traced() -> None:
    def broken(_: RunContext) -> None:
        raise TimeoutError("feed timed out")

    outcome = run_pipeline(context(), [("collect", broken), *V0_STEPS])
    assert outcome.status is RunStatus.FAILED
    assert outcome.trace[-1]["ok"] is False
    assert "collect" in (outcome.error or "")
