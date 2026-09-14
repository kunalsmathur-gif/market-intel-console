"""Database tests: the Supabase migrations applied to a real Postgres with stubbed auth and storage.

Uses TEST_DATABASE_URL when set (CI's Postgres service). Otherwise starts an embedded PostgreSQL
with pgserver. Each test gets a fresh database cloned from a migrated template.

On a Windows PC where Application Control blocks psycopg's compiled build, set PSYCOPG_IMPL=python;
this file puts pgserver's libpq on PATH for it.
"""

from __future__ import annotations

import importlib
import json
import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

pgserver: Any = None
if not os.environ.get("TEST_DATABASE_URL"):
    try:
        pgserver = importlib.import_module("pgserver")
    except ImportError:  # pragma: no cover - only without TEST_DATABASE_URL
        pass
    else:
        _bin = Path(pgserver.__file__).parent / "pginstall" / "bin"
        os.environ["PATH"] = f"{_bin}{os.pathsep}{os.environ.get('PATH', '')}"

import psycopg  # noqa: E402  (must follow the PATH setup above)
import pytest  # noqa: E402
from psycopg.conninfo import make_conninfo  # noqa: E402

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
STUBS = Path(__file__).with_name("supabase_stubs.sql")
TEMPLATE = "citebell_template"

OWNER_ID = "11111111-1111-1111-1111-111111111111"
STRANGER_ID = "22222222-2222-2222-2222-222222222222"
OWNER_EMAIL = "owner@example.com"
STRANGER_EMAIL = "stranger@example.com"


@pytest.fixture(scope="session")
def admin_url() -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    if pgserver is None:
        pytest.skip("set TEST_DATABASE_URL or `pip install pgserver` to run database tests")
    server = pgserver.get_server(Path(tempfile.mkdtemp(prefix="citebell-pg-")), cleanup_mode="stop")
    yield server.get_uri()


@pytest.fixture(scope="session")
def template(admin_url: str) -> str:
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(f"drop database if exists {TEMPLATE} with (force)")
        admin.execute(f"create database {TEMPLATE}")
    with psycopg.connect(make_conninfo(admin_url, dbname=TEMPLATE), autocommit=True) as conn:
        conn.execute(STUBS.read_text(encoding="utf-8"))
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(migration.read_text(encoding="utf-8"))
    return TEMPLATE


@pytest.fixture
def db_url(admin_url: str, template: str) -> Iterator[str]:
    name = f"t_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(f"create database {name} template {template}")
    try:
        yield make_conninfo(admin_url, dbname=name)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(f"drop database if exists {name} with (force)")


@pytest.fixture
def db(db_url: str) -> Iterator[psycopg.Connection[Any]]:
    with psycopg.connect(db_url, autocommit=True) as conn:
        yield conn


@pytest.fixture
def seeded(db: psycopg.Connection[Any]) -> dict[str, Any]:
    """One source, run, claim and report, plus the owner and a stranger in auth.users."""
    db.execute(
        """insert into public.sources (id, name, domain, tier, kind)
           values ('rbi', 'RBI', 'rbi.org.in', 'T1', 'api')"""
    )
    run_id = db.execute(
        """insert into public.report_runs (report_type, trading_date, deadline_at)
           values ('morning', '2026-09-15', '2026-09-15 08:45+05:30') returning id"""
    ).fetchone()[0]  # type: ignore[index]
    db.execute(
        """insert into public.claims (id, run_id, claim_type, text, verdict, badge)
           values ('c1', %s, 'news_event', 'RBI kept the repo rate unchanged', 'publish', 'verified')""",
        (run_id,),
    )
    report_id = db.execute(
        """insert into public.reports (run_id, report_type, trading_date, version, title)
           values (%s, 'morning', '2026-09-15', 1, 'Morning Insights') returning id""",
        (run_id,),
    ).fetchone()[0]  # type: ignore[index]
    db.execute(
        "insert into auth.users values (%s, %s), (%s, %s)",
        (OWNER_ID, OWNER_EMAIL, STRANGER_ID, STRANGER_EMAIL),
    )
    db.execute("insert into public.allowed_users (email) values (%s)", (OWNER_EMAIL,))
    return {"run_id": run_id, "report_id": report_id, "claim_id": "c1"}


@contextmanager
def acting_as(
    conn: psycopg.Connection[Any], user_id: str | None, email: str | None = None
) -> Iterator[None]:
    """Run statements as Supabase's anon role (user_id None) or as a signed-in user."""
    role = "anon" if user_id is None else "authenticated"
    claims = {} if user_id is None else {"sub": user_id, "email": email, "role": role}
    conn.execute(f"set role {role}")
    conn.execute("select set_config('request.jwt.claims', %s, false)", (json.dumps(claims),))
    try:
        yield
    finally:
        conn.execute("reset role")
        conn.execute("select set_config('request.jwt.claims', '', false)")


def count(conn: psycopg.Connection[Any], table: str) -> int:
    row = conn.execute(f"select count(*) from {table}").fetchone()
    assert row is not None
    return int(row[0])
