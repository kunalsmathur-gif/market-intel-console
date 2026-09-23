"""Command line entry point.

    citebell-worker check                     settings, private config and database reachability
    citebell-worker dry-run --report morning  run the pipeline in memory, print the trace
    citebell-worker scheduler                 the always-on process that Railway runs
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import httpx

from citebell_schemas import ReportType, RunKey, RunStatus, SourceKind

from .config import Settings, get_settings
from .llm import LLMRouter
from .pipeline.check import make_check_step
from .pipeline.extract import make_extract_step
from .pipeline.gate import GatePolicy
from .pipeline.market_sources import build_market_collect_step
from .pipeline.publish import publish_report
from .pipeline.runner import RunContext, Step, gate_step, run_pipeline
from .pipeline.templates import REPORT_TEMPLATES
from .pipeline.verify import make_news_verify_step
from .pipeline.write import make_write_step
from .private_config import PrivateConfig, PrivateConfigError
from .private_config_remote import load_configured_private_config
from .schedule import IST, SCHEDULE, is_trading_day, now_ist

if TYPE_CHECKING:
    import psycopg

log = logging.getLogger("citebell_worker")

QUEUE_POLL_SECONDS = 10
MISFIRE_GRACE_SECONDS = 600


def default_policy(now: datetime) -> GatePolicy:
    # One window for every section for now; per-section windows arrive with the report templates.
    return GatePolicy(now=now, stale_before=now - timedelta(hours=24))


def _time_minus_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(date(2000, 1, 1), t) - timedelta(minutes=minutes)).time()


def _load_config(settings: Settings) -> PrivateConfig:
    config, source = load_configured_private_config(settings)
    log.info("private config: %s (%d sources)", source, len(config.sources))
    if source.startswith("public example"):
        log.warning("no private config set: using the public example config")
    if not any(day.year == now_ist().year for day in config.holidays):
        log.warning("no NSE holidays listed for %s: every weekday counts as a trading day",
                    now_ist().year)
    return config


def _load_upstox_token(conn: "psycopg.Connection[Any]") -> str | None:
    """The owner's Upstox token expires daily (PRD §9.3); a missing or expired one just
    means the run collects no Upstox index numbers, not a run failure."""
    from . import credentials

    try:
        return credentials.load_credential(conn, "upstox").access_token
    except credentials.CredentialsError as exc:
        log.warning("upstox: %s", exc)
        return None


def _build_steps(
    settings: Settings,
    config: PrivateConfig,
    client: httpx.Client,
    report_type: ReportType,
    upstox_access_token: str | None = None,
) -> list[tuple[str, Step]]:
    """Collect, extract+verify news claims, gate, then write and check (PRD §7). Every connector
    or LLM
    provider with credentials available runs; anything unconfigured is silently left out with
    a warning, so a run still produces whatever it can rather than failing outright."""
    steps: list[tuple[str, Step]] = []
    collect_step = build_market_collect_step(
        client,
        config.sources,
        settings.fred_api_key.get_secret_value() if settings.fred_api_key else None,
        settings.coingecko_api_key.get_secret_value() if settings.coingecko_api_key else None,
        upstox_access_token,
    )
    if collect_step is not None:
        steps.append(("collect", collect_step))
    else:
        log.warning("no data-connector credentials set: the run will collect no market numbers")

    rss_sources = [s for s in config.sources if s.active and s.kind is SourceKind.RSS]
    llm_configured = settings.gemini_api_key is not None or settings.openrouter_api_key is not None
    router: LLMRouter | None = None
    if not rss_sources:
        log.warning("no active RSS sources configured: the run will extract no news claims")
    elif not llm_configured:
        log.warning("no LLM provider API key set: the run will extract no news claims")
    else:
        try:
            extract_prompt = config.prompt("extract")
            verify_prompt = config.prompt("verify")
        except PrivateConfigError as exc:
            log.warning("news extract/verify skipped: %s", exc)
        else:
            router = LLMRouter(settings, client)
            steps.append(("extract", make_extract_step(client, router, extract_prompt, rss_sources)))
            steps.append((
                "verify",
                make_news_verify_step(
                    client, router, verify_prompt,
                    reject_confirmations=settings.verify_reject_confirmations,
                ),
            ))

    steps.append(("gate", gate_step))

    if not llm_configured:
        log.warning("no LLM provider API key set: the run will publish no written sections")
    else:
        try:
            write_prompt = config.prompt("write")
        except PrivateConfigError as exc:
            log.warning("write step skipped: %s", exc)
        else:
            router = router or LLMRouter(settings, client)
            write_template = REPORT_TEMPLATES[report_type]
            steps.append(("write", make_write_step(write_template, router, write_prompt)))
            steps.append(("check", make_check_step()))

    return steps


def _upstox_status_message(conn: "psycopg.Connection[Any]") -> str:
    """A one-line human status for cmd_check and the scheduler's freshness job — never raises."""
    from . import credentials

    credential = credentials.get_credential_status(conn, "upstox")
    if credential is None:
        return "not connected — set it on the Settings page"
    if credential.expired:
        return f"expired at {credential.expires_at.isoformat()} — reconnect on the Settings page"
    return f"valid until {credential.expires_at.isoformat()}"


