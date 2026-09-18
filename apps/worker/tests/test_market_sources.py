from decimal import Decimal

import httpx
import pytest
import respx

from citebell_schemas import Source, SourceKind, SourceTier
from citebell_worker.data.base import DataSourceError
from citebell_worker.pipeline.market_sources import (
    build_coingecko_collectors,
    build_fred_collectors,
    build_market_collect_step,
    build_upstox_collectors,
    find_source,
)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
QUOTES_URL = "https://api.upstox.com/v2/market-quote/quotes"


def fred_source() -> Source:
    return Source(id="fred", name="FRED", domain="fred.stlouisfed.org",
                  tier=SourceTier.T1, kind=SourceKind.API)


def cg_source() -> Source:
    return Source(id="coingecko", name="CoinGecko", domain="coingecko.com",
                   tier=SourceTier.T2, kind=SourceKind.API)


def upstox_source() -> Source:
    return Source(id="upstox", name="Upstox", domain="upstox.com",
                  tier=SourceTier.T2, kind=SourceKind.API)


SOURCES = [fred_source(), cg_source(), upstox_source()]


def test_find_source_returns_the_matching_entry() -> None:
    assert find_source(SOURCES, "fred").id == "fred"


def test_find_source_raises_on_an_unknown_id() -> None:
    with pytest.raises(KeyError, match="dhan"):
        find_source(SOURCES, "dhan")


@respx.mock
def test_build_fred_collectors_fetches_us10y() -> None:
    respx.get(FRED_URL).mock(return_value=httpx.Response(200, json={
        "observations": [{"date": "2026-09-12", "value": "4.08"}],
    }))
    specs = build_fred_collectors(httpx.Client(), "k", fred_source())
    assert [s.name for s in specs] == ["fred.us10y"]
    observations = specs[0].fetch()
    assert len(observations) == 1
    assert observations[0].field == "us10y.yield"
    assert observations[0].evidence.value == Decimal("4.08")


@respx.mock
def test_build_fred_collectors_propagates_connector_errors() -> None:
    respx.get(FRED_URL).mock(return_value=httpx.Response(200, json={"observations": []}))
    specs = build_fred_collectors(httpx.Client(), "k", fred_source())
    with pytest.raises(DataSourceError, match="no observations"):
        specs[0].fetch()


@respx.mock
def test_build_coingecko_collectors_fetches_prices_and_dominance() -> None:
    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json={
        "bitcoin": {"usd": 111000.5, "last_updated_at": 1757930400},
        "ethereum": {"usd": 4300.25, "last_updated_at": 1757930400},
    }))
    respx.get(GLOBAL_URL).mock(return_value=httpx.Response(200, json={
        "data": {"market_cap_percentage": {"btc": 58.42, "eth": 12.1}},
    }))
    specs = build_coingecko_collectors(httpx.Client(), "k", cg_source())
    assert [s.name for s in specs] == ["coingecko.prices", "coingecko.dominance"]
    prices = specs[0].fetch()
    assert {o.field for o in prices} == {"bitcoin.price_usd", "ethereum.price_usd"}
    dominance = specs[1].fetch()
    assert dominance[0].field == "btc.dominance_pct"


def test_build_market_collect_step_returns_none_with_no_keys_configured() -> None:
    step = build_market_collect_step(httpx.Client(), SOURCES, None, None)
    assert step is None


@respx.mock
def test_build_market_collect_step_wires_up_fred_only() -> None:
    respx.get(FRED_URL).mock(return_value=httpx.Response(200, json={
        "observations": [{"date": "2026-09-12", "value": "4.08"}],
    }))
    step = build_market_collect_step(httpx.Client(), SOURCES, "k", None)
    assert step is not None


@respx.mock
def test_build_market_collect_step_wires_up_coingecko_only() -> None:
    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json={
        "bitcoin": {"usd": 111000.5, "last_updated_at": 1757930400},
        "ethereum": {"usd": 4300.25, "last_updated_at": 1757930400},
    }))
    respx.get(GLOBAL_URL).mock(return_value=httpx.Response(200, json={
        "data": {"market_cap_percentage": {"btc": 58.42, "eth": 12.1}},
    }))
    step = build_market_collect_step(httpx.Client(), SOURCES, None, "k")
    assert step is not None


@respx.mock
def test_build_upstox_collectors_fetches_all_four_indices_in_one_call() -> None:
    respx.get(QUOTES_URL).mock(return_value=httpx.Response(200, json={
        "status": "success",
        "data": {
            "NSE_INDEX:Nifty 50": {"instrument_token": "NSE_INDEX|Nifty 50", "last_price": 24850.75},
            "NSE_INDEX:Nifty Bank": {"instrument_token": "NSE_INDEX|Nifty Bank", "last_price": 51000.0},
            "NSE_INDEX:India VIX": {"instrument_token": "NSE_INDEX|India VIX", "last_price": 12.34},
            "BSE_INDEX:SENSEX": {"instrument_token": "BSE_INDEX|SENSEX", "last_price": 81500.5},
        },
    }))
    specs = build_upstox_collectors(httpx.Client(), "token", upstox_source())
    assert [s.name for s in specs] == ["upstox.indices"]
    observations = specs[0].fetch()
    fields = {o.field for o in observations}
    assert fields == {"nifty50.ltp", "banknifty.ltp", "india_vix.ltp", "sensex.ltp"}


@respx.mock
def test_build_upstox_collectors_propagates_connector_errors() -> None:
    respx.get(QUOTES_URL).mock(return_value=httpx.Response(200, json={"status": "error"}))
    specs = build_upstox_collectors(httpx.Client(), "token", upstox_source())
    with pytest.raises(DataSourceError, match="status"):
        specs[0].fetch()


def test_build_market_collect_step_returns_none_when_upstox_token_missing_too() -> None:
    step = build_market_collect_step(httpx.Client(), SOURCES, None, None, None)
    assert step is None


@respx.mock
def test_build_market_collect_step_wires_up_upstox_only() -> None:
    respx.get(QUOTES_URL).mock(return_value=httpx.Response(200, json={
        "status": "success",
        "data": {
            "NSE_INDEX:Nifty 50": {"instrument_token": "NSE_INDEX|Nifty 50", "last_price": 24850.75},
            "NSE_INDEX:Nifty Bank": {"instrument_token": "NSE_INDEX|Nifty Bank", "last_price": 51000.0},
            "NSE_INDEX:India VIX": {"instrument_token": "NSE_INDEX|India VIX", "last_price": 12.34},
            "BSE_INDEX:SENSEX": {"instrument_token": "BSE_INDEX|SENSEX", "last_price": 81500.5},
        },
    }))
    step = build_market_collect_step(httpx.Client(), SOURCES, None, None, "token")
    assert step is not None
