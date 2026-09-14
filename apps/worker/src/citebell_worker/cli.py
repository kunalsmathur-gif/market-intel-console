"""Command line entry point.

    citebell-worker check                     settings, private config and database reachability
    citebell-worker dry-run --report morning  run the pipeline in memory, print the trace
    citebell-worker scheduler                 the always-on process that Railway runs
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta

import httpx

from citebell_schemas import ReportType, RunKey

from .config import Settings, get_settings
from .pipeline.gate import GatePolicy
from .pipeline.runner import RunContext, run_pipeline
from .private_config import PrivateConfig, PrivateConfigError, load_private_config
from .schedule import IST, SCHEDULE, is_trading_day, now_ist

log = logging.getLogger("citebell_worker")

QUEUE_POLL_SECONDS = 10
MISFIRE_GRACE_SECONDS = 600


def default_policy(now: datetime) -> GatePolicy:
    # One window for every section for now; per-section windows arrive with the report templates.
    return GatePolicy(now=now, stale_before=now - timedelta(hours=24))


def _load_config(settings: Settings) -> PrivateConfig:
    config = load_private_config(settings.resolved_private_config_dir)
    if settings.using_example_config:
        log.warning("PRIVATE_CONFIG_DIR is not set: using the public example config")
    if not any(day.year == now_ist().year for day in config.holidays):
        log.warning("no NSE holidays listed for %s: every weekday counts as a trading day",
                    now_ist().year)
    return config


def cmd_check(settings: Settings) -> int:
    config = _load_config(settings)
    print(f"private config: {config.root} ({len(config.sources)} sources)")
    for slot in SCHEDULE.values():
        start = slot.collect_start.strftime("%H:%M") if slot.collect_start else "on upload"
        print(f"  {slot.title:<22} collect {start:<9} deadline {slot.deadline:%H:%M} IST")
    if settings.database_url is None:
        print("database: DATABASE_URL not set")
        return 0
    import psycopg  # only commands that touch the database load the driver

    with psycopg.connect(settings.database_url.get_secret_value(), connect_timeout=10) as conn:
        conn.execute("select 1")
    print("database: reachable")
    return 0


def cmd_dry_run(settings: Settings, report: ReportType, trading_date: date) -> int:
    _load_config(settings)
    ctx = RunContext(key=RunKey(report_type=report, trading_date=trading_date),
                     policy=default_policy(now_ist()))
    outcome = run_pipeline(ctx)
    print(json.dumps({"run": ctx.key.model_dump(mode="json"), "status": outcome.status,
                      "error": outcome.error, "trace": outcome.trace}, indent=2))
    return 0


def cmd_scheduler(settings: Settings) -> int:
    import psycopg
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    from . import queue

    if settings.database_url is None:
        log.error("DATABASE_URL is required for the scheduler")
        return 2
    dsn = settings.database_url.get_secret_value()
    config = _load_config(settings)

    lock_conn = psycopg.connect(dsn, autocommit=True)
    if not queue.try_scheduler_lock(lock_conn):
        log.error("another scheduler holds the lock; exiting")
        return 1

    def enqueue_today(report: ReportType) -> None:
        today = now_ist().date()
        if not is_trading_day(today, config.holidays):
            log.info("%s: %s is not a trading day", report, today)
            return
        with psycopg.connect(dsn, autocommit=True) as conn:
            run_id = queue.enqueue_run(conn, SCHEDULE[report], today)
        log.info("%s %s: %s", report, today, f"queued run {run_id}" if run_id else "already queued")

    def process_queue() -> None:
        with psycopg.connect(dsn, autocommit=True) as conn:
            run = queue.claim_next_run(conn)
            if run is None:
                return
            ctx = RunContext(key=run.key, policy=default_policy(now_ist()))
            outcome = run_pipeline(ctx)
            queue.finish_run(conn, run.id, outcome.status, outcome.trace, outcome.error)
        log.info("run %s %s: %s", run.id, run.key, outcome.status)
        if settings.healthcheck_ping_url:
            try:
                httpx.get(settings.healthcheck_ping_url, timeout=10)
            except httpx.HTTPError as exc:
                log.warning("health check ping failed: %s", exc)

    scheduler = BlockingScheduler(timezone=IST)
    for slot in SCHEDULE.values():
        if slot.collect_start is None:
            continue  # Institutional Flows is queued when NSE's file arrives
        trigger = CronTrigger(day_of_week="mon-fri", hour=slot.collect_start.hour,
                              minute=slot.collect_start.minute, timezone=IST)
        scheduler.add_job(enqueue_today, trigger, args=[slot.report_type],
                          id=f"enqueue-{slot.report_type}", coalesce=True,
                          misfire_grace_time=MISFIRE_GRACE_SECONDS)
    scheduler.add_job(process_queue, "interval", seconds=QUEUE_POLL_SECONDS, id="process-queue",
                      coalesce=True, max_instances=1)
    log.info("scheduler started with %d jobs", len(scheduler.get_jobs()))
    try:
        scheduler.start()
    finally:
        lock_conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citebell-worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="check settings, private config and the database")
    dry = sub.add_parser("dry-run", help="run one report in memory and print its trace")
    dry.add_argument("--report", type=ReportType, choices=list(ReportType), required=True)
    dry.add_argument("--date", type=date.fromisoformat, default=None, help="trading date, IST")
    sub.add_parser("scheduler", help="run the always-on scheduler and queue worker")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    try:
        if args.command == "check":
            return cmd_check(settings)
        if args.command == "dry-run":
            return cmd_dry_run(settings, args.report, args.date or now_ist().date())
        return cmd_scheduler(settings)
    except PrivateConfigError as exc:
        log.error("%s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
