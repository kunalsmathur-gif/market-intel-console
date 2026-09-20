"""Check step: a final, code-only editor pass over the write step's rendered sections (PRD §7
"Editor / QA: consistency · rounding · attribution").

Write's placeholder substitution is already deterministic, so this step isn't a second draft --
it's a fail-closed safety net for the handful of things that can still slip through:

* **Rounding.** A claim's raw value can carry more precision than a report should show (a feed
  returning 24500.1234 instead of a clean 24500.12). This step reformats any cited number that
  exceeds its unit's display precision; values already within the convention are left untouched.
* **Consistency.** The same market field must show the very same number everywhere in one report
  (PRD §7 "a number has one value everywhere in a report"). write.py only ever resolves one
  global claim per field in a single run, so this can't currently diverge -- but this step
  re-derives and cross-checks it independently anyway, so a future change to write.py that broke
  that guarantee would be caught here, not in production.
* **Attribution.** A forecast or opinion must always be shown with who said it. write.py doesn't
  select FORECAST/OPINION claims for any section today, but this step still enforces the rule so
  the day one is added it can't accidentally publish in Citebell's own voice.

A section that fails any of these checks is withheld at this stage, in the same fail-closed
style as gate.py.
"""

import logging
from collections.abc import Callable
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from citebell_schemas import Claim, ClaimType

from .runner import RenderedSection, RunContext
from .write import UNIT_SUFFIXES, all_published_claims, claim_value_text

log = logging.getLogger(__name__)

# Max decimal places shown for a unit; a unit with no entry here already prints with the
# precision the data source gives it (e.g. a plain index level) and is left alone.
DISPLAY_DECIMALS: dict[str, int] = {"percent": 2, "inr_crore": 2, "index_points": 2}


def _rounded_value_text(claim: Claim) -> str | None:
    """The display-precision version of a market number's rendered text, or None if the claim
    already prints within its unit's convention (nothing to round)."""
    if claim.claim_type is not ClaimType.MARKET_NUMBER or claim.value is None:
        return None
    decimals = DISPLAY_DECIMALS.get(claim.unit or "")
    if decimals is None:
        return None
    exponent = claim.value.as_tuple().exponent
    current_decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    if current_decimals <= decimals:
        return None
    quantum = Decimal(1).scaleb(-decimals)
    rounded = claim.value.quantize(quantum, rounding=ROUND_HALF_UP)
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}{UNIT_SUFFIXES.get(claim.unit or '', '')}"


def _check_rounding(section: RenderedSection, claims: dict[str, Claim]) -> RenderedSection:
    if section.text is None:
        return section
    text = section.text
    for citation in section.citations:
        claim = claims.get(citation.claim_id)
        if claim is None:
            continue
        rounded = _rounded_value_text(claim)
        if rounded is not None:
            text = text.replace(claim_value_text(claim), rounded)
    return section if text == section.text else replace(section, text=text)


def _check_consistency(
    sections: list[RenderedSection], claims: dict[str, Claim]
) -> list[RenderedSection]:
    """Every field cited across the report must resolve to one canonical value. Withholds any
    section that cites a field where two different published claims disagree."""
    field_values: dict[str, str] = {}
    conflicting_fields: set[str] = set()
    for section in sections:
        if section.text is None:
            continue
        for citation in section.citations:
            claim = claims.get(citation.claim_id)
            if claim is None or claim.field is None:
                continue
            value_text = claim_value_text(claim)
            existing = field_values.setdefault(claim.field, value_text)
            if existing != value_text:
                conflicting_fields.add(claim.field)
    if not conflicting_fields:
        return sections

    result = []
    for section in sections:
        cited_fields = {
            claims[c.claim_id].field
            for c in section.citations
            if c.claim_id in claims and claims[c.claim_id].field is not None
        }
        bad: set[str] = {f for f in cited_fields if f is not None} & conflicting_fields
        if section.text is not None and bad:
            log.warning("check %s: conflicting values for %s, withholding the section",
                       section.key, ", ".join(sorted(bad)))
            result.append(replace(
                section, text=None, citations=(),
                withheld_reason=f"conflicting published values for {', '.join(sorted(bad))}",
            ))
        else:
            result.append(section)
    return result


def _check_attribution(section: RenderedSection, claims: dict[str, Claim]) -> RenderedSection:
    if section.text is None:
        return section
    for citation in section.citations:
        claim = claims.get(citation.claim_id)
        if claim is None or claim.claim_type not in (ClaimType.FORECAST, ClaimType.OPINION):
            continue
        name = (claim.attributed_to or "").strip()
        if not name or name.lower() not in section.text.lower():
            log.warning("check %s: claim %r has no attribution in the written text",
                       section.key, citation.claim_id)
            return replace(
                section, text=None, citations=(),
                withheld_reason=(
                    f"forecast/opinion claim {citation.claim_id!r} has no attribution in the text"
                ),
            )
    return section


def make_check_step() -> Callable[[RunContext], None]:
    """Build a pipeline Step that runs the rounding, consistency and attribution checks over
    ``ctx.rendered_sections`` in place, recording any section this step newly withholds."""

    def check_step(ctx: RunContext) -> None:
        claims = all_published_claims(ctx)
        already_withheld = {s.key for s in ctx.rendered_sections if s.text is None}

        sections = [_check_rounding(s, claims) for s in ctx.rendered_sections]
        sections = _check_consistency(sections, claims)
        sections = [_check_attribution(s, claims) for s in sections]

        ctx.rendered_sections = sections
        newly_withheld = [s.key for s in sections if s.text is None and s.key not in already_withheld]
        if newly_withheld:
            ctx.trace.append({
                "step": "check:withheld",
                "ok": False,
                "detail": f"sections withheld: {', '.join(newly_withheld)}",
            })

    return check_step
