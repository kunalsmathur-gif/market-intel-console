# Citebell

**Verified before the bell.**

A fact-checked market console for an Indian F&O trader. A scheduled worker collects financial, geopolitical, tech and crypto news from trusted sources. Every claim is fact-checked and cited before it appears. Built for one trader first, and shaped so it can become a subscription product later.

*(Working name was "Market Intel Console"; the repo keeps that slug for now.)*

## Daily reports (IST)

| Report | Ready by |
|---|---|
| Morning Insights | 8:45 AM |
| Mid-day Markets | 12:15 PM |
| End-of-day Insights | 4:00 PM |
| Institutional Flows (FII/DII and others) | 8:00 PM |

The console also shows charts for Indian and global indices (Nifty 50, Bank Nifty, Sensex, S&P 500, Nasdaq, Nikkei 225, Hang Seng and more), Bitcoin, and tech news that can move markets.

## Core rule

**Nothing is published without verification.** Every claim carries a source link, publisher, timestamp and source tier. Anything that fails verification is left out.

## Repository layout

| Path | What it is | Runs on |
|---|---|---|
| [`apps/web`](apps/web) | Next.js 16 + Tailwind web app. Reads and displays only; owner sign-in with a Supabase magic link | Vercel |
| [`apps/worker`](apps/worker) | Python worker: schedule, collect, verify, publish. Holds every model and data key | Railway |
| [`packages/schemas`](packages/schemas) | Data shapes defined once as Pydantic models, exported to JSON Schema and TypeScript | both |
| [`infra/supabase`](infra/supabase/migrations) | Database schema: append-only facts and claims, run queue, alerts outbox, owner-only RLS | Supabase (Mumbai) |
| [`evals`](evals) | Eval harness and model bake-off (test data lives in the private config repo) | CI |

Prompts, the source registry and eval goldens live in a **separate private repo**, loaded by the worker from `PRIVATE_CONFIG_DIR`.

## Getting started

- **Worker:** see [apps/worker/README.md](apps/worker/README.md). `citebell-worker dry-run --report morning` works without any keys.
- **Web app:** see [apps/web/README.md](apps/web/README.md).
- **Database:** with the Supabase CLI, run these once from the repo root: `npx supabase init --workdir infra`, `npx supabase link --project-ref <ref> --workdir infra`, then `npx supabase db push --workdir infra`. Then add the owner's email to `public.allowed_users`.
- **CI:** [.github/workflows/ci.yml](.github/workflows/ci.yml) runs worker lint, types and tests; database tests against Postgres 17 (migrations, RLS, append-only guards, run queue); a web lint, typecheck and build; and a check that the generated TypeScript matches the Python models.

## Docs

- [Product Requirements Document](docs/PRD.md) (Markdown)
- [PRD with hi-fi clickable wireframes](docs/prd.html). Download it and open it in a browser.
- [Planning record](docs/PLAN.md)
- [Design system](design-system/citebell/MASTER.md), generated with ui-ux-pro-max plus brand refinements

## Project tooling

- `vendor/ui-ux-pro-max-skill`: [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT) as a git submodule, registered as a Claude Code plugin in `.claude/settings.json`. Clone with `git clone --recurse-submodules`.

## Status

PRD v1.3 is complete. **V0 build ("proof of trust") has started with the scaffold:**
- the worker skeleton with the publish gate, model router and run queue
- the database schema
- the web app shell with sign-in
- CI

V0 decisions (PRD appendix):
- Upstox for India market data.
- NSE-only files downloaded by hand and sent to the Telegram bot.
- Prompts and the source registry in a private repo.

Next: data collectors, starting with Upstox and its daily login.

## Disclaimer

Market information for personal use, not investment advice. Market data and news belong to their respective publishers and exchanges.