def cmd_check(settings: Settings) -> int:
    config = _load_config(settings)
    print(f"private config: {config.root} ({len(config.sources)} sources, "
          f"{len(list((config.root / 'prompts').glob('*.md')))} prompts)")
    for slot in SCHEDULE.values():
        start = slot.collect_start.strftime("%H:%M") if slot.collect_start else "on upload"
        print(f"  {slot.title:<22} collect {start:<9} deadline {slot.deadline:%H:%M} IST")
    if settings.database_url is None:
        print("database: DATABASE_URL not set")
        return 0
    import psycopg  # only commands that touch the database load the driver

    with psycopg.connect(settings.database_url.get_secret_value(), connect_timeout=10) as conn:
        conn.execute("select 1")
        upstox_status = _upstox_status_message(conn)
    print("database: reachable")
    print(f"upstox token: {upstox_status}")
    return 0


def cmd_dry_run(settings: Settings, report: ReportType, trading_date: date) -> int:
    config = _load_config(settings)
    ctx = RunContext(key=RunKey(report_type=report, trading_date=trading_date),
                     policy=default_policy(now_ist()))
    upstox_access_token = None
    if settings.database_url is not None:
        import psycopg

        with psycopg.connect(settings.database_url.get_secret_value(), connect_timeout=10) as conn:
            upstox_access_token = _load_upstox_token(conn)
    with httpx.Client() as client:
        outcome = run_pipeline(ctx, _build_steps(settings, config, client, report, upstox_access_token))
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
            upstox_access_token = _load_upstox_token(conn)
            with httpx.Client() as client:
                outcome = run_pipeline(
                    ctx, _build_steps(settings, config, client, run.key.report_type, upstox_access_token)
                )
            with conn.transaction():
                if outcome.status in (RunStatus.PUBLISHED, RunStatus.PARTIAL):
                    publish_report(conn, ctx, run.id)
                queue.finish_run(conn, run.id, outcome.status, outcome.trace, outcome.error)
        log.info("run %s %s: %s", run.id, run.key, outcome.status)

    def check_upstox_token() -> None:
        """Surfaces a missing/expired token in the scheduler's own logs before the first
        collect run of the day (Morning Insights collects from 07:30 IST; the owner's daily
        login task is due before then, PRD §9.3) — no separate alert channel exists yet."""
        today = now_ist().date()
        if not is_trading_day(today, config.holidays):
            return
        with psycopg.connect(dsn, autocommit=True) as conn:
            status = _upstox_status_message(conn)
        log.log(logging.INFO if "valid until" in status else logging.WARNING,
                "upstox token: %s", status)

    def heartbeat(ping_url: str) -> None:
        # Proves the process and its database connection are alive; the monitor alerts on silence.
        try:
            with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
                conn.execute("select 1")
            httpx.get(ping_url, timeout=10)
        except (psycopg.Error, httpx.HTTPError) as exc:
            log.warning("heartbeat skipped: %s", exc)

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
    upstox_check_time = _time_minus_minutes(SCHEDULE[ReportType.MORNING].collect_start or time(7, 30), 15)
    scheduler.add_job(check_upstox_token,
                      CronTrigger(day_of_week="mon-fri", hour=upstox_check_time.hour,
                                  minute=upstox_check_time.minute, timezone=IST),
                      id="check-upstox-token", coalesce=True, misfire_grace_time=MISFIRE_GRACE_SECONDS)
    if settings.healthcheck_ping_url:
        scheduler.add_job(heartbeat, "interval", seconds=settings.heartbeat_seconds, id="heartbeat",
                          args=[settings.healthcheck_ping_url], coalesce=True, max_instances=1,
                          next_run_time=datetime.now(IST))
    else:
        log.warning("HEALTHCHECK_PING_URL is not set: nothing will notice if the worker stops")
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
    # The queue is polled every few seconds; keep library chatter out of the Railway logs.
    for noisy in ("apscheduler", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
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
