"""Run a report's steps in order, timing each one, and fail closed.

Collect → extract → verify → gate → write → check → publish. Each step is a plain function
that reads and extends the run context, so any report can be rebuilt from its saved inputs.
A step that raises stops the run; a run that ends with no published section is withheld.
"""

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from citebell_schemas import Claim, GateDecision, RunKey, RunStatus, Verdict

from .gate import GatePolicy, decide

log = logging.getLogger(__name__)


@dataclass
class Section:
    key: str
    title: str
    claims: list[Claim] = field(default_factory=list)
    decisions: list[GateDecision] = field(default_factory=list)

    @property
    def publishable(self) -> bool:
        return any(d.verdict is Verdict.PUBLISH for d in self.decisions)

    def published_claims(self) -> dict[str, Claim]:
        """Claims the gate step passed, keyed by id (decisions are parallel to claims)."""
        verdicts = {d.claim_id: d.verdict for d in self.decisions}
        return {c.id: c for c in self.claims if verdicts.get(c.id) is Verdict.PUBLISH}


@dataclass(frozen=True)
class Citation:
    """One claim cited by a rendered section's text, for the fact-check drawer (PRD §7)."""

    claim_id: str
    source_id: str
    url: str | None


@dataclass(frozen=True)
class RenderedSection:
    """The write step's output for one report section: prose with every number/quote
    resolved from a published claim, or a reason the section is withheld instead."""

    key: str
    title: str
    text: str | None  # None when withheld
    citations: tuple[Citation, ...] = ()
    withheld_reason: str | None = None


@dataclass
class RunContext:
    key: RunKey
    policy: GatePolicy
    sections: list[Section] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    rendered_sections: list[RenderedSection] = field(default_factory=list)


Step = Callable[[RunContext], None]


def gate_step(ctx: RunContext) -> None:
    for section in ctx.sections:
        section.decisions = [decide(claim, ctx.policy) for claim in section.claims]


# Steps are added here as they're built; until then every run is withheld.
V0_STEPS: Sequence[tuple[str, Step]] = (("gate", gate_step),)


@dataclass(frozen=True)
class RunOutcome:
    status: RunStatus
    trace: list[dict[str, Any]]
    error: str | None = None


def run_pipeline(ctx: RunContext, steps: Sequence[tuple[str, Step]] = V0_STEPS) -> RunOutcome:
    for name, step in steps:
        started_at = datetime.now(ctx.policy.now.tzinfo)
        started = time.monotonic()
        try:
            step(ctx)
        except Exception as exc:
            log.exception("run %s: step %s failed", ctx.key, name)
            ctx.trace.append(_record(name, started_at, started, ok=False, detail=repr(exc)))
            return RunOutcome(RunStatus.FAILED, ctx.trace, error=f"{name}: {exc!r}")
        ctx.trace.append(_record(name, started_at, started, ok=True))

    if ctx.rendered_sections:
        published_sections = [s for s in ctx.rendered_sections if s.text is not None]
        if not published_sections:
            return RunOutcome(RunStatus.WITHHELD, ctx.trace, error="no report section passed check")
        if len(published_sections) < len(ctx.rendered_sections):
            return RunOutcome(RunStatus.PARTIAL, ctx.trace)
        return RunOutcome(RunStatus.PUBLISHED, ctx.trace)

    published = [s for s in ctx.sections if s.publishable]
    if not published:
        return RunOutcome(RunStatus.WITHHELD, ctx.trace, error="no section passed the gate")
    if len(published) < len(ctx.sections):
        return RunOutcome(RunStatus.PARTIAL, ctx.trace)
    return RunOutcome(RunStatus.PUBLISHED, ctx.trace)


def _record(
    name: str, started_at: datetime, started: float, ok: bool, detail: str | None = None
) -> dict[str, Any]:
    return {
        "step": name,
        "started_at": started_at.isoformat(),
        "duration_ms": round((time.monotonic() - started) * 1000),
        "ok": ok,
        "detail": detail,
    }
