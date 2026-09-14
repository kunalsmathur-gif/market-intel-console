"""Report runs as a Postgres job queue: no Redis until it's needed (PRD §8.11).

A run is keyed by (report type, trading date, version), so enqueueing twice is a no-op and a
retry never publishes twice. Workers claim runs with SKIP LOCKED, and an advisory lock makes
sure only one scheduler enqueues.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from citebell_schemas import ReportType, RunKey, RunStatus

from .schedule import ReportSlot

if TYPE_CHECKING:
    import psycopg

SCHEDULER_LOCK = "citebell:scheduler"
FINAL_STATUSES = frozenset(
    {RunStatus.PUBLISHED, RunStatus.PARTIAL, RunStatus.WITHHELD, RunStatus.FAILED}
)


@dataclass(frozen=True)
class ClaimedRun:
    id: int
    key: RunKey
    deadline_at: datetime
    attempts: int


def enqueue_run(
    conn: psycopg.Connection[Any], slot: ReportSlot, trading_date: date, version: int = 1
) -> int | None:
    """Queue a run. Returns its id, or None if that run already exists."""
    row = conn.execute(
        """
        insert into public.report_runs (report_type, trading_date, version, deadline_at)
        values (%s::public.report_type, %s, %s, %s)
        on conflict (report_type, trading_date, version) do nothing
        returning id
        """,
        (slot.report_type.value, trading_date, version, slot.deadline_at(trading_date)),
    ).fetchone()
    return None if row is None else int(row[0])


def claim_next_run(conn: psycopg.Connection[Any]) -> ClaimedRun | None:
    """Take the queued run with the nearest deadline, skipping runs another worker holds."""
    row = conn.execute(
        """
        update public.report_runs
           set status = 'running', started_at = now(), attempts = attempts + 1
         where id = (
               select id from public.report_runs
                where status = 'queued'
                order by deadline_at
                limit 1
                for update skip locked)
        returning id, report_type::text, trading_date, version, deadline_at, attempts
        """
    ).fetchone()
    if row is None:
        return None
    run_id, report_type, trading_date, version, deadline_at, attempts = row
    key = RunKey(report_type=ReportType(report_type), trading_date=trading_date, version=version)
    return ClaimedRun(id=run_id, key=key, deadline_at=deadline_at, attempts=attempts)


def finish_run(
    conn: psycopg.Connection[Any],
    run_id: int,
    status: RunStatus,
    trace: list[dict[str, Any]],
    error: str | None = None,
) -> None:
    if status not in FINAL_STATUSES:
        raise ValueError(f"{status} is not a final run status")
    conn.execute(
        """
        update public.report_runs
           set status = %s::public.run_status, finished_at = now(), trace = %s::jsonb, error = %s
         where id = %s
        """,
        (status.value, json.dumps(trace, default=str), error, run_id),
    )


def try_scheduler_lock(conn: psycopg.Connection[Any]) -> bool:
    """Session-level lock: hold this connection open for as long as the scheduler runs."""
    row = conn.execute(
        "select pg_try_advisory_lock(hashtext(%s))", (SCHEDULER_LOCK,)
    ).fetchone()
    return bool(row and row[0])
