from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
import respx

from citebell_schemas import Evidence, EvidenceKind, Source, SourceKind, SourceTier
from citebell_worker.data.base import DataSourceError, Observation, get_with_retries, require

URL = "https://api.example/data"


def api_source(**kw: object) -> Source:
    fields: dict[str, object] = {
        "id": "example-api", "name": "Example API", "domain": "api.example",
        "tier": SourceTier.T1, "kind": SourceKind.API,
    }
    return Source.model_validate(fields | kw)


@respx.mock
def test_get_with_retries_returns_first_success() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    response = get_with_retries(httpx.Client(), URL)
    assert response.json() == {"ok": True}
    assert route.call_count == 1


@respx.mock
def test_get_with_retries_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("citebell_worker.data.base.time.sleep", lambda _seconds: None)
    route = respx.get(URL).mock(return_value=httpx.Response(503, text="down"))
    with pytest.raises(DataSourceError, match="503"):
        get_with_retries(httpx.Client(), URL, retries=2)
    assert route.call_count == 3


@respx.mock
def test_get_with_retries_recovers_after_a_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("citebell_worker.data.base.time.sleep", lambda _seconds: None)
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(500, text="boom"), httpx.Response(200, json={"ok": True})]
    )
    response = get_with_retries(httpx.Client(), URL, retries=2)
    assert response.json() == {"ok": True}
    assert route.call_count == 2


def test_get_with_retries_wraps_transport_errors() -> None:
    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    transport = httpx.MockTransport(raise_connect_error)
    with pytest.raises(DataSourceError, match="refused"):
        get_with_retries(httpx.Client(transport=transport), URL, retries=0)


def test_require_passes_for_matching_kind() -> None:
    require(api_source(), "api")


def test_require_rejects_wrong_kind() -> None:
    with pytest.raises(DataSourceError, match="expected 'rss'"):
        require(api_source(), "rss")


def test_observation_wraps_evidence() -> None:
    evidence = Evidence(
        kind=EvidenceKind.FEED, source_id="example-api", tier=SourceTier.T1,
        fetched_at=datetime(2026, 9, 15, tzinfo=UTC), value=Decimal("1.5"),
        as_of=datetime(2026, 9, 15, tzinfo=UTC),
    )
    obs = Observation(field="x.y", evidence=evidence)
    assert obs.field == "x.y"
    assert obs.evidence.value == Decimal("1.5")
