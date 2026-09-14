"""The publish gate: code, not a prompt, and fail-closed (PRD §7 verification pipeline).

| Claim type    | Publish when                                                        | Badge          |
|---------------|---------------------------------------------------------------------|----------------|
| Market number | a T1 source matches, or two independent feeds agree within tolerance | Primary data   |
| Market number | no feed, but two independent T2 reports agree within tolerance       | News-reported  |
| News event    | one T1 source, or two independent T2 sources                         | Verified       |
| Forecast/view | attributed to its author, with a T1/T2 page that carries the quote   | Attributed view|
| Anything else | withheld, with the reasons written to the audit log                  | Withheld       |

Syndicated copies (the same PTI or Reuters story on several sites) count as one source.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from citebell_schemas import (
    Badge,
    Claim,
    ClaimType,
    Evidence,
    EvidenceKind,
    GateDecision,
    SourceTier,
    Verdict,
)

COUNTED_TIERS = frozenset({SourceTier.T1, SourceTier.T2})


@dataclass(frozen=True)
class Tolerance:
    """How far two values may differ and still agree. With neither bound set, only an exact match agrees."""

    absolute: Decimal | None = None
    relative: Decimal | None = None  # a share of the reference value, e.g. 0.0001 is ±0.01%

    def agrees(self, value: Decimal, reference: Decimal) -> bool:
        diff = abs(value - reference)
        if diff == 0:
            return True
        if self.absolute is not None and diff <= self.absolute:
            return True
        return self.relative is not None and diff <= abs(reference) * self.relative


EXACT = Tolerance()

# Units without an entry must match exactly.
DEFAULT_TOLERANCES: Mapping[str, Tolerance] = {
    "index_points": Tolerance(relative=Decimal("0.0001")),  # index ±0.01%
    "inr_crore": Tolerance(absolute=Decimal("0.01")),  # flows exact to ₹0.01 Cr
}


@dataclass(frozen=True)
class GatePolicy:
    now: datetime
    stale_before: datetime  # evidence published or valued before this is too old for the report
    allow_single_source: bool = False  # PRD §8.4: a single source is badged or withheld; default withheld
    clock_skew: timedelta = timedelta(minutes=5)
    tolerances: Mapping[str, Tolerance] = field(default_factory=lambda: DEFAULT_TOLERANCES)


def decide(claim: Claim, policy: GatePolicy) -> GateDecision:
    usable, reasons = _usable_evidence(claim.evidence, policy)
    match claim.claim_type:
        case ClaimType.MARKET_NUMBER:
            return _market_number(claim, usable, reasons, policy)
        case ClaimType.NEWS_EVENT:
            return _news_event(claim, usable, reasons, policy)
        case ClaimType.FORECAST | ClaimType.OPINION:
            return _attributed_view(claim, usable, reasons)


def _usable_evidence(
    evidence: Iterable[Evidence], policy: GatePolicy
) -> tuple[list[Evidence], list[str]]:
    usable: list[Evidence] = []
    reasons: list[str] = []
    for item in evidence:
        problem = _evidence_problem(item, policy)
        if problem is None:
            usable.append(item)
        else:
            reasons.append(f"{item.source_id}: {problem}")
    return usable, reasons


def _evidence_problem(item: Evidence, policy: GatePolicy) -> str | None:
    if item.tier is SourceTier.TX:
        return "tier TX sources are never publishable"
    if item.kind is EvidenceKind.ARTICLE:
        if item.http_status != 200:
            return f"link check failed (HTTP {item.http_status})"
        if not item.quote_found:
            return "quote not found on the page"
        stamp = item.published_at
        missing = "no publish time"
    else:
        stamp = item.as_of
        missing = "feed value has no as-of time"
    if stamp is None:
        return missing
    if stamp > policy.now + policy.clock_skew:
        return "timestamp is in the future"
    if stamp < policy.stale_before:
        return "stale for this report"
    return None


def _independent(evidence: Iterable[Evidence]) -> int:
    return len({item.syndication_group or item.source_id for item in evidence})


def _market_number(
    claim: Claim, usable: list[Evidence], reasons: list[str], policy: GatePolicy
) -> GateDecision:
    if claim.value is None or claim.unit is None or claim.as_of is None:
        return _withhold(claim, reasons, "a market number needs a value, a unit and an as-of time")

    tolerance = policy.tolerances.get(claim.unit, EXACT)
    counted = [e for e in usable if e.tier in COUNTED_TIERS and e.value is not None]
    matching = [e for e in counted if e.value is not None and tolerance.agrees(claim.value, e.value)]
    disagreeing = [e for e in counted if e not in matching]
    if disagreeing:
        names = ", ".join(f"{e.source_id}={e.value}" for e in disagreeing)
        return _withhold(claim, reasons, f"sources disagree with {claim.value}: {names}")

    n = _independent(matching)
    if any(e.tier is SourceTier.T1 for e in matching):
        return _publish(claim, Badge.PRIMARY_DATA, n, reasons)
    feeds = [e for e in matching if e.kind is EvidenceKind.FEED]
    if _independent(feeds) >= 2:
        return _publish(claim, Badge.PRIMARY_DATA, n, reasons)
    if _independent(e for e in matching if e.kind is EvidenceKind.ARTICLE) >= 2:
        return _publish(claim, Badge.NEWS_REPORTED, n, reasons)
    if n == 1 and policy.allow_single_source:
        return _publish(claim, Badge.SINGLE_SOURCE, n, reasons)
    return _withhold(
        claim, reasons, f"needs a T1 match or two independent agreeing sources; found {n}"
    )


def _news_event(
    claim: Claim, usable: list[Evidence], reasons: list[str], policy: GatePolicy
) -> GateDecision:
    counted = [e for e in usable if e.tier in COUNTED_TIERS]
    n = _independent(counted)
    if any(e.tier is SourceTier.T1 for e in counted):
        return _publish(claim, Badge.VERIFIED, n, reasons)
    if n >= 2:
        return _publish(claim, Badge.VERIFIED, n, reasons)
    if n == 1 and policy.allow_single_source:
        return _publish(claim, Badge.SINGLE_SOURCE, n, reasons)
    return _withhold(
        claim, reasons, f"needs one T1 source or two independent T2 sources; found {n}"
    )


def _attributed_view(claim: Claim, usable: list[Evidence], reasons: list[str]) -> GateDecision:
    if not (claim.attributed_to or "").strip():
        return _withhold(claim, reasons, "forecasts and opinions must name who said them")
    pages = [e for e in usable if e.tier in COUNTED_TIERS and e.kind is EvidenceKind.ARTICLE]
    if not pages:
        return _withhold(claim, reasons, "no T1/T2 page carries the attributed quote")
    return _publish(claim, Badge.ATTRIBUTED_VIEW, _independent(pages), reasons)


def _publish(claim: Claim, badge: Badge, sources: int, reasons: list[str]) -> GateDecision:
    return GateDecision(
        claim_id=claim.id,
        verdict=Verdict.PUBLISH,
        badge=badge,
        independent_sources=sources,
        reasons=tuple(reasons),
    )


def _withhold(claim: Claim, reasons: list[str], why: str) -> GateDecision:
    return GateDecision(
        claim_id=claim.id,
        verdict=Verdict.WITHHOLD,
        badge=Badge.WITHHELD,
        reasons=(*reasons, why),
    )
