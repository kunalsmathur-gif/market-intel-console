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
| `examples/private-config/` | A fake stand-in for that repo, used by tests |

## Not built yet

Collectors (Upstox with the daily login, FRED, CoinGecko, NSDL, RSS, GDELT, search), claim extraction, story grouping, report templates, PDF and citation pack, Telegram and email senders, the NSE file upload via Telegram, and the eval harness. Until the collectors exist, every run ends as **withheld**, which is the intended fail-closed behaviour.

## Deploying on Railway

Create a service from this repo with root directory `/` and config file `apps/worker/railway.json`. Set the variables from `.env.example`. The private config repo still needs a way into the container, for example cloning it at build time with a read-only deploy token; that's decided with the deploy task.

## Windows note

Windows Application Control on the development PC blocks some compiled Python extensions: psycopg's binary build, and the compiled mypy (install it with `--no-binary mypy`). Commands that don't touch the database work as they are. For database commands, set `PSYCOPG_IMPL=python` and put a `libpq.dll` on `PATH`.
