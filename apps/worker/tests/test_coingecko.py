from decimal import Decimal

import httpx
import pytest
import respx

from citebell_schemas import Source, SourceKind, SourceTier
from citebell_worker.data.base import DataSourceError
from citebell_worker.data.coingecko import btc_dominance, simple_prices

PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
GLOBAL_URL = "https://api.coingecko.com/api/v3/global"


def cg_source(**kw: object) -> Source:
    fields: dict[str, object] = {
        "id": "coingecko", "name": "CoinGecko", "domain": "coingecko.com",
        "tier": SourceTier.T2, "kind": SourceKind.API,
    }
    return Source.model_validate(fields | kw)


@respx.mock
def test_simple_prices_returns_one_observation_per_coin() -> None:
    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json={
        "bitcoin": {"usd": 111000.5, "last_updated_at": 1757930400},
        "ethereum": {"usd": 4300.25, "last_updated_at": 1757930400},
    }))
    observations = simple_prices(httpx.Client(), "k", cg_source())
    fields = {o.field: o.evidence.value for o in observations}
    assert fields == {"bitcoin.price_usd": Decimal("111000.5"), "ethereum.price_usd": Decimal("4300.25")}
    assert all(o.evidence.tier is SourceTier.T2 for o in observations)


@respx.mock
def test_simple_prices_raises_when_a_coin_is_missing() -> None:
    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json={"bitcoin": {"usd": 111000.5}}))
    with pytest.raises(DataSourceError, match="ethereum"):
        simple_prices(httpx.Client(), "k", cg_source())


@respx.mock
def test_btc_dominance_reads_market_cap_percentage() -> None:
    respx.get(GLOBAL_URL).mock(return_value=httpx.Response(200, json={
        "data": {"market_cap_percentage": {"btc": 58.42, "eth": 12.1}},
    }))
    obs = btc_dominance(httpx.Client(), "k", cg_source())
    assert obs.field == "btc.dominance_pct"
    assert obs.evidence.value == Decimal("58.42")


@respx.mock
def test_btc_dominance_raises_when_missing() -> None:
    respx.get(GLOBAL_URL).mock(return_value=httpx.Response(200, json={"data": {}}))
    with pytest.raises(DataSourceError, match="btc share"):
        btc_dominance(httpx.Client(), "k", cg_source())
