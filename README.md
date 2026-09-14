# Citebell

**Verified before the bell.**

A fact-checked market console for an Indian F&O trader. Scheduled Claude agents collect financial, geopolitical, tech and crypto news from trusted sources. Every claim is fact-checked and cited before it appears. Built for one trader first, and shaped so it can become a subscription product later.

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

## Docs

- [Product Requirements Document](docs/PRD.md) (Markdown)
- [PRD with hi-fi clickable wireframes](docs/prd.html). Download it and open it in a browser.
- [Planning record](docs/PLAN.md)
- [Design system](design-system/citebell/MASTER.md), generated with ui-ux-pro-max plus brand refinements

## Project tooling

- `vendor/ui-ux-pro-max-skill`: [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT) as a git submodule, registered as a Claude Code plugin in `.claude/settings.json`. Clone with `git clone --recurse-submodules`.

## Status

PRD v1.2 is drafted, including technical architecture decisions (PRD §8); AI models are chosen per step by an OpenRouter bake-off (§8.12). The V0 build ("proof of trust") has not started.

## Disclaimer

Market information for personal use, not investment advice. Market data and news belong to their respective publishers and exchanges.
