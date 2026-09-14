"""Typed inputs and outputs of the verification pipeline (PRD §7 verification, §8.8 storage).

Every time is timezone-aware. Quotes are capped at 25 words because Citebell stores
headlines, links and short quotes, never full articles.
"""

from datetime import date
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .enums import (
    Badge,
    ClaimType,
    EvidenceKind,
    ReportType,
    SourceKind,
    SourceTier,
    Verdict,
)

MAX_QUOTE_WORDS = 25


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(_Model):
    """One entry in the source registry (the registry itself lives in the private config repo)."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str
    domain: str
    tier: SourceTier
    kind: SourceKind
    url: str | None = None
    active: bool = True


class Evidence(_Model):
    """One piece of support for a claim: a feed value or an article that states it."""

    kind: EvidenceKind
    source_id: str
    tier: SourceTier
    url: str | None = None
    # Copies of one wire story (PTI, Reuters) share a group and count as one source.
    syndication_group: str | None = None
    published_at: AwareDatetime | None = None
    fetched_at: AwareDatetime
    http_status: int | None = None
    quote: str | None = None
    quote_found: bool = False
    value: Decimal | None = None
    as_of: AwareDatetime | None = None

    @field_validator("quote")
    @classmethod
    def _short_quote(cls, quote: str | None) -> str | None:
        if quote is not None and len(quote.split()) > MAX_QUOTE_WORDS:
            raise ValueError(f"quotes are limited to {MAX_QUOTE_WORDS} words")
        return quote


class Claim(_Model):
    """An atomic statement pulled from a draft, with the evidence gathered for it."""

    id: str
    claim_type: ClaimType
    text: str
    field: str | None = None  # e.g. "nifty50.close"; set for market numbers
    unit: str | None = None  # e.g. "index_points", "inr_crore"
    value: Decimal | None = None
    as_of: AwareDatetime | None = None
    attributed_to: str | None = None  # required for forecasts and opinions
    evidence: tuple[Evidence, ...] = ()


class GateDecision(_Model):
    """The publish gate's verdict for one claim. Reasons are written to the audit log."""

    claim_id: str
    verdict: Verdict
    badge: Badge
    independent_sources: int = 0
    reasons: tuple[str, ...] = ()


class RunKey(_Model):
    """Identifies a report run, so a retry never publishes twice (PRD §8.11)."""

    report_type: ReportType
    trading_date: date
    version: int = Field(default=1, ge=1)
