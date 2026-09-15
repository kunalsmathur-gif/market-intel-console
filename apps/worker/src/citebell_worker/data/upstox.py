"""Upstox v2 market-data API — indices, VIX and index option chains (PRD §8.4, §9.3).

The daily access token is not read from an env var: it expires at 03:30 IST every day
with no refresh token (PRD §9.3 [R42]), so the owner pastes a fresh one into the web
app's Settings page each morning and the worker reads it via `credentials.py`. This
connector only takes the token as a plain string parameter — it has no idea how the
token was obtained or stored.

Field names below (``last_price``, ``call_options``/``put_options``, ``market_data``,
``option_greeks``) follow Upstox's public v2 docs as of this writing but were not
verified against a live account in this session — treat a `DataSourceError` here as a
signal to re-check the current API response shape, not necessarily a real outage.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from citebell_schemas import Evidence, EvidenceKind, Source

from .base import DataSourceError, Observation, get_with_retries, require

BASE_URL = "https://api.upstox.com/v2"


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}


def quotes(
    client: httpx.Client,
    access_token: str,
    instrument_keys: tuple[str, ...],
    fields: tuple[str, ...],
    source: Source,
) -> list[Observation]:
    """Batched last-traded-price fetch, e.g. for NIFTY 50 / BANK NIFTY / INDIA VIX.

    ``instrument_keys`` and ``fields`` line up positionally: fetching one instrument's
    LTP for two output fields is two calls of this function, not one, to keep the
    field-to-registry-entry mapping unambiguous, matching the FRED/CoinGecko connectors.
    """
    require(source, "api")
    if len(instrument_keys) != len(fields):
        raise DataSourceError("upstox.quotes: instrument_keys and fields must line up 1:1")
    response = get_with_retries(
        client,
        f"{BASE_URL}/market-quote/quotes",
        params={"instrument_key": ",".join(instrument_keys)},
        headers=_auth_headers(access_token),
    )
    payload = response.json()
    if payload.get("status") != "success":
        raise DataSourceError(f"Upstox quotes: status={payload.get('status')!r}")
    quote_data = payload.get("data") or {}
    fetched_at = datetime.now(UTC)
    observations = []
    for instrument_key, field in zip(instrument_keys, fields, strict=True):
        entry = _find_quote(quote_data, instrument_key)
        if entry is None:
            raise DataSourceError(f"Upstox quotes: no data for {instrument_key!r}")
        last_price = entry.get("last_price")
        if last_price is None:
            raise DataSourceError(f"Upstox quotes: missing last_price for {instrument_key!r}")
        as_of = _parse_trade_time(entry.get("last_trade_time")) or fetched_at
        evidence = Evidence(
            kind=EvidenceKind.FEED,
            source_id=source.id,
            tier=source.tier,
            url=f"https://upstox.com/instruments/{instrument_key}",
            fetched_at=fetched_at,
            value=Decimal(str(last_price)),
            as_of=as_of,
        )
        observations.append(Observation(field=field, evidence=evidence))
    return observations


def _find_quote(quote_data: dict[str, Any], instrument_key: str) -> dict[str, Any] | None:
    """Upstox keys `data` by an exchange-prefixed symbol, not the instrument_key we sent."""
    for entry in quote_data.values():
        if entry.get("instrument_token") == instrument_key:
            result: dict[str, Any] = entry
            return result
    return None


def _parse_trade_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).astimezone(UTC)
    except ValueError:
        return None


@dataclass(frozen=True)
class StrikeQuote:
    strike: Decimal
    call_oi: int | None
    call_ltp: Decimal | None
    call_volume: int | None
    put_oi: int | None
    put_ltp: Decimal | None
    put_volume: int | None


@dataclass(frozen=True)
class OptionChainSnapshot:
    """Raw per-strike option-chain data. PCR / max-pain are computed downstream, not here."""

    underlying_key: str
    expiry: str
    fetched_at: datetime
    strikes: list[StrikeQuote]


def option_chain(
    client: httpx.Client,
    access_token: str,
    instrument_key: str,
    expiry_date: str,
    source: Source,
) -> OptionChainSnapshot:
    """Fetch the raw per-strike option chain for one underlying + expiry (e.g. NIFTY weekly)."""
    require(source, "api")
    response = get_with_retries(
        client,
        f"{BASE_URL}/option/chain",
        params={"instrument_key": instrument_key, "expiry_date": expiry_date},
        headers=_auth_headers(access_token),
    )
    payload = response.json()
    if payload.get("status") != "success":
        raise DataSourceError(f"Upstox option chain: status={payload.get('status')!r}")
    rows = payload.get("data") or []
    if not rows:
        raise DataSourceError(
            f"Upstox option chain: no strikes for {instrument_key!r} @ {expiry_date!r}"
        )

    strikes = [_parse_strike_row(row, instrument_key) for row in rows]
    return OptionChainSnapshot(
        underlying_key=instrument_key,
        expiry=expiry_date,
        fetched_at=datetime.now(UTC),
        strikes=strikes,
    )


def _parse_strike_row(row: dict[str, Any], instrument_key: str) -> StrikeQuote:
    strike_price = row.get("strike_price")
    if strike_price is None:
        raise DataSourceError(f"Upstox option chain: strike row missing strike_price {row!r}")
    call = row.get("call_options") or {}
    put = row.get("put_options") or {}
    call_md = call.get("market_data") or {}
    put_md = put.get("market_data") or {}
    return StrikeQuote(
        strike=Decimal(str(strike_price)),
        call_oi=_optional_int(call_md.get("oi")),
        call_ltp=_optional_decimal(call_md.get("ltp")),
        call_volume=_optional_int(call_md.get("volume")),
        put_oi=_optional_int(put_md.get("oi")),
        put_ltp=_optional_decimal(put_md.get("ltp")),
        put_volume=_optional_int(put_md.get("volume")),
    )


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)  # type: ignore[call-overload]


def _optional_decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))
