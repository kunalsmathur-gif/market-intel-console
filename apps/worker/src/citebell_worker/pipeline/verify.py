"""Verify step: confirm (or drop) each news claim's evidence against the live article page
(PRD §7 verify).

``quote_found`` is the one field the gate step trusts absolutely (pipeline/gate.py), so it is
never set by a model — only by a deterministic, normalized substring check against the page's
own text, fetched fresh here. The LLM is used for a second, narrower job: once a quote is
confirmed on the page, judge whether the article actually supports the claim (not just that
the words appear somewhere on it). That judgement can only drop a claim, never confirm one,
and if the model call itself fails, this step fails open — the claim is kept and the hard,
deterministic checks (tier, quote_found, independent sources) still decide whether it publishes.
"""

import logging
import time
from collections.abc import Callable

import httpx

from citebell_schemas import Claim, ClaimType, Evidence, EvidenceKind

from ..data.base import DEFAULT_RETRIES, DEFAULT_TIMEOUT, RETRY_BACKOFF_SECONDS
from ..llm import LLMError, LLMRequest, LLMRouter
from ..llm import Step as LLMStep
from .runner import RunContext
from .textmatch import normalize_for_match, strip_html

log = logging.getLogger(__name__)

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {"supported": {"type": "boolean"}},
    "required": ["supported"],
    "additionalProperties": False,
}


def fetch_article(
    client: httpx.Client, url: str, *, retries: int = DEFAULT_RETRIES
) -> tuple[int | None, str]:
    """GET a page, returning its status and body on *any* response — unlike
    ``data.base.get_with_retries``, a non-200 is a result to record on the evidence, not an
    error to raise away. Only transport failures are retried; ``(None, "")`` means every
    attempt failed at the transport level."""
    for attempt in range(retries + 1):
        try:
            response = client.get(url, timeout=DEFAULT_TIMEOUT, follow_redirects=True)
        except httpx.HTTPError as exc:
            log.warning("verify: GET %s: %r", url, exc)
        else:
            return response.status_code, response.text
        if attempt < retries:
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return None, ""


def _llm_supports_claim(
    router: LLMRouter, prompt: str, claim_text: str, quote: str, article_text: str
) -> bool:
    request = LLMRequest(
        system=prompt,
        user=(
            f"Claim: {claim_text}\nQuote used as evidence: {quote}\n\n"
            f"Article text:\n{article_text[:8000]}"
        ),
        schema_name="claim_support",
        json_schema=VERIFY_SCHEMA,
        # A narrow yes/no judgement doesn't need extended reasoning; skipping it cuts tail
        # latency (was timing out at 60s under normal load) without changing the check itself.
        thinking=False,
    )
    result = router.complete_json(LLMStep.VERIFY, request)
    return bool(result.data.get("supported")) if isinstance(result.data, dict) else False


def verify_article_evidence(
    client: httpx.Client, router: LLMRouter, prompt: str, claim_text: str, evidence: Evidence
) -> tuple[Evidence, str | None]:
    """Fetch the live page, run the deterministic quote check, and — only once that check
    passes — ask the model whether the article supports the claim. Returns the updated
    evidence and, if the claim should be dropped, a reason string."""
    if not evidence.url:
        return evidence, "article evidence has no url to verify"

    status, body = fetch_article(client, evidence.url)
    plain = strip_html(body) if status == 200 and body else ""
    quote = evidence.quote
    quote_found = (
        quote is not None
        and status == 200
        and normalize_for_match(quote) in normalize_for_match(plain)
    )
    updated = evidence.model_copy(update={"http_status": status, "quote_found": quote_found})

    if status != 200:
        return updated, None  # the gate step already withholds evidence with a bad http_status
    if not quote_found:
        return updated, None  # ditto for quote_found=False; no need for the model's opinion

    try:
        supported = _llm_supports_claim(router, prompt, claim_text, evidence.quote or "", plain)
    except LLMError as exc:
        log.warning("verify: model check failed for %s, keeping the claim: %s", evidence.url, exc)
        return updated, None  # fail open: the hard checks above still gate this evidence
    if not supported:
        return updated, f"{evidence.url}: model judged the article does not support the claim"
    return updated, None


def make_news_verify_step(
    client: httpx.Client, router: LLMRouter, prompt: str
) -> Callable[[RunContext], None]:
    """Build a pipeline Step that re-fetches every NEWS_EVENT claim's article evidence,
    confirms (or refutes) its quote, and drops any claim the model judges unsupported."""

    def verify_step(ctx: RunContext) -> None:
        failures: list[str] = []
        for section in ctx.sections:
            kept: list[Claim] = []
            for claim in section.claims:
                if claim.claim_type is not ClaimType.NEWS_EVENT:
                    kept.append(claim)
                    continue
                new_evidence: list[Evidence] = []
                drop = False
                for evidence in claim.evidence:
                    if evidence.kind is not EvidenceKind.ARTICLE:
                        new_evidence.append(evidence)
                        continue
                    updated, reason = verify_article_evidence(client, router, prompt, claim.text, evidence)
                    new_evidence.append(updated)
                    if reason is not None:
                        drop = True
                        failures.append(f"{claim.id}: {reason}")
                if drop:
                    continue
                kept.append(claim.model_copy(update={"evidence": tuple(new_evidence)}))
            section.claims = kept
        if failures:
            ctx.trace.append({"step": "verify:failures", "ok": False, "detail": "; ".join(failures)})

    return verify_step
