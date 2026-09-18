from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from citebell_worker.credentials import CredentialsError, get_credential_status, load_credential


class FakeCursor:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class FakeConn:
    """Stands in for psycopg.Connection: credentials.py only ever calls conn.execute(...).fetchone()."""

    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def execute(self, _query: str, _params: tuple[Any, ...]) -> FakeCursor:
        return FakeCursor(self._row)


def make_row(*, expired: bool) -> tuple[str, datetime, datetime]:
    now = datetime.now(UTC)
    expires_at = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    return ("secret-token", expires_at, now - timedelta(hours=2))


def test_get_credential_status_returns_none_when_nothing_saved() -> None:
    assert get_credential_status(FakeConn(None), "upstox") is None  # type: ignore[arg-type]


def test_get_credential_status_returns_the_row_even_when_expired() -> None:
    conn = FakeConn(make_row(expired=True))
    credential = get_credential_status(conn, "upstox")  # type: ignore[arg-type]
    assert credential is not None
    assert credential.expired is True
    assert credential.access_token == "secret-token"


def test_get_credential_status_returns_the_row_when_valid() -> None:
    conn = FakeConn(make_row(expired=False))
    credential = get_credential_status(conn, "upstox")  # type: ignore[arg-type]
    assert credential is not None
    assert credential.expired is False


def test_load_credential_raises_when_nothing_saved() -> None:
    with pytest.raises(CredentialsError, match="no 'upstox' credential saved"):
        load_credential(FakeConn(None), "upstox")  # type: ignore[arg-type]


def test_load_credential_raises_when_expired() -> None:
    conn = FakeConn(make_row(expired=True))
    with pytest.raises(CredentialsError, match="expired"):
        load_credential(conn, "upstox")  # type: ignore[arg-type]


def test_load_credential_returns_a_usable_credential_when_valid() -> None:
    conn = FakeConn(make_row(expired=False))
    credential = load_credential(conn, "upstox")  # type: ignore[arg-type]
    assert credential.access_token == "secret-token"
    assert credential.provider == "upstox"
