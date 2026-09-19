"""Write step: turn each report section's gated claims into rendered prose (PRD §7 write;
architecture diagram's "Writer: fills template").

The model drafts prose with ``{{claim_id}}`` placeholders — it never gets to write a number,
a quote, or a citation itself (PRD §8.2 "models never produce numbers; they return
placeholders that code fills in"). Code resolves every placeholder to the matching published
claim's value or quote; a placeholder that doesn't name a claim this section actually
published fails the whole section closed (withheld) rather than showing an unverifiable
number, mirroring the same fail-closed posture as gate.py.
"""

import logging
import re
from collections.abc import Callable

from citebell_schemas import Claim, ClaimType

from ..llm import LLMError, LLMRequest, LLMRouter
from ..llm import Step as LLMStep
from .runner import Citation, RenderedSection, RunContext
from .templates import ReportTemplate, SectionTemplate

log = logging.getLogger(__name__)

WRITE_SCHEMA = {
    "type": "object",
    "properties": {"paragraph": {"type": "string"}},
    "required": ["paragraph"],
    "additionalProperties": False,
}

PLACEHOLDER_RE = re.compile(r"\{\{([^{}]+)\}\}")

# Claim.unit -> the suffix code prints after a resolved value; anything else prints bare.
UNIT_SUFFIXES: dict[str, str] = {"percent": "%", "inr_crore": " Cr"}


def _claim_value_text(claim: Claim) -> str:
    """The one deterministic rendering of a claim's number or quote — never the model's own
    words, so a claim's evidence always matches what the report actually says."""
    if claim.claim_type is ClaimType.MARKET_NUMBER and claim.value is not None:
        # normalize() strips trailing zeros but can flip round numbers into scientific
        # notation (e.g. 24500 -> 2.45E+4); format as a plain fixed-point string instead.
        value = format(claim.value.normalize(), "f")
        return f"{value}{UNIT_SUFFIXES.get(claim.unit or '', '')}"
    return claim.text


def _citation_for(claim: Claim) -> Citation:
    evidence = claim.evidence[0] if claim.evidence else None
    return Citation(
        claim_id=claim.id,
        source_id=evidence.source_id if evidence else "",
        url=evidence.url if evidence else None,
    )


def _all_published_claims(ctx: RunContext) -> dict[str, Claim]:
    claims: dict[str, Claim] = {}
    for section in ctx.sections:
        claims.update(section.published_claims())
    return claims


def _pick_slots(
    section_template: SectionTemplate, published: dict[str, Claim], news_used: set[str]
) -> list[Claim]:
    by_field: dict[str, Claim] = {c.field: c for c in published.values() if c.field}
    slots = [by_field[f] for f in section_template.market_fields if f in by_field]
    if section_template.include_news:
        for claim in published.values():
            if claim.claim_type is ClaimType.NEWS_EVENT and claim.id not in news_used:
                slots.append(claim)
                news_used.add(claim.id)
    return slots


def render_section(
    section_template: SectionTemplate,
    published: dict[str, Claim],
    news_used: set[str],
    router: LLMRouter,
    prompt: str,
) -> RenderedSection:
    """Render one section from whatever published claims fill its template slots. Returns a
    withheld ``RenderedSection`` (no LLM call) if nothing is available to write about yet."""
    slots = _pick_slots(section_template, published, news_used)
    if not slots:
        return RenderedSection(
            section_template.key, section_template.title, text=None,
            withheld_reason="no published claims for this section yet",
        )

    facts = "\n".join(f"{{{{{c.id}}}}} = {c.text}" for c in slots)
    request = LLMRequest(
        system=prompt,
        user=(
            f'Write a short paragraph for the "{section_template.title}" section using only '
            f"the facts below. Refer to every number or quote by its placeholder token exactly "
            f"as given (e.g. {{{{{slots[0].id}}}}}) — never write the value or quote yourself.\n\n"
            f"{facts}"
        ),
        schema_name="section_paragraph",
        json_schema=WRITE_SCHEMA,
    )
    try:
        result = router.complete_json(LLMStep.WRITE, request)
    except LLMError as exc:
        log.warning("write %s: %s", section_template.key, exc)
        return RenderedSection(
            section_template.key, section_template.title, text=None,
            withheld_reason=f"writer model unavailable: {exc}",
        )

    paragraph = result.data.get("paragraph", "") if isinstance(result.data, dict) else ""
    known = {c.id: c for c in slots}
    used_ids: list[str] = []
    for match in PLACEHOLDER_RE.finditer(str(paragraph)):
        token = match.group(1).strip()
        if token not in known:
            log.warning(
                "write %s: model cited an unpublished claim %r, withholding the section",
                section_template.key, token,
            )
            return RenderedSection(
                section_template.key, section_template.title, text=None,
                withheld_reason=f"writer referenced a claim that wasn't published: {token!r}",
            )
        used_ids.append(token)

    def _resolve(match: re.Match[str]) -> str:
        return _claim_value_text(known[match.group(1).strip()])

    text = PLACEHOLDER_RE.sub(_resolve, str(paragraph))
    citations = tuple(_citation_for(known[cid]) for cid in dict.fromkeys(used_ids))
    return RenderedSection(section_template.key, section_template.title, text=text, citations=citations)


def make_write_step(
    report_template: ReportTemplate, router: LLMRouter, prompt: str
) -> Callable[[RunContext], None]:
    """Build a pipeline Step that renders every section of ``report_template`` from whatever
    claims survived the gate step, and stores the result on ``ctx.rendered_sections`` for the
    (unbuilt) check and publish steps."""

    def write_step(ctx: RunContext) -> None:
        published = _all_published_claims(ctx)
        news_used: set[str] = set()
        rendered = [
            render_section(section_template, published, news_used, router, prompt)
            for section_template in report_template.sections
        ]
        ctx.rendered_sections = rendered
        withheld = [r.key for r in rendered if r.text is None]
        if withheld:
            ctx.trace.append({
                "step": "write:withheld",
                "ok": False,
                "detail": f"sections withheld: {', '.join(withheld)}",
            })

    return write_step
