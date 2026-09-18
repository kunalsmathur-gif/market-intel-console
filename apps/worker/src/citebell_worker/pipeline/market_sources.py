"""Builds CollectorSpecs for the V0 connectors (PRD §8.4): FRED, CoinGecko, and Upstox.

Kept separate from collect.py so that module stays connector-agnostic; this one is where
Settings, the source registry and a specific connector call meet. Upstox's collectors take
an already-resolved access token, not a database connection — the caller (the scheduler's
run loop) reads the owner's daily token via `credentials.load_credential` first, since that
needs a live Postgres connection this module doesn't hold.
"""

from collections.abc import Sequence

import httpx

from citebell_schemas import Source

from ..data import btc_dominance, fred_latest_observation, simple_prices, upstox_quotes
from .collect import CollectorSpec, make_collect_step
from .runner import Step

US10Y_SERIES_ID = "DGS10"

# instrument_key -> claim field, for the index LTPs V0 needs (PRD §8.4). Bank Nifty and
# Sensex use their own exchange-prefixed keys, not the "NSE_INDEX|Nifty 50" shape's twin.
UPSTOX_INDEX_INSTRUMENTS: tuple[tuple[str, str], ...] = (
    ("NSE_INDEX|Nifty 50", "nifty50.ltp"),
    ("NSE_INDEX|Nifty Bank", "banknifty.ltp"),
    ("NSE_INDEX|India VIX", "india_vix.ltp"),
    ("BSE_INDEX|SENSEX", "sensex.ltp"),
)


def build_fred_collectors(client: httpx.Client, api_key: str, source: Source) -> list[CollectorSpec]:
    """US 10-year Treasury yield — one collector, one Observation (PRD §8.4)."""
    return [
        CollectorSpec(
            name="fred.us10y",
            fetch=lambda: [
                fred_latest_observation(client, api_key, US10Y_SERIES_ID, "us10y.yield", source)
            ],
        )
    ]


def build_coingecko_collectors(
    client: httpx.Client, api_key: str, source: Source
) -> list[CollectorSpec]:
    """Bitcoin, Ethereum and BTC dominance (PRD §8.4). A second exchange price is still needed
    before these can clear the gate on their own — CoinGecko alone is a single source."""
    return [
        CollectorSpec(name="coingecko.prices", fetch=lambda: simple_prices(client, api_key, source)),
        CollectorSpec(name="coingecko.dominance", fetch=lambda: [btc_dominance(client, api_key, source)]),
    ]


def build_upstox_collectors(
    client: httpx.Client, access_token: str, source: Source
) -> list[CollectorSpec]:
    """The four index LTPs V0 needs (PRD §8.4): Nifty 50, Bank Nifty, India VIX, Sensex.

    One `quotes()` call batches all four instruments, so this is a single CollectorSpec —
    if Upstox is unreachable, all four index claims are withheld together, which is the
    right blast radius for a single API call.
    """
    instrument_keys, fields = zip(*UPSTOX_INDEX_INSTRUMENTS, strict=True)
    return [
        CollectorSpec(
            name="upstox.indices",
            fetch=lambda: upstox_quotes(client, access_token, instrument_keys, fields, source),
        )
    ]


def find_source(sources: Sequence[Source], source_id: str) -> Source:
    for source in sources:
        if source.id == source_id:
            return source
    raise KeyError(f"no source {source_id!r} in the registry")


def build_market_collect_step(
    client: httpx.Client,
    sources: Sequence[Source],
    fred_api_key: str | None,
    coingecko_api_key: str | None,
    upstox_access_token: str | None = None,
) -> Step | None:
    """Wire up every connector with credentials available; None if none are."""
    specs: list[CollectorSpec] = []
    if fred_api_key:
        specs += build_fred_collectors(client, fred_api_key, find_source(sources, "fred"))
    if coingecko_api_key:
        specs += build_coingecko_collectors(client, coingecko_api_key, find_source(sources, "coingecko"))
    if upstox_access_token:
        specs += build_upstox_collectors(client, upstox_access_token, find_source(sources, "upstox"))
    if not specs:
        return None
    return make_collect_step(specs)

