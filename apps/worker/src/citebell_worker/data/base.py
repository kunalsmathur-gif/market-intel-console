"""Shared HTTP conventions for the data connectors (PRD §8.4).

Every connector does a real fetch and raises on anything it can't make sense of — no
cached or invented numbers. A step that can't collect a value should withhold that
claim, not publish a stale or guessed one.
"""

import time
from dataclasses import dataclass

import httpx

from citebell_schemas import Evidence, Source

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
DEFAULT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0


class DataSourceError(RuntimeError):
    """A connector's fetch failed, or the response wasn't usable."""


@dataclass(frozen=True)
class Observation:
    """A single dated value from a data feed, ready to match against a claim (PRD §7 collect step)."""

    field: str
    evidence: Evidence


def get_with_retries(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    retries: int = DEFAULT_RETRIES,
) -> httpx.Response:
    """GET with a small retry budget; the last error (transport or non-200) is raised."""
    last_exc: DataSourceError | None = None
    for attempt in range(retries + 1):
        try:
            response = client.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        except httpx.HTTPError as exc:
            last_exc = DataSourceError(f"GET {url}: {exc!r}")
        else:
            if response.status_code == 200:
                return response
            last_exc = DataSourceError(f"GET {url}: HTTP {response.status_code}: {response.text[:200]}")
        if attempt < retries:
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    assert last_exc is not None  # retries is >= 0, so the loop always sets this before exiting
    raise last_exc


def require(source: Source, expected_kind: str) -> None:
    """A small guard so a connector fails loudly if wired to the wrong registry entry."""
    if source.kind != expected_kind:
        raise DataSourceError(
            f"source {source.id!r} is kind={source.kind!r}, expected {expected_kind!r}"
        )
