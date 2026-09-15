from decimal import Decimal

import httpx
import pytest
import respx

from citebell_schemas import Source, SourceKind, SourceTier
from citebell_worker.data.base import DataSourceError
from citebell_worker.data.fred import latest_observation

URL = "https://api.stlouisfed.org/fred/series/observations"


def fred_source(**kw: object) -> Source:
    fields: dict[str, object] = {
        "id": "fred", "name": "FRED", "domain": "fred.stlouisfed.org",
        "tier": SourceTier.T1, "kind": SourceKind.API,
    }
    return Source.model_validate(fields | kw)


@respx.mock
def test_latest_observation_parses_the_most_recent_value() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={
        "observations": [{"date": "2026-09-12", "value": "4.08"}],
    }))
    obs = latest_observation(httpx.Client(), "k", "DGS10", "us_10y_yield", fred_source())
    assert obs.field == "us_10y_yield"
    assert obs.evidence.value == Decimal("4.08")
    assert obs.evidence.source_id == "fred"
    assert obs.evidence.tier is SourceTier.T1
    assert obs.evidence.as_of is not None
    assert obs.evidence.as_of.isoformat().startswith("2026-09-12")


@respx.mock
def test_latest_observation_rejects_the_missing_value_marker() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={
        "observations": [{"date": "2026-09-12", "value": "."}],
    }))
    with pytest.raises(DataSourceError, match="no value"):
        latest_observation(httpx.Client(), "k", "DGS10", "us_10y_yield", fred_source())


@respx.mock
def test_latest_observation_rejects_empty_series() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={"observations": []}))
    with pytest.raises(DataSourceError, match="no observations"):
        latest_observation(httpx.Client(), "k", "DGS10", "us_10y_yield", fred_source())


def test_latest_observation_requires_an_api_source() -> None:
    rss_source = fred_source(kind=SourceKind.RSS, url="https://fred.example/rss")
    with pytest.raises(DataSourceError, match="expected 'api'"):
        latest_observation(httpx.Client(), "k", "DGS10", "field", rss_source)
