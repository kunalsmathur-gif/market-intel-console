"""FRED (Federal Reserve Economic Data) API — free, ~120 requests/minute (PRD §8.4 [R18]).

Used for US index closes, the US 10-year yield and US economic data: daily closing
values, not live futures. The source's tier and id come from the private registry
(sources.toml), never hardcoded here, so a re-classification doesn't need a code change.
"""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx

from citebell_schemas import Evidence, EvidenceKind, Source

from .base import DataSourceError, Observation, get_with_retries, require

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
MISSING_VALUE = "."  # FRED's own marker for "no observation on this date"


def latest_observation(
    client: httpx.Client, api_key: str, series_id: str, field: str, source: Source
) -> Observation:
    """Fetch a FRED series' most recent published value (e.g. DGS10, the 10-year yield)."""
    require(source, "api")
    response = get_with_retries(
        client,
        BASE_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": "1",
        },
    )
    payload = response.json()
    observations = payload.get("observations") or []
    if not observations:
        raise DataSourceError(f"FRED series {series_id!r}: no observations returned")

    obs = observations[0]
    raw_value = obs.get("value")
    if raw_value is None or raw_value == MISSING_VALUE:
        raise DataSourceError(f"FRED series {series_id!r}: no value for {obs.get('date')!r}")
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise DataSourceError(f"FRED series {series_id!r}: non-numeric value {raw_value!r}") from exc

    try:
        as_of = datetime.strptime(obs["date"], "%Y-%m-%d").replace(tzinfo=UTC)
    except (KeyError, ValueError) as exc:
        raise DataSourceError(f"FRED series {series_id!r}: bad date {obs.get('date')!r}") from exc

    evidence = Evidence(
        kind=EvidenceKind.FEED,
        source_id=source.id,
        tier=source.tier,
        url=f"https://fred.stlouisfed.org/series/{series_id}",
        fetched_at=datetime.now(UTC),
        value=value,
        as_of=as_of,
    )
    return Observation(field=field, evidence=evidence)
