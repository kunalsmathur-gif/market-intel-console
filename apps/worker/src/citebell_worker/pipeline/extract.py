"""Extract step: turn RSS feed items into draft news-event claims (PRD §7 extract).

The first LLM step in the pipeline — splitting a headline+summary into atomic claims and
picking a short supporting quote takes judgement code can't do on its own. But the model
never gets to assert a quote exists: every quote it returns is checked, in code, against the
feed item's own title+summary before it becomes a claim (PRD §8.2 "no AI model sits between a
data source and a published number", generalized here to "a model never asserts an
unverifiable quote"). Whether that quote is actually present on the live article page is the
verify step's job, not this one's — this step only proves the model didn't invent it outright.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from citebell_schemas import MAX_QUOTE_WORDS, Claim, ClaimType, Evidence, EvidenceKind, Source

from ..data import DataSourceError, FeedItem, fetch_feed
from ..llm import LLMError, LLMRequest, LLMRouter
from ..llm import Step as LLMStep
from .runner import RunContext, Section
from .textmatch import normalize_for_match

log = logging.getLogger(__name__)

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["text", "quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}


def _item_text(item: FeedItem) -> str:
    return f"{item.title}\n\n{item.summary or ''}".strip()


def extract_claims_from_item(
    router: LLMRouter, prompt: str, source: Source, item: FeedItem, claim_id_prefix: str
) -> list[Claim]:
    """One LLM call per feed item. Every candidate claim is checked against the item's own
    text before it's kept, so the model can split and summarize but never invent a quote."""
    source_text = _item_text(item)
    if not source_text:
        return []
    request = LLMRequest(
        system=prompt,
        user=f"Title: {item.title}\nSummary: {item.summary or '(none)'}\nLink: {item.link}",
        schema_name="news_claims",
        json_schema=EXTRACT_SCHEMA,
    )
    result = router.complete_json(LLMStep.EXTRACT, request)
    raw_claims = result.data.get("claims", []) if isinstance(result.data, dict) else []
    fetched_at = datetime.now(UTC)
    normalized_source = normalize_for_match(source_text)

    claims: list[Claim] = []
    for i, raw in enumerate(raw_claims):
        text = str(raw.get("text", "")).strip()
        quote = str(raw.get("quote", "")).strip()
        if not text or not quote:
            log.warning("extract %s: dropped a claim with no text/quote", source.id)
            continue
        if len(quote.split()) > MAX_QUOTE_WORDS:
            log.warning("extract %s: dropped a quote over %d words", source.id, MAX_QUOTE_WORDS)
            continue
        if normalize_for_match(quote) not in normalized_source:
            log.warning("extract %s: dropped a quote not found in the source text", source.id)
            continue
        evidence = Evidence(
            kind=EvidenceKind.ARTICLE,
            source_id=source.id,
            tier=source.tier,
            url=item.link,
            published_at=item.published_at,
            fetched_at=fetched_at,
            quote=quote,
            # Confirmed against the live page by the verify step, never here.
            quote_found=False,
        )
        claims.append(
            Claim(
                id=f"{claim_id_prefix}:{i}",
                claim_type=ClaimType.NEWS_EVENT,
                text=text,
                evidence=(evidence,),
            )
        )
    return claims


@dataclass(frozen=True)
class ExtractResult:
    claims: list[Claim]
    failures: list[str]  # "{source or item}: {error}" for every feed or item that failed


def extract_news_claims(
    client: httpx.Client,
    router: LLMRouter,
    prompt: str,
    sources: Sequence[Source],
    run_id: str,
) -> ExtractResult:
    """Fetch every RSS source and extract claims from each item. One source's fetch failure,
    or one item's LLM failure, withholds only its own claims (PRD §7)."""
    claims: list[Claim] = []
    failures: list[str] = []
    for source in sources:
        try:
            items = fetch_feed(client, source)
        except DataSourceError as exc:
            log.warning("extract %s: %s", source.id, exc)
            failures.append(f"{source.id}: {exc}")
            continue
        for item_index, item in enumerate(items):
            claim_id_prefix = f"{run_id}:{source.id}:{item_index}"
            try:
                claims.extend(extract_claims_from_item(router, prompt, source, item, claim_id_prefix))
            except LLMError as exc:
                log.warning("extract %s item %d: %s", source.id, item_index, exc)
                failures.append(f"{source.id}[{item_index}]: {exc}")
    return ExtractResult(claims=claims, failures=failures)


def make_extract_step(
    client: httpx.Client,
    router: LLMRouter,
    prompt: str,
    sources: Sequence[Source],
    section_key: str = "news",
    section_title: str = "News",
) -> Callable[[RunContext], None]:
    """Build a pipeline Step that runs ``extract_news_claims`` and appends the resulting
    draft claims to a section, creating it if this is the first step to touch it."""

    def extract_step(ctx: RunContext) -> None:
        result = extract_news_claims(client, router, prompt, sources, run_id=str(ctx.key))
        section = next((s for s in ctx.sections if s.key == section_key), None)
        if section is None:
            section = Section(key=section_key, title=section_title)
            ctx.sections.append(section)
        section.claims.extend(result.claims)
        if result.failures:
            ctx.trace.append({"step": "extract:failures", "ok": False, "detail": "; ".join(result.failures)})

    return extract_step
