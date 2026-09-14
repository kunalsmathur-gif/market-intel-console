# Plan: PRD for Market Intel Console

*Planning record, 14 Sep 2026. The PRD itself is in [PRD.md](PRD.md) and [prd.html](prd.html).*

## Context
The user trades Indian F&O on their own account and starts work at the 9:00 AM IST pre-open. Their pre-market work is spread across Moneycontrol, Mint, Morningstar, Reuters, NSE pages, charting apps and more. They want one console where scheduled Claude agents produce four fact-checked reports (8:45 AM, 12:15 PM, 4:00 PM, 8:00 PM IST). The console also needs charts for global indices, Bitcoin, and tech news. The most important requirement: **every item must be fact-checked and cited with links. Nothing unverified gets published.**

## Decisions confirmed with the user
- **Audience:** personal use only, not a publishing business.
- **Build path:** scheduled Claude agents plus a light web app (Next.js).
- **Format:** HTML PRD with clickable hi-fi wireframes, plus a Markdown copy. All artefacts live in this repo under `docs/`.
- **Repository:** `kunalsmathur-gif/market-intel-console` (public).
- **Naming:** the user's sample report templates are layout and content references only. Any business name, tagline or registration number printed on them must never be used in this project. Working product name: **Market Intel Console (MIC)**.
- **Reference templates stay out of git** (third-party material). `.gitignore` excludes `reference-templates/`.

## Later decisions (same session)
- **Brand name: Citebell**, tagline "Verified before the bell." Chosen as design lead with the ui-ux-pro-max design system. Around 80 candidates were screened; all five Citebell domains (.com, .app, .in, .ai, .io) were unregistered via RDAP on 14 Sep 2026. A formal trademark search is still required. Details in PRD §5.
- **Market-ready UX** section (PRD §11) and SaaS screens (W11: landing, pricing, onboarding) added.
- **Design system** persisted to `design-system/citebell/MASTER.md`, with design-lead refinements at the top.
- **Skill:** ui-ux-pro-max added as a git submodule at `vendor/ui-ux-pro-max-skill` and enabled via `.claude/settings.json`.

## v1.1: technical architecture decisions (same day)
The user raised 12 architecture questions (frontend/backend split, LangChain/Python, APIs vs MCP, free vs paid data, auth, downloads, alerts, building on stored data, caching/RAG, eval suites, latency/scale, model choice). They're answered in PRD §8 and backed by fresh pricing and terms checks. Corrections to v1.0 made along the way:
- "Claude Agent SDK" replaced by a Python worker calling the Claude API directly.
- Reuters has no public RSS; it's reached through allow-listed web search instead.
- "Archived snapshot" replaced by a Wayback Machine capture plus a content fingerprint, so full-page copies aren't stored.
- NSE's Terms of Use prohibit automated data collection, so NSE-only datasets are an open decision.
- Scheduling moved off GitHub Actions, which can delay or drop scheduled jobs.
- New "News-reported" badge for V0 values that have no primary feed.
- Breaking-news alerts capped at 5 per day, with report-ready alerts excluded from the cap.

## v1.2: model choice by bake-off (same day)
The Claude Opus 5 plan (~US$85–100 a month) was too expensive for the user. The user has an OpenRouter account for multi-model evals and existing Supabase, Railway and Vercel subscriptions. Changes:
- PRD §8.12 now picks models per step through an OpenRouter bake-off. The shortlist has 12 models with live prices, including Gemini 2.5 Flash. The bake-off scores accuracy, judgement, faithfulness, format, latency, cost and stability, with pass bars and a decision rule.
- Monthly cost options now run from ~US$3–18 (budget model) to ~US$20–33 (Gemini 2.5 Flash plus a strong verifier), against ~US$82–95 for all Opus 5.
- Search is provider-neutral: a search API called from code with a domain allow-list, because Google's search can't be domain-filtered through OpenRouter.
- The worker is hosted on Railway, and the existing plans are reused.
- Fixed a mobile overflow bug in the HTML masthead.

## v1.3: budget and pricing section (same day)
The user asked what it costs to build and run using free data sources and a direct Gemini API key (2.5 or 3.5 Flash-Lite), and what's lost without paid sources. PRD §9 now has:
- one-time cash (~US$20–40) and effort (26–36 developer days; 8–10 weeks end to end)
- monthly running cost (~US$2–25) and upkeep (6–10 h/month plus a daily Upstox login)
- the gaps in the free plan
- a plan comparison and triggers for when to pay for more

Also: V0 duration in phasing corrected from ~3 weeks; USD/INR reference rate attributed to FBIL (not RBI); cost guardrail tied to the §9 budget. Later sections renumbered (phasing is now §10).

## Inputs reviewed
- Sample morning outlook reports (3 pages: Global Opening Check / India Setup & Flows / Data Outlook).
- Older text pre-market briefs (May–Jul 2026).
- Sample mid-day pulse, post-market and institutional-flow report images.
- Web searches on competitor features (sources listed in PRD §3).

## Execution steps
1. Load the design and data-viz guidance used for the HTML page.
2. Write `docs/prd.html`. It will be one document with a sticky table of contents, sections §1–§12, Mermaid diagrams (architecture and user flow), and a wireframe gallery of screens W1–W9 built as real HTML/CSS mockups. All sample numbers are labelled "illustrative".
3. Write `docs/PRD.md` with the same content in Markdown; wireframes appear as layout specs.
4. Name check: both files are searched for any business name taken from the reference templates. Zero hits are required.
5. Publish the HTML as a private Artifact for easy viewing; commit and push everything to the repo.

## PRD outline
1. Business context & objective
2. Problems the user faces
3. Competitors & key features
4. Differentiation
5. Features to copy from competitors
6. High-level solution (architecture, data layer, verification rules, report schedule, charts, stack)
7. Phasing: V0 → Nirvana
8. What else makes it holistic
9. User flows
10. High-fidelity wireframes
11. Success metrics
12. Guardrail metrics
- Appendix: risks, assumptions, open questions, glossary

## Verification of the deliverable
- Business-name scan of all committed files: 0 hits.
- HTML renders: TOC links work, wireframe tabs switch, Mermaid renders, no horizontal scroll on mobile, both light and dark themes readable.
- Every competitor claim links to a source; all wireframe data is labelled illustrative.
