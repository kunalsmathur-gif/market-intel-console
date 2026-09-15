from decimal import Decimal

import httpx
import pytest
import respx

from citebell_schemas import Source, SourceKind, SourceTier
from citebell_worker.data.base import DataSourceError
from citebell_worker.data.upstox import option_chain, quotes

QUOTES_URL = "https://api.upstox.com/v2/market-quote/quotes"
CHAIN_URL = "https://api.upstox.com/v2/option/chain"


def upstox_source(**kw: object) -> Source:
    fields: dict[str, object] = {
        "id": "upstox", "name": "Upstox", "domain": "upstox.com",
        "tier": SourceTier.T2, "kind": SourceKind.API,
    }
    return Source.model_validate(fields | kw)


@respx.mock
def test_quotes_returns_one_observation_per_instrument() -> None:
    respx.get(QUOTES_URL).mock(return_value=httpx.Response(200, json={
        "status": "success",
        "data": {
            "NSE_INDEX:Nifty 50": {
                "instrument_token": "NSE_INDEX|Nifty 50",
                "last_price": 24850.75,
                "last_trade_time": "2026-09-15T15:30:00+05:30",
            },
            "NSE_INDEX:India VIX": {
                "instrument_token": "NSE_INDEX|India VIX",
                "last_price": 12.34,
                "last_trade_time": "2026-09-15T15:30:00+05:30",
            },
        },
    }))
    observations = quotes(
        httpx.Client(),
        "token",
        ("NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX"),
        ("nifty50.ltp", "india_vix.ltp"),
        upstox_source(),
    )
    fields = {o.field: o.evidence.value for o in observations}
    assert fields == {"nifty50.ltp": Decimal("24850.75"), "india_vix.ltp": Decimal("12.34")}
    assert all(o.evidence.tier is SourceTier.T2 for o in observations)


@respx.mock
def test_quotes_raises_when_an_instrument_is_missing() -> None:
    respx.get(QUOTES_URL).mock(return_value=httpx.Response(200, json={
        "status": "success",
        "data": {"NSE_INDEX:Nifty 50": {"instrument_token": "NSE_INDEX|Nifty 50", "last_price": 24850.75}},
    }))
    with pytest.raises(DataSourceError, match="India VIX"):
        quotes(
            httpx.Client(),
            "token",
            ("NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX"),
            ("nifty50.ltp", "india_vix.ltp"),
            upstox_source(),
        )


@respx.mock
def test_quotes_raises_on_non_success_status() -> None:
    respx.get(QUOTES_URL).mock(return_value=httpx.Response(200, json={"status": "error"}))
    with pytest.raises(DataSourceError, match="status"):
        quotes(httpx.Client(), "token", ("NSE_INDEX|Nifty 50",), ("nifty50.ltp",), upstox_source())


def test_quotes_rejects_mismatched_keys_and_fields() -> None:
    with pytest.raises(DataSourceError, match="1:1"):
        quotes(httpx.Client(), "token", ("a", "b"), ("only_one",), upstox_source())


@respx.mock
def test_option_chain_parses_strikes() -> None:
    respx.get(CHAIN_URL).mock(return_value=httpx.Response(200, json={
        "status": "success",
        "data": [
            {
                "strike_price": 24800,
                "call_options": {"market_data": {"oi": 123456, "ltp": 210.5, "volume": 5000}},
                "put_options": {"market_data": {"oi": 98765, "ltp": 150.25, "volume": 4200}},
            },
            {
                "strike_price": 24900,
                "call_options": {"market_data": {"oi": 111, "ltp": 160.0, "volume": 3000}},
                "put_options": {"market_data": {}},
            },
        ],
    }))
    snapshot = option_chain(httpx.Client(), "token", "NSE_INDEX|Nifty 50", "2026-09-25", upstox_source())
    assert snapshot.underlying_key == "NSE_INDEX|Nifty 50"
    assert len(snapshot.strikes) == 2
    first = snapshot.strikes[0]
    assert first.strike == Decimal("24800")
    assert first.call_oi == 123456
    assert first.put_ltp == Decimal("150.25")
    second = snapshot.strikes[1]
    assert second.put_oi is None
    assert second.put_ltp is None


@respx.mock
def test_option_chain_raises_when_empty() -> None:
    respx.get(CHAIN_URL).mock(return_value=httpx.Response(200, json={"status": "success", "data": []}))
    with pytest.raises(DataSourceError, match="no strikes"):
        option_chain(httpx.Client(), "token", "NSE_INDEX|Nifty 50", "2026-09-25", upstox_source())


@respx.mock
def test_option_chain_raises_on_non_success_status() -> None:
    respx.get(CHAIN_URL).mock(return_value=httpx.Response(200, json={"status": "error"}))
    with pytest.raises(DataSourceError, match="status"):
        option_chain(httpx.Client(), "token", "NSE_INDEX|Nifty 50", "2026-09-25", upstox_source())
