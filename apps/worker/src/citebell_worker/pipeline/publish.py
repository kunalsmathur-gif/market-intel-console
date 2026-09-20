"""Publish step (PRD §7 pipeline, §8.8 storage): writes a run's claims and rendered report
sections to Postgres, and queues a report-ready (or section-withheld) alert in the same
transaction so nothing is lost (§8.7 "publishing writes alerts to an outbox table in the same
step").

This is deliberately not a pipeline ``Step`` -- every other step only ever touches ``ctx``, but
publishing needs the run's database connection and row id, which only the caller holding the
queue claim has. Call ``publish_report`` directly after ``run_pipeline`` finishes, and only when
the run actually produced something to publish (status ``PUBLISHED`` or ``PARTIAL``); a
``WITHHELD`` or ``FAILED`` run has nothing here a retry won't redo.

Claims are written even when the gate withheld them -- the audit log needs every reason a claim
didn't make it, not just the ones that did. Report sections only carry a body once published.
PDF and citation-pack generation are a separate, still-unbuilt piece (PRD §8.8 deliverables);
``reports.pdf_path``/``citation_pack_path`` are left null here.
"""

import json
from typing import TYPE_CHECKING, Any

from citebell_schemas import Claim, Evidence, GateDecision

from ..schedule import SCHEDULE
from .runner import RenderedSection, RunContext, Section

if TYPE_CHECKING:
    import psycopg


def _insert_evidence(conn: "psycopg.Connection[Any]", claim_id: str, evidence: Evidence) -> None:
    conn.execute(
        """
        insert into public.claim_evidence
            (claim_id, kind, source_id, tier, url, syndication_group, published_at,
             fetched_at, http_status, quote, quote_found, value, as_of)
        values (%s, %s::public.evidence_kind, %s, %s::public.source_tier, %s, %s, %s,
                %s, %s, %s, %s, %s, %s)
        """,
        (claim_id, evidence.kind.value, evidence.source_id, evidence.tier.value, evidence.url,
         evidence.syndication_group, evidence.published_at, evidence.fetched_at,
         evidence.http_status, evidence.quote, evidence.quote_found, evidence.value,
         evidence.as_of),
    )


def _insert_claim(conn: "psycopg.Connection[Any]", claim: Claim, decision: GateDecision, run_id: int) -> None:
    conn.execute(
        """
        insert into public.claims
            (id, run_id, claim_type, text, field, unit, value, as_of, attributed_to,
             verdict, badge, independent_sources, reasons)
        values (%s, %s, %s::public.claim_type, %s, %s, %s, %s, %s, %s,
                %s::public.verdict, %s::public.badge, %s, %s)
        on conflict (id) do nothing
        """,
        (claim.id, run_id, claim.claim_type.value, claim.text, claim.field, claim.unit,
         claim.value, claim.as_of, claim.attributed_to, decision.verdict.value,
         decision.badge.value, decision.independent_sources, list(decision.reasons)),
    )
    for evidence in claim.evidence:
        _insert_evidence(conn, claim.id, evidence)


def _insert_claims(conn: "psycopg.Connection[Any]", sections: list[Section], run_id: int) -> None:
    """Every claim the gate ever decided on, published or withheld -- the audit trail."""
    for section in sections:
        decisions = {d.claim_id: d for d in section.decisions}
        for claim in section.claims:
            decision = decisions.get(claim.id)
            if decision is not None:
                _insert_claim(conn, claim, decision, run_id)


def _section_body(section: RenderedSection) -> dict[str, Any] | None:
    if section.text is None:
        return None
    return {
        "text": section.text,
        "citations": [
            {"claim_id": c.claim_id, "source_id": c.source_id, "url": c.url}
            for c in section.citations
        ],
    }


def _insert_report_sections(
    conn: "psycopg.Connection[Any]", report_id: int, sections: list[RenderedSection]
) -> None:
    for position, section in enumerate(sections):
        body = _section_body(section)
        row = conn.execute(
            """
            insert into public.report_sections
                (report_id, key, position, title, status, body, withheld_reason)
            values (%s, %s, %s, %s, %s::public.section_status, %s::jsonb, %s)
            returning id
            """,
            (report_id, section.key, position, section.title,
             "published" if body is not None else "withheld",
             json.dumps(body) if body is not None else None, section.withheld_reason),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"insert into report_sections did not return an id for {section.key!r}")
        section_id = int(row[0])
        for claim_position, citation in enumerate(section.citations):
            conn.execute(
                "insert into public.section_claims (section_id, claim_id, position) "
                "values (%s, %s, %s)",
                (section_id, citation.claim_id, claim_position),
            )


def _queue_alerts(conn: "psycopg.Connection[Any]", ctx: RunContext, report_id: int) -> None:
    trading_date = ctx.key.trading_date.isoformat()
    dedupe_prefix = f"{ctx.key.report_type.value}:{trading_date}:{ctx.key.version}"
    conn.execute(
        """
        insert into public.outbox (channel, kind, dedupe_key, payload)
        values ('telegram'::public.alert_channel, 'report_ready'::public.alert_kind, %s, %s::jsonb)
        on conflict (dedupe_key) do nothing
        """,
        (f"report_ready:{dedupe_prefix}",
         json.dumps({"report_id": report_id, "report_type": ctx.key.report_type.value,
                     "trading_date": trading_date})),
    )
    for section in ctx.rendered_sections:
        if section.text is not None:
            continue
        conn.execute(
            """
            insert into public.outbox (channel, kind, dedupe_key, payload)
            values ('telegram'::public.alert_channel, 'section_withheld'::public.alert_kind,
                    %s, %s::jsonb)
            on conflict (dedupe_key) do nothing
            """,
            (f"section_withheld:{dedupe_prefix}:{section.key}",
             json.dumps({"report_id": report_id, "section": section.key,
                        "reason": section.withheld_reason})),
        )


def publish_report(conn: "psycopg.Connection[Any]", ctx: RunContext, run_id: int) -> int:
    """Write this run's claims, rendered sections and alerts. Returns the new report row id.

    Only call this for a run whose ``RunOutcome.status`` is ``PUBLISHED`` or ``PARTIAL`` --
    i.e. ``ctx.rendered_sections`` has at least one published section. The caller should wrap
    this call and the matching ``queue.finish_run`` in one ``conn.transaction()`` block, so a
    crash between the two never leaves a published report whose run row still reads ``running``.
    """
    _insert_claims(conn, ctx.sections, run_id)

    title = SCHEDULE[ctx.key.report_type].title
    row = conn.execute(
        """
        insert into public.reports (run_id, report_type, trading_date, version, title)
        values (%s, %s::public.report_type, %s, %s, %s)
        returning id
        """,
        (run_id, ctx.key.report_type.value, ctx.key.trading_date, ctx.key.version, title),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"insert into reports did not return an id for {ctx.key!r}")
    report_id = int(row[0])

    _insert_report_sections(conn, report_id, ctx.rendered_sections)
    _queue_alerts(conn, ctx, report_id)
    return report_id


__all__ = ["publish_report"]
