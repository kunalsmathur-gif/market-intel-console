import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

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
from citebell_worker.pipeline.publish import publish_report
from citebell_worker.pipeline.runner import Citation, RenderedSection, RunContext, Section


class FakeCursor:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class FakeConn:
    """Stands in for psycopg.Connection: publish.py only ever calls conn.execute(sql, params)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self._next_id = 100

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        normalized = " ".join(sql.split())
        self.calls.append((normalized, params))
        if "returning id" in normalized:
            row = (self._next_id,)
            self._next_id += 1
            return FakeCursor(row)
        return FakeCursor(None)


def feed_evidence(source_id: str = "nse") -> Evidence:
    return Evidence(
        kind=EvidenceKind.FEED, source_id=source_id, tier=SourceTier.T1,
        url="https://nse.example/data", fetched_at=datetime.now(UTC),
    )


def market_claim(claim_id: str, field: str = "nifty50.close", value: str = "24500") -> Claim:
    return Claim(id=claim_id, claim_type=ClaimType.MARKET_NUMBER, text=f"{field} is {value}",
                field=field, value=Decimal(value), evidence=(feed_evidence(),))


def gated_section(key: str, published: list[Claim], withheld: list[Claim]) -> Section:
    section = Section(key=key, title=key)
    section.claims = [*published, *withheld]
    section.decisions = [
        GateDecision(claim_id=c.id, verdict=Verdict.PUBLISH, badge=Badge.PRIMARY_DATA) for c in published
    ] + [
        GateDecision(claim_id=c.id, verdict=Verdict.WITHHOLD, badge=Badge.WITHHELD, reasons=("stale",))
        for c in withheld
    ]
    return section


def _run_key() -> RunKey:
    return RunKey(report_type=ReportType.MORNING, trading_date=date(2026, 1, 1))


def _context() -> RunContext:
    return RunContext(key=_run_key(), policy=None)  # type: ignore[arg-type]


def test_publish_report_inserts_every_claim_published_or_withheld() -> None:
    published = market_claim("c1")
    withheld = market_claim("c2", field="banknifty.close", value="51000")
    ctx = _context()
    ctx.sections.append(gated_section("market", [published], [withheld]))
    ctx.rendered_sections = []
    conn = FakeConn()

    publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    claim_inserts = [c for sql, c in conn.calls if "insert into public.claims" in sql]
    assert len(claim_inserts) == 2
    inserted_ids = {params[0] for params in claim_inserts}
    assert inserted_ids == {"c1", "c2"}
    withheld_insert = next(p for p in claim_inserts if p[0] == "c2")
    assert withheld_insert[9] == "withhold"  # verdict
    assert withheld_insert[10] == "withheld"  # badge


def test_publish_report_inserts_claim_evidence_for_every_claim() -> None:
    ctx = _context()
    ctx.sections.append(gated_section("market", [market_claim("c1")], []))
    ctx.rendered_sections = []
    conn = FakeConn()

    publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    evidence_inserts = [c for sql, c in conn.calls if "insert into public.claim_evidence" in sql]
    assert len(evidence_inserts) == 1
    assert evidence_inserts[0][0] == "c1"


def test_publish_report_creates_a_report_row_with_the_scheduled_title() -> None:
    ctx = _context()
    ctx.rendered_sections = []
    conn = FakeConn()

    report_id = publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    report_inserts = [(sql, p) for sql, p in conn.calls if "insert into public.reports " in sql]
    assert len(report_inserts) == 1
    _, params = report_inserts[0]
    assert params == (1, "morning", ctx.key.trading_date, ctx.key.version, "Morning Insights")
    assert report_id == 100


def test_publish_report_writes_a_published_section_with_its_body() -> None:
    ctx = _context()
    ctx.rendered_sections = [
        RenderedSection("india_setup_and_flows", "India Setup & Flows", text="Nifty closed at 24500.",
                        citations=(Citation(claim_id="c1", source_id="nse", url="https://nse.example"),)),
    ]
    conn = FakeConn()

    publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    section_inserts = [(sql, p) for sql, p in conn.calls if "insert into public.report_sections" in sql]
    assert len(section_inserts) == 1
    _, params = section_inserts[0]
    assert params[4] == "published"
    body = json.loads(params[5])
    assert body["text"] == "Nifty closed at 24500."
    assert body["citations"] == [{"claim_id": "c1", "source_id": "nse", "url": "https://nse.example"}]
    assert params[6] is None  # withheld_reason


def test_publish_report_writes_a_withheld_section_with_no_body() -> None:
    ctx = _context()
    ctx.rendered_sections = [
        RenderedSection("data_outlook", "Data Outlook", text=None, withheld_reason="no published claims yet"),
    ]
    conn = FakeConn()

    publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    section_inserts = [(sql, p) for sql, p in conn.calls if "insert into public.report_sections" in sql]
    _, params = section_inserts[0]
    assert params[4] == "withheld"
    assert params[5] is None
    assert params[6] == "no published claims yet"


def test_publish_report_links_section_claims_for_each_citation() -> None:
    ctx = _context()
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="A and B.",
                        citations=(Citation(claim_id="c1", source_id="nse", url=None),
                                  Citation(claim_id="c2", source_id="nse", url=None))),
    ]
    conn = FakeConn()

    publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    link_inserts = [p for sql, p in conn.calls if "insert into public.section_claims" in sql]
    assert len(link_inserts) == 2
    assert [p[1] for p in link_inserts] == ["c1", "c2"]
    assert [p[2] for p in link_inserts] == [0, 1]


def test_publish_report_queues_a_report_ready_alert() -> None:
    ctx = _context()
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="Published."),
    ]
    conn = FakeConn()

    report_id = publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    outbox_inserts = [(sql, p) for sql, p in conn.calls if "insert into public.outbox" in sql]
    ready = [p for sql, p in outbox_inserts if "report_ready" in sql]
    assert len(ready) == 1
    dedupe_key, payload = ready[0]
    assert dedupe_key == f"report_ready:morning:{ctx.key.trading_date.isoformat()}:1"
    assert json.loads(payload)["report_id"] == report_id


def test_publish_report_queues_a_section_withheld_alert_per_withheld_section() -> None:
    ctx = _context()
    ctx.rendered_sections = [
        RenderedSection("s1", "Section One", text="Published."),
        RenderedSection("s2", "Section Two", text=None, withheld_reason="no claims"),
    ]
    conn = FakeConn()

    publish_report(conn, ctx, run_id=1)  # type: ignore[arg-type]

    withheld_alerts = [p for sql, p in conn.calls if "section_withheld" in sql and "insert" in sql]
    assert len(withheld_alerts) == 1
    dedupe_key, payload = withheld_alerts[0]
    assert dedupe_key.endswith(":s2")
    assert json.loads(payload)["reason"] == "no claims"
