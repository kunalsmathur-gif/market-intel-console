"""Collect step: turn data-connector observations into market-number claims (PRD §7 collect,
§8.2 "no AI model sits between a data source and a published number").

Deterministic and LLM-free — a market number's value, as-of time and evidence come straight
from a connector fetch, never a model's guess. A connector that fails withholds only its own
claims; it never fails the whole run, since the gate step already withholds any claim that
ends up under-evidenced (PRD §7).
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from citebell_schemas import Claim, ClaimType

from ..data import DataSourceError, Observation
from .runner import RunContext, Section

log = logging.getLogger(__name__)

# Units the gate's tolerance table (pipeline/gate.py) recognizes; anything else falls back to
# an exact match. Kept here, next to the claims that carry it, rather than guessed per-call.
FIELD_UNITS: Mapping[str, str] = {
    "nifty50.close": "index_points",
    "nifty50.ltp": "index_points",
    "banknifty.close": "index_points",
    "banknifty.ltp": "index_points",
    "india_vix.ltp": "index_points",
    "sensex.close": "index_points",
    "sensex.ltp": "index_points",
    "us10y.yield": "percent",
    "bitcoin.price_usd": "usd",
    "ethereum.price_usd": "usd",
    "btc.dominance_pct": "percent",
    "fii.net_cash_cr": "inr_crore",
    "dii.net_cash_cr": "inr_crore",
}


def market_number_claim(claim_id: str, observation: Observation, unit: str | None = None) -> Claim:
    """One Claim per Observation. The text is a plain restatement — the report's own copy is
    written by the (unbuilt) write step; this is only what a fact-check drawer would show."""
    resolved_unit = unit if unit is not None else FIELD_UNITS.get(observation.field)
    return Claim(
        id=claim_id,
        claim_type=ClaimType.MARKET_NUMBER,
        text=f"{observation.field} is {observation.evidence.value}",
        field=observation.field,
        unit=resolved_unit,
        value=observation.evidence.value,
        as_of=observation.evidence.as_of,
        evidence=(observation.evidence,),
    )


@dataclass(frozen=True)
class CollectorSpec:
    """One connector call the collect step will run.

    ``fetch`` takes no arguments — bind the client, api key and any parameters with a
    closure or ``functools.partial`` when building the spec, so this stays a plain, retryable
    unit of work regardless of which connector it wraps.
    """

    name: str
    fetch: Callable[[], Sequence[Observation]]
    unit: str | None = None


@dataclass(frozen=True)
class CollectResult:
    claims: list[Claim]
    failures: list[str]  # "{spec.name}: {error}" for every connector that couldn't be reached


def collect(specs: Sequence[CollectorSpec], run_id: str) -> CollectResult:
    """Run every collector. One spec raising DataSourceError withholds only its own claims."""
    claims: list[Claim] = []
    failures: list[str] = []
    for spec in specs:
        try:
            observations = spec.fetch()
        except DataSourceError as exc:
            log.warning("collect %s: %s", spec.name, exc)
            failures.append(f"{spec.name}: {exc}")
            continue
        for i, observation in enumerate(observations):
            claim_id = f"{run_id}:{spec.name}:{i}"
            claims.append(market_number_claim(claim_id, observation, spec.unit))
    return CollectResult(claims=claims, failures=failures)


def make_collect_step(
    specs: Sequence[CollectorSpec], section_key: str = "market", section_title: str = "Market"
) -> Callable[[RunContext], None]:
    """Build a pipeline Step that runs ``specs`` and appends their claims to a section,
    creating it if this is the first step to touch it."""

    def collect_step(ctx: RunContext) -> None:
        result = collect(specs, run_id=str(ctx.key))
        section = next((s for s in ctx.sections if s.key == section_key), None)
        if section is None:
            section = Section(key=section_key, title=section_title)
            ctx.sections.append(section)
        section.claims.extend(result.claims)
        if result.failures:
            ctx.trace.append({"step": "collect:failures", "ok": False, "detail": "; ".join(result.failures)})

    return collect_step
