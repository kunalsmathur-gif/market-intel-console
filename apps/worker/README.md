# Citebell worker

Python 3.12. It does all fetching, model calls, verification and publishing on a schedule, and runs as one always-on container on Railway (PRD §8.1, §8.11).

```bash
cd apps/worker
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/python
cp .env.example .env

citebell-worker check                                    # settings, private config, database
citebell-worker dry-run --report morning --date 2026-09-15
citebell-worker scheduler                                # what Railway runs
```

Checks: `pytest`, `ruff check src tests ../../packages/schemas/src`, `mypy src tests ../../packages/schemas/src`.

## Layout

| Path | What it does |
|---|---|
| `schedule.py` | Report timetable in IST and trading-day checks |
| `pipeline/gate.py` | The publish gate: badge rules, tolerances, syndication, stale and broken evidence. Code, not a prompt; fails closed |
| `pipeline/runner.py` | Runs the steps in order, traces each one, withholds a run that has nothing verified |
| `llm/` | Provider-neutral JSON calls: Gemini (direct key) and OpenRouter, with a model and backup per step |
| `queue.py` | Report runs as a Postgres queue: idempotent enqueue, `SKIP LOCKED` claims, one scheduler via an advisory lock |
| `private_config.py` | Loads prompts, the source registry and NSE holidays from the private config repo |
| `private_config_remote.py` | Downloads that repo's config files from GitHub at a pinned commit (production) |
| `examples/private-config/` | A fake stand-in for that repo, used by tests |

## Not built yet

Collectors (Upstox with the daily login, FRED, CoinGecko, NSDL, RSS, GDELT, search), claim extraction, story grouping, report templates, PDF and citation pack, Telegram and email senders, the NSE file upload via Telegram, and the eval harness. Until the collectors exist, every run ends as **withheld**, which is the intended fail-closed behaviour.

## Deploying on Railway

Follow [docs/setup/production.md](../../docs/setup/production.md). In short:
- Create a service from this repo with root directory `/` and config file `apps/worker/railway.json`, and set the variables from `.env.example`.
- The private config is downloaded at startup from `PRIVATE_CONFIG_REPO` at `PRIVATE_CONFIG_REF`, using a read-only fine-grained token (`private_config_remote.py`). Only `sources.toml`, `nse_holidays.txt` and `prompts/` are fetched, never the recorded eval days. Each commit is cached, and the log names the commit in use.
- The scheduler pings `HEALTHCHECK_PING_URL` every 5 minutes after checking the database connection.

## Windows note

Windows Application Control on the development PC blocks some compiled Python extensions: psycopg's binary build, and the compiled mypy (install it with `--no-binary mypy`). Commands that don't touch the database work as they are. For database commands, set `PSYCOPG_IMPL=python` and put a `libpq.dll` on `PATH`.
