from datetime import UTC, datetime, time, timedelta
from typing import Any

from citebell_worker.cli import _time_minus_minutes, _upstox_status_message


class FakeCursor:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class FakeConn:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def execute(self, _query: str, _params: tuple[Any, ...]) -> FakeCursor:
        return FakeCursor(self._row)


def make_row(*, expired: bool) -> tuple[str, datetime, datetime]:
    now = datetime.now(UTC)
    expires_at = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    return ("secret-token", expires_at, now - timedelta(hours=2))


def test_time_minus_minutes_crosses_the_hour_boundary() -> None:
    assert _time_minus_minutes(time(8, 15), 45) == time(7, 30)


def test_time_minus_minutes_within_the_hour() -> None:
    assert _time_minus_minutes(time(7, 30), 15) == time(7, 15)


def test_upstox_status_message_when_nothing_saved() -> None:
    assert "not connected" in _upstox_status_message(FakeConn(None))  # type: ignore[arg-type]


def test_upstox_status_message_when_expired() -> None:
    conn = FakeConn(make_row(expired=True))
    message = _upstox_status_message(conn)  # type: ignore[arg-type]
    assert "expired" in message


def test_upstox_status_message_when_valid() -> None:
    conn = FakeConn(make_row(expired=False))
    message = _upstox_status_message(conn)  # type: ignore[arg-type]
    assert "valid until" in message
