"""Builds CollectorSpecs for the free V0 connectors (PRD §8.4): FRED and CoinGecko.

Kept separate from collect.py so that module stays connector-agnostic; this one is where
Settings, the source registry and a specific connector call meet. Upstox isn't wired here
yet — its daily access token comes from the database (credentials.load_credential), which
needs a live Postgres connection this factory doesn't have; it's built where that connection
already exists (the scheduler's run loop), not as a plain CollectorSpec list.
"""

from collections.abc import Sequence

import httpx

from citebell_schemas import Source

from ..data import btc_dominance, fred_latest_observation, simple_prices
from .collect import CollectorSpec, make_collect_step
from .runner import Step

US10Y_SERIES_ID = "DGS10"


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


def find_source(sources: Sequence[Source], source_id: str) -> Source:
    for source in sources:
        if source.id == source_id:
            return source
    raise KeyError(f"no source {source_id!r} in the registry")


def build_market_collect_step(
    client: httpx.Client, sources: Sequence[Source], fred_api_key: str | None, coingecko_api_key: str | None
) -> Step | None:
    """Wire up every free connector whose API key is configured; None if neither is set."""
    specs: list[CollectorSpec] = []
    if fred_api_key:
        specs += build_fred_collectors(client, fred_api_key, find_source(sources, "fred"))
    if coingecko_api_key:
        specs += build_coingecko_collectors(client, coingecko_api_key, find_source(sources, "coingecko"))
    if not specs:
        return None
    return make_collect_step(specs)

