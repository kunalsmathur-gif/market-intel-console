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
