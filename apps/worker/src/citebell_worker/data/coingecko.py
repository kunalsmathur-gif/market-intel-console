"""CoinGecko Demo API — free key, 10,000 calls/month; a report uses ~4–10 (PRD §8.4 [R21]).

Used for Bitcoin, Ethereum and dominance. This connector only fetches CoinGecko's own
value; cross-checking it against a second exchange price happens in the gate, not here.
"""

from datetime import UTC, datetime
from decimal import Decimal

import httpx

from citebell_schemas import Evidence, EvidenceKind, Source

from .base import DataSourceError, Observation, get_with_retries, require

BASE_URL = "https://api.coingecko.com/api/v3"
DEFAULT_COINS = ("bitcoin", "ethereum")


def simple_prices(
    client: httpx.Client,
    api_key: str,
    source: Source,
    *,
    coins: tuple[str, ...] = DEFAULT_COINS,
    vs_currency: str = "usd",
) -> list[Observation]:
    """Fetch the current price of each coin, e.g. field ``bitcoin.price_usd``."""
    require(source, "api")
    response = get_with_retries(
        client,
        f"{BASE_URL}/simple/price",
        params={
            "ids": ",".join(coins),
            "vs_currencies": vs_currency,
            "include_last_updated_at": "true",
        },
        headers={"x-cg-demo-api-key": api_key},
    )
    payload = response.json()
    fetched_at = datetime.now(UTC)
    observations = []
    for coin_id in coins:
        entry = payload.get(coin_id)
        if not entry or vs_currency not in entry:
            raise DataSourceError(f"CoinGecko: missing {vs_currency!r} price for {coin_id!r}")
        as_of_epoch = entry.get("last_updated_at")
        as_of = datetime.fromtimestamp(as_of_epoch, tz=UTC) if as_of_epoch else fetched_at
        evidence = Evidence(
            kind=EvidenceKind.FEED,
            source_id=source.id,
            tier=source.tier,
            url=f"https://www.coingecko.com/en/coins/{coin_id}",
            fetched_at=fetched_at,
            value=Decimal(str(entry[vs_currency])),
            as_of=as_of,
        )
        observations.append(Observation(field=f"{coin_id}.price_{vs_currency}", evidence=evidence))
    return observations


def btc_dominance(client: httpx.Client, api_key: str, source: Source) -> Observation:
    """Bitcoin's share of total crypto market cap, as a percentage."""
    require(source, "api")
    response = get_with_retries(
        client, f"{BASE_URL}/global", headers={"x-cg-demo-api-key": api_key}
    )
    data = response.json().get("data") or {}
    pct = (data.get("market_cap_percentage") or {}).get("btc")
    if pct is None:
        raise DataSourceError("CoinGecko: missing btc share in /global market_cap_percentage")
    fetched_at = datetime.now(UTC)
    evidence = Evidence(
        kind=EvidenceKind.FEED,
        source_id=source.id,
        tier=source.tier,
        url="https://www.coingecko.com/en/global-charts",
        fetched_at=fetched_at,
        value=Decimal(str(pct)),
        as_of=fetched_at,
    )
    return Observation(field="btc.dominance_pct", evidence=evidence)
