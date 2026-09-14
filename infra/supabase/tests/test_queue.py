"""The worker's run queue against real Postgres: idempotent enqueue, SKIP LOCKED, one scheduler."""

from __future__ import annotations

from datetime import date
from typing import Any

import psycopg
import pytest

from citebell_schemas import ReportType, RunStatus
from citebell_worker import queue
from citebell_worker.schedule import SCHEDULE

DAY = date(2026, 9, 15)


def test_enqueue_is_idempotent(db: psycopg.Connection[Any]) -> None:
    first = queue.enqueue_run(db, SCHEDULE[ReportType.MORNING], DAY)
    assert isinstance(first, int)
    assert queue.enqueue_run(db, SCHEDULE[ReportType.MORNING], DAY) is None
    assert queue.enqueue_run(db, SCHEDULE[ReportType.MORNING], DAY, version=2) is not None


def test_claims_the_nearest_deadline_first(db: psycopg.Connection[Any]) -> None:
    eod = queue.enqueue_run(db, SCHEDULE[ReportType.EOD], DAY)
    morning = queue.enqueue_run(db, SCHEDULE[ReportType.MORNING], DAY)
    first = queue.claim_next_run(db)
    second = queue.claim_next_run(db)
    assert first is not None and second is not None
    assert (first.id, second.id) == (morning, eod)
    assert first.key.report_type is ReportType.MORNING
    assert first.attempts == 1
    assert queue.claim_next_run(db) is None


def test_a_run_locked_by_another_worker_is_skipped(db: psycopg.Connection[Any], db_url: str) -> None:
    morning = queue.enqueue_run(db, SCHEDULE[ReportType.MORNING], DAY)
    midday = queue.enqueue_run(db, SCHEDULE[ReportType.MIDDAY], DAY)
    with psycopg.connect(db_url) as other, other.transaction():
        other.execute("select id from public.report_runs where id = %s for update", (morning,))
        claimed = queue.claim_next_run(db)
    assert claimed is not None and claimed.id == midday


def test_finish_run_stores_status_trace_and_error(db: psycopg.Connection[Any]) -> None:
    run_id = queue.enqueue_run(db, SCHEDULE[ReportType.MORNING], DAY)
    assert run_id is not None
    trace = [{"step": "gate", "ok": True, "duration_ms": 3}]
    queue.finish_run(db, run_id, RunStatus.WITHHELD, trace, "no section passed the gate")
    row = db.execute(
        """select status::text, trace, error, finished_at is not null
           from public.report_runs where id = %s""",
        (run_id,),
    ).fetchone()
    assert row == ("withheld", trace, "no section passed the gate", True)


def test_finish_run_rejects_a_non_final_status(db: psycopg.Connection[Any]) -> None:
    with pytest.raises(ValueError, match="not a final run status"):
        queue.finish_run(db, 1, RunStatus.RUNNING, [])


def test_only_one_scheduler_holds_the_lock(db_url: str) -> None:
    with (
        psycopg.connect(db_url, autocommit=True) as first,
        psycopg.connect(db_url, autocommit=True) as second,
    ):
        assert queue.try_scheduler_lock(first)
        assert not queue.try_scheduler_lock(second)
    with psycopg.connect(db_url, autocommit=True) as third:
        assert queue.try_scheduler_lock(third)  # released when the holder disconnected
