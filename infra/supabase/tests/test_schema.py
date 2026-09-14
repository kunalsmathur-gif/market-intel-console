"""Schema rules: RLS everywhere, append-only history, constraints, and enums that match Python."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import psycopg
import pytest
from conftest import count

from citebell_schemas import (
    MAX_QUOTE_WORDS,
    Badge,
    ClaimType,
    EvidenceKind,
    ReportType,
    RunStatus,
    SourceKind,
    SourceTier,
    Verdict,
)


def test_every_public_table_has_row_level_security(db: psycopg.Connection[Any]) -> None:
    rows = db.execute(
        "select tablename from pg_tables where schemaname = 'public' and not rowsecurity"
    ).fetchall()
    assert rows == []


@pytest.mark.parametrize(
    ("pg_enum", "py_enum"),
    [
        ("report_type", ReportType),
        ("source_tier", SourceTier),
        ("source_kind", SourceKind),
        ("evidence_kind", EvidenceKind),
        ("claim_type", ClaimType),
        ("badge", Badge),
        ("verdict", Verdict),
        ("run_status", RunStatus),
    ],
)
def test_database_enums_match_the_python_schemas(
    db: psycopg.Connection[Any], pg_enum: str, py_enum: type[StrEnum]
) -> None:
    labels = db.execute(
        """select e.enumlabel from pg_enum e join pg_type t on t.oid = e.enumtypid
           where t.typname = %s order by e.enumsortorder""",
        (pg_enum,),
    ).fetchall()
    assert [label for (label,) in labels] == [member.value for member in py_enum]


@pytest.mark.parametrize(
    "statement", ["update public.claims set text = 'edited'", "delete from public.claims"]
)
def test_claims_are_append_only(
    db: psycopg.Connection[Any], seeded: dict[str, Any], statement: str
) -> None:
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        db.execute(statement)


def test_market_facts_evidence_and_corrections_are_append_only(
    db: psycopg.Connection[Any], seeded: dict[str, Any]
) -> None:
    db.execute(
        """insert into public.market_facts (run_id, field, value, unit, as_of, source_id)
           values (%s, 'nifty50.close', 25100.5, 'index_points', now(), 'rbi')""",
        (seeded["run_id"],),
    )
    db.execute(
        """insert into public.claim_evidence (claim_id, kind, source_id, tier, fetched_at)
           values ('c1', 'feed', 'rbi', 'T1', now())"""
    )
    db.execute(
        "insert into public.corrections (claim_id, report_id, reason) values ('c1', %s, 'test')",
        (seeded["report_id"],),
    )
    for table in ("market_facts", "claim_evidence", "corrections"):
        with pytest.raises(psycopg.errors.RaiseException):
            db.execute(f"delete from public.{table}")


def test_verdict_and_badge_must_agree(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            """insert into public.claims (id, run_id, claim_type, text, verdict, badge)
               values ('c2', %s, 'news_event', 'x', 'withhold', 'verified')""",
            (seeded["run_id"],),
        )


def test_quote_limit_matches_the_python_schema(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    insert = """insert into public.claim_evidence (claim_id, kind, source_id, tier, fetched_at, quote)
                values ('c1', 'article', 'rbi', 'T1', now(), %s)"""
    db.execute(insert, (" ".join(["word"] * MAX_QUOTE_WORDS),))
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(insert, (" ".join(["word"] * (MAX_QUOTE_WORDS + 1)),))


def test_sections_need_a_body_or_a_withheld_reason(
    db: psycopg.Connection[Any], seeded: dict[str, Any]
) -> None:
    insert = """insert into public.report_sections
                  (report_id, key, position, title, status, body, withheld_reason)
                values (%s, %s, 0, 'Section', %s, %s, %s)"""
    report = seeded["report_id"]
    db.execute(insert, (report, "ok-published", "published", "[]", None))
    db.execute(insert, (report, "ok-withheld", "withheld", None, "Upstox login needed"))
    for key, status, body, reason in [
        ("bad-1", "withheld", None, None),
        ("bad-2", "withheld", "[]", "reason"),
        ("bad-3", "published", None, None),
    ]:
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute(insert, (report, key, status, body, reason))


def test_outbox_never_holds_the_same_alert_twice(db: psycopg.Connection[Any]) -> None:
    insert = """insert into public.outbox (channel, kind, dedupe_key, payload)
                values ('telegram', 'report_ready', 'morning:2026-09-15:1', '{}')"""
    db.execute(insert)
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(insert)
    assert count(db, "public.outbox") == 1


def test_private_storage_buckets_exist(db: psycopg.Connection[Any]) -> None:
    rows = db.execute("select id, public from storage.buckets order by id").fetchall()
    assert rows == [("reports", False), ("uploads", False)]
