"""provider_credentials against real Postgres: the owner-only set_provider_credential and
provider_credential_status RPCs, and the worker's credentials.load_credential (PRD §8.5, §9.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest
from conftest import OWNER_EMAIL, OWNER_ID, STRANGER_EMAIL, STRANGER_ID, acting_as, count

from citebell_worker.credentials import CredentialsError, load_credential

FUTURE = datetime.now(UTC) + timedelta(hours=6)
PAST = datetime.now(UTC) - timedelta(hours=1)


def _set(db: psycopg.Connection[Any], token: str, expires_at: datetime, provider: str = "upstox") -> None:
    db.execute("select public.set_provider_credential(%s, %s, %s)", (provider, token, expires_at))


def test_owner_can_set_and_replace_a_credential(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        _set(db, "tok-1", FUTURE)
        _set(db, "tok-2", FUTURE)
    row = db.execute(
        "select access_token from public.provider_credentials where provider = 'upstox'"
    ).fetchone()
    assert row is not None and row[0] == "tok-2"


def test_stranger_cannot_set_a_credential(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, STRANGER_ID, STRANGER_EMAIL), pytest.raises(psycopg.errors.InsufficientPrivilege):
        _set(db, "tok", FUTURE)


def test_no_one_can_select_the_raw_token(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        _set(db, "tok-1", FUTURE)
        assert count(db, "public.provider_credentials") == 0


def test_status_function_reports_expiry_without_the_token(
    db: psycopg.Connection[Any], seeded: dict[str, Any]
) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        _set(db, "tok-1", FUTURE)
        row = db.execute("select * from public.provider_credential_status('upstox')").fetchone()
        assert row is not None
        expires_at, updated_at = row
        assert expires_at is not None
        assert updated_at is not None


def test_status_function_hides_from_a_stranger(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        _set(db, "tok-1", FUTURE)
    with acting_as(db, STRANGER_ID, STRANGER_EMAIL):
        row = db.execute("select * from public.provider_credential_status('upstox')").fetchone()
        assert row is None


def test_load_credential_raises_when_missing(db: psycopg.Connection[Any]) -> None:
    with pytest.raises(CredentialsError, match="no 'upstox' credential"):
        load_credential(db, "upstox")


def test_load_credential_raises_when_expired(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        _set(db, "tok-1", PAST)
    with pytest.raises(CredentialsError, match="expired"):
        load_credential(db, "upstox")


def test_load_credential_returns_the_token(db: psycopg.Connection[Any], seeded: dict[str, Any]) -> None:
    with acting_as(db, OWNER_ID, OWNER_EMAIL):
        _set(db, "tok-1", FUTURE)
    credential = load_credential(db, "upstox")
    assert credential.access_token == "tok-1"
    assert not credential.expired
