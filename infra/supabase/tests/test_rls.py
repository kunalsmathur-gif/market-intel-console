"""Owner-only access: what the web app's signed-in roles can and can't do."""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from conftest import OWNER_EMAIL, OWNER_ID, STRANGER_EMAIL, STRANGER_ID, acting_as, count

READABLE_BY_OWNER = ["public.reports", "public.claims", "public.report_runs", "public.sources"]
WORKER_ONLY = ["public.outbox", "public.allowed_users", "public.raw_responses"]


def test_owner_reads_published_data(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        assert all(count(db, table) >= 1 for table in READABLE_BY_OWNER)


def test_owner_email_match_ignores_case(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, "Owner@Example.COM"):
        assert count(db, "public.reports") == 1


def test_worker_only_tables_are_hidden_from_the_owner(
    db: psycopg.Connection[Any], seeded: dict[str, Any]
) -> None:
    db.execute(
        """insert into public.outbox (channel, kind, dedupe_key, payload)
           values ('telegram', 'report_ready', 'k', '{}')"""
    )
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        assert [count(db, table) for table in WORKER_ONLY] == [0, 0, 0]


def test_owner_can_flag_a_claim_as_themselves(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        db.execute("insert into public.claim_flags (claim_id, note) values ('c1', 'number looks wrong')")
        assert count(db, "public.claim_flags") == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(
                "insert into public.claim_flags (claim_id, user_id) values ('c1', %s)", (STRANGER_ID,)
            )


def test_flags_are_visible_only_to_their_author(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    db.execute("insert into public.claim_flags (claim_id, user_id) values ('c1', %s)", (STRANGER_ID,))
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        assert count(db, "public.claim_flags") == 0


def test_owner_cannot_write_published_data(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL), pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(
            """insert into public.reports (run_id, report_type, trading_date, version, title)
               values (%s, 'eod', '2026-09-15', 1, 'x')""",
            (seeded["run_id"],),
        )


def test_signed_in_stranger_sees_and_flags_nothing(
    db: psycopg.Connection[Any], seeded: dict[str, Any]
) -> None:
    with acting_as(db, STRANGER_ID, STRANGER_EMAIL):
        assert [count(db, table) for table in READABLE_BY_OWNER] == [0, 0, 0, 0]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute("insert into public.claim_flags (claim_id) values ('c1')")


def test_anonymous_visitor_sees_nothing(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, None):
        assert [count(db, table) for table in READABLE_BY_OWNER] == [0, 0, 0, 0]


def test_is_owner_function(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    def is_owner() -> bool:
        row = db.execute("select public.is_owner()").fetchone()
        return bool(row and row[0])

    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        assert is_owner()
    with acting_as(db, STRANGER_ID, STRANGER_EMAIL):
        assert not is_owner()
    with acting_as(db, None):
        assert not is_owner()
