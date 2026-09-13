# Citebell: Product Requirements Document

**Verified before the bell.**

| | |
|---|---|
| Version | v1.0, draft for review |
| Date | 14 Sep 2026 |
| Product | Citebell (working name was "Market Intel Console") |
| Audience | Personal use first; SaaS-ready by design |
| Visual version | [`prd.html`](prd.html) has the hi-fi clickable wireframes. Download it and open it in a browser. |

> Wireframe figures, headlines and tickers are illustrative sample data, not real market information. Citebell provides market information, not investment advice.

---

## Contents
1. [Business context & objective](#1-business-context--objective)
2. [Problems the user faces](#2-problems-the-user-faces)
3. [Competitors and their key features](#3-competitors-and-their-key-features)
4. [How Citebell is different](#4-how-citebell-is-different)
5. [Brand: name & identity](#5-brand-name--identity)
6. [Features to copy from competitors](#6-features-to-copy-from-competitors)
7. [High-level solution](#7-high-level-solution)
8. [Phasing: V0 → Nirvana](#8-phasing-v0--nirvana)
9. [What else makes it holistic](#9-what-else-makes-it-a-holistic-platform)
10. [User flows](#10-user-flows)
11. [Market-ready UX](#11-market-ready-ux)
12. [High-fidelity wireframes](#12-high-fidelity-wireframes)
13. [Success metrics](#13-success-metrics)
14. [Guardrail metrics](#14-guardrail-metrics)
- [Appendix: risks, assumptions, open questions, sources](#appendix)

---

## The trading day in IST (September timings)

| Session | IST |
|---|---|
| Tokyo | 05:30–12:00 |
| Hong Kong | 07:00–13:30 |
| NSE / BSE | pre-open 09:00, regular 09:15–15:30 |
| London | 12:30–21:00 |
| New York | 19:00–01:30 |
| **Citebell drops** | **08:45 · 12:15 · 16:00 · 20:00** |

After the clocks change (UK 25 Oct, US 1 Nov 2026), London and New York start and end one hour later in IST.

---

## 1. Business context & objective

**The user** is a solo Indian F&O trader (Nifty and Bank Nifty index options, plus stock F&O). Their decisions cluster at the pre-open (09:00–09:08 order entry) and the 09:15 open. Trades are rechecked around midday and reviewed after the 15:30 close.

**What moves their book:** overnight US and Asia sessions, GIFT Nifty, crude, USD/INR, DXY, US yields, FII/DII flows, OI, PCR and max pain, India VIX, the F&O ban list, scheduled events (RBI, Fed, CPI, results), geopolitics (shipping lanes, sanctions, conflict, tariffs), tech news (AI capex and semiconductors feed Nasdaq, which feeds Nifty IT), and Bitcoin as a gauge of risk appetite.

**Objective:** one trusted source for every trading decision. Four on-time, fact-checked reports each trading day, cross-market charts, and a citation on every claim. The trader stops researching and spends that time deciding.

**Business objective (later):** prove the verification engine on one demanding user, then package it as a subscription for Indian retail F&O traders and investors. The paid promise is trust.

| Goal | Target | Why it matters |
|---|---|---|
| Pre-market research time | ≤ 15 min | Frees the 08:45–09:15 window for decisions |
| Claims with a working citation | 100% | The product's core promise |
| Unverified claims published | 0 | One wrong number costs more trust than ten right ones earn |
| Reports delivered on time | ≥ 98% | A late morning report is a useless morning report |

**Non-goals:** placing orders; buy/sell calls or price targets in Citebell's own voice (third-party views appear only with attribution); tick-level data for scalping; social media as a source.

## 2. Problems the user faces

| # | Problem | What it looks like today | Cost |
|---|---|---|---|
| P1 | Too many sources | 10+ tabs: Moneycontrol, Mint, Business Standard, Reuters, CNBC, NSE, NSDL, Investing.com, TradingView, X | An estimated 60–90 min before the open *(assumption; measure in V0)* |
| P2 | Fact-checking is manual | Provisional vs final FII data, Brent front-month vs next-month, old articles resurfacing, rumours on X and Telegram | Wrong inputs lead to wrong positions |
| P3 | Hand-built reports drift | Seen in the sample reports reviewed for this PRD: a file suffixed `_Corrected`; Brent given as $108.31, "$108" and "near $109" within one morning report; a typo in a July brief | Rework and lost trust |
| P4 | Synthesis is hard | The same story appears in eight outlets; turning it into "what does this mean for Nifty and Bank Nifty" is manual | Mental load right at 09:00 |
| P5 | Unclear freshness | It's often unclear what "as of" time a number refers to | Decisions made on stale data |
| P6 | Tight timing | US close is 01:30 IST, Tokyo opens 05:30, Hong Kong 07:00, and the report is due 08:45 | No room for a slow workflow |
| P7 | Missed events | Ban list, expiry calendar, SEBI circulars, results, macro data releases | Surprise risk on open positions |
| P8 | Charts live in other apps | No single cross-asset view | Correlations go unnoticed |
| P9 | Paywalls | Mint, Business Standard, FT, Bloomberg | Only part of a story gets read |
| P10 | No memory | No record of how a story evolved, or which news came before a win or a loss | No learning loop |

## 3. Competitors and their key features

Features and prices were checked by web search on 14 Sep 2026. Prices come from third-party reviews and may be out of date; verify before relying on them.

| Product | Key features | Gaps for this trader | Indicative price |
|---|---|---|---|
| Moneycontrol app + Pro | News, FII/DII data, results, alerts, portfolio tracking, analyst trade ideas | Ad-heavy; no claim-level citations; mostly India; promotional content mixed in | Pro ~₹699/yr [R1] |
| Mint · Business Standard · ET | Quality reporting, explainers, live market blogs | One outlet's view each; paywalls; no synthesis across sources | Subscriptions |
| Zerodha Pulse | Last 24 h of business news from major Indian outlets in one feed; related stories grouped; web, apps and browser extension | Headlines only; no verification; little global or crypto depth; no charts | Free [R2] |
| Perplexity Finance | Live NSE/BSE prices, market summaries with citations, watchlists, earnings-call transcripts, SEBI filing summaries | On demand, not scheduled; no fixed F&O report format; no flows or OI view | Free tier [R3] |
| Bloomberg Terminal · LSEG Workspace | Fast verified wire news (Reuters inside Workspace), urgency flags, calendars with consensus, deep data | Built for institutions; far beyond a personal budget; no personal synthesis | Enterprise [R5] |
| TradingView | Best-in-class charts, multi-asset coverage, alerts, watchlists; open-source Lightweight Charts (Apache-2.0) | News is secondary; no verification | Free + paid tiers [R6] |
| Koyfin | Custom dashboards; macro, FX, yields and crypto; news; transcripts | US-centric; weak India F&O coverage | Pro ~$69–109/mo [R7] |
| Benzinga Pro | Real-time newsfeed, audio squawk, scanners, calendars | US equities focus; expensive for an Indian retail trader | ~$99–197/mo, reviews differ [R8] |
| Sensibull · Opstra | Option chain, OI, PCR, Greeks, IV, strategy builders, backtesting (Opstra) | Options analytics tools, not news products | Free + paid [R4] |
| StockEdge · Trendlyne | Daily scans, FII/DII data, screeners, fundamentals | Thin on news and synthesis | Free + paid [R9] |
| Investing.com | Global quotes; economic calendar with importance stars and actual / forecast / previous columns | Ads; uneven source quality | Free + paid [R10] |
| AI-native newcomers (Tradar, MarketsEasy) | AI pre-market briefs, scored alerts, live option chain and OI with news | Accuracy unproven; sourcing opaque | Varies [R11] |

## 4. How Citebell is different

Every competitor either has trust without synthesis (wires, terminals) or synthesis without proof (apps, AI summaries). Citebell's position is **synthesis with proof, delivered at fixed times in the trading day.**

1. **Verification-first.** Each claim goes through source tiers, corroboration, a numeric check, a recency check and a publish gate. Anything unverified never appears.
2. **Citations that show their work.** Every citation carries a link, publisher, timestamp, matched quote, source tier and an archived snapshot.
3. **Figures come from data, not articles.** Figures come from exchange and primary feeds and are checked against a second feed. A number has one value everywhere in a report (fixes P3).
4. **Written for F&O.** Each story is tagged with the index or sector it affects, likely direction and time horizon, plus a one-line cause → effect.
5. **Built around the trading day.** Four fixed drops in IST, each opening with what changed since the last report.
6. **Global → India transmission map.** Nasdaq semis → Nifty IT; crude → OMCs, paints, aviation; DXY → INR → FII flows; BTC → risk appetite.
7. **Learns with the trader.** Story timelines, a trade journal that links news to trades, and descriptive pattern statistics (never signals).
8. **Public corrections log.** No ads, no paid placements, no unattributed tips.

## 5. Brand: name & identity

### Recommendation: **Citebell**, tagline *"Verified before the bell."*

- **Meaning.** *Cite* is the product's promise: every claim cited. *Bell* is the market's opening bell and the four scheduled drops.
- **Sound.** Two short syllables, easy to say in English and Hindi. It works as a verb: "Citebell it before you trade."
- **Room to grow.** Not tied to F&O or India. It stretches to equities, crypto and global investors (Citebell Pro, Citebell Desk).
- **Availability.** `.com`, `.app`, `.in`, `.ai` and `.io` were all unregistered at check time; a web search found no company or product using the name.
- **Risk to manage.** "Cite" sounds like "site" and "sight". The logo and exact-match domains carry the spelling.
- **Brand device.** The `[1]` citation marker in the wordmark is the same marker that appears on every claim in the product.

### Name screen

About 80 candidates were generated. Domains were checked via registry RDAP lookups on 14 Sep 2026 (Verisign for .com, Google Registry for .app, NIXI for .in, Identity Digital for .ai and .io). Each lookup was validated against a known-registered domain and a random unregistered one.

| Name | Idea | .com | .app | .in | .ai | .io | Verdict |
|---|---|---|---|---|---|---|---|
| **Citebell** | Cited, delivered on the bell | free | free | free | free | free | **Recommended** |
| Bellproof | Proof before the bell | free | free | free | free | free | Runner-up; can read as "resistant to bells" |
| Groundtick | Ground truth, tick by tick | free | free | free | free | free | Less intuitive; "tick" also means the insect |
| Citetick | A cited tick | free | free | free | free | free | Dropped: too close to TickTick |
| Veracle | Vera (truth) + oracle | taken | free | free | free | — | No .com; "oracle" trademark risk |
| Tapeproof | Proof for the market tape | taken | free | free | free | — | No .com |
| Tickproof | A proven tick | taken | free | free | free | — | No .com; sounds like tick repellent |
| Pramaan · Tathya · Pramana | Hindi/Sanskrit for proof and fact | taken | taken | taken | taken | — | Every domain taken |
| Openbell · Firstbell | The opening bell | taken | taken | taken | taken | — | Every domain taken |

**Before announcing the name:** register all five Citebell domains together ("unregistered" doesn't rule out premium pricing); run a formal trademark search on IP India (classes 9, 36, 41, 42) and on USPTO/WIPO; check social handles, which weren't part of this screen.

### Identity system

Built from the ui-ux-pro-max design-system output for a financial dashboard (data-dense, dark-first, trust blue with amber highlights, Fira pairing), then refined for this brand. See [`design-system/citebell/MASTER.md`](../design-system/citebell/MASTER.md).

| Token | Dark | Light | Use |
|---|---|---|---|
| Ink navy | `#0A1120` | `#F3F5F9` (ground) | Background |
| Bell brass | `#EAAB45` | `#8F5B08` | Brand, citations, as-of chips |
| Signal blue | `#6AA3FF` | `#1F4FD1` | Interactive, primary |
| Advance | `#34C28E` | `#0B7A55` | Up, verified |
| Decline | `#F4697A` | `#BD2A40` | Down |
| Withheld | `#EE8B57` | `#A64B16` | Stale, withheld |

- **Type:** Fira Sans for display and UI (600–700 for headlines, 400 for body); Fira Code for tickers, prices, timestamps and citation marks, with tabular figures. ₹ amounts use Indian digit grouping (₹1,23,456 Cr).
- **Voice, do:** "Brent $96.20, up 1.4% since the NSE close [1][2] · ICE, 08:12 IST." Views are always attributed and linked.
- **Voice, don't:** "Oil is exploding, sell OMCs now!" No number without an as-of time, no hype words, no emoji, no buy/sell calls in Citebell's own voice.

## 6. Features to copy from competitors

| Feature | Borrowed from | How Citebell uses it | Phase |
|---|---|---|---|
| Multi-source aggregation, grouped stories | Zerodha Pulse | A story cluster shows "+5 similar"; syndicated copies are merged and counted as one source | V1 |
| Inline citations; Q&A over news; filing and call summaries | Perplexity Finance | A citation on every claim; Ask Citebell answers only from the verified corpus | V0 / V2 |
| Urgency levels; calendar with consensus | Bloomberg, LSEG | Flash / Breaking / Update tags; actual, consensus and prior values | V1 |
| Interactive charts, compare, alerts, watchlists | TradingView | Lightweight Charts (with attribution); percent-compare overlay; price alerts | V0 / V1 |
| Configurable dashboards; macro panel | Koyfin | Rearrangeable widgets; yields, DXY and commodities panel | V2 |
| Audio squawk; real-time alerts | Benzinga Pro | 2-minute audio morning brief; verified breaking alerts only | V2 |
| FII/DII history; ban list; results calendar; buildup scans | Moneycontrol, StockEdge, Trendlyne | Flows tab; ban-list chip in the Today rail; long/short buildup lists | V0 / V1 |
| OI, PCR, max pain, IV, VIX | Sensibull, Opstra | Display-only derivatives panel | V1 |
| Event importance stars; holiday calendars | Investing.com | 1–3 importance levels with text labels; NSE, US and Asia holidays | V1 |
| Crypto market panel | CoinGecko-style trackers | BTC/ETH, dominance, spot ETF flows, funding rates | V1 |

## 7. High-level solution

### Architecture

```mermaid
flowchart LR
  SCH[Scheduler<br/>IST cron] --> COL
  SRC[(Exchange data · market APIs<br/>RSS · regulators)] --> COL
  subgraph AGENTS[Agent pipeline · Claude Agent SDK]
    COL[Collectors<br/>India · Global · Geopolitics<br/>Tech · Crypto · Flows] --> EXT[Claim extractor]
    EXT --> VER[Independent verifier]
    VER --> WRI[Writer<br/>fills template]
    WRI --> QA[Editor / QA<br/>consistency · rounding · attribution]
    QA --> GATE{Publish gate<br/>fail-closed}
  end
  GATE -- pass --> DB[(Postgres · Supabase<br/>reports · claims · sources · audit)]
  GATE -- fail --> LOG[Audit log + withheld banner]
  DB --> APP[Citebell web app<br/>Next.js PWA]
  DB --> NOTIF[Telegram · email · push]
  VER --> ARC[Link archiver]
```

### Verification pipeline

1. **Extract:** split the draft into atomic claims (number, event, forecast or opinion).
2. **Tier sources:** T1 primary (exchange, regulator, central bank, government statistics, company filing) · T2 established press and wires · T3 context only · TX never publishable (social media, Telegram, unnamed).
3. **Corroborate:** find independent support. Syndicated PTI or Reuters copies count as one source.
4. **Reconcile numbers:** match against T1 data or a second feed within tolerance.
5. **Check links:** HTTP 200, the claim text is on the page, publish time captured, snapshot archived.
6. **Check recency:** reject stale or resurfaced stories; stamp every number with its as-of time.
7. **Gate:** pass → publish with a badge; fail → withhold and log.

| Claim type | Rule to publish | Badge |
|---|---|---|
| Market number | Matches T1 data, or two independent feeds agree within tolerance (index ±0.01%, flows exact to ₹0.01 Cr); always shows an as-of time | Primary data |
| News event | One T1 source, or two independent T2 sources | Verified · N sources |
| Forecast / opinion | Attributed to its author ("Brokerage X expects…") with a link; never in Citebell's voice | Attributed view |
| Fails any rule | Left out and written to the audit log. If a whole section misses its deadline, a banner shows the reason and retry time | Withheld |

### Report schedule

Report fields follow the structure of the sample reports reviewed for this PRD.

| Report | Cutoff → ready | Contents |
|---|---|---|
| Morning Insights | 08:15 → **08:45** | **Global opening check:** GIFT Nifty, S&P and Nasdaq futures, US close, Asia. **India setup & flows:** previous Nifty, Bank Nifty and VIX close; commodities; FII/DII; USD/INR; futures premium. **Data outlook:** PCR, put base and call wall, max pain, expiry, long/short buildup, F&O ban. Also: key takeaway; opening cue, support and key risk; overnight global news, domestic triggers, geopolitics, tech, crypto; today's calendar |
| Mid-day Markets | 11:50 → **12:15** | Main intraday driver and tone; Nifty, Sensex, Bank Nifty, VIX; breadth; sector and stock leaders; cross-asset check (WTI, Brent, gold, silver, DXY, USD/INR); news since 08:45; what changed since the morning; Europe pre-open |
| End-of-day Insights | 15:35 → **16:00** | Market story and close badge; session in one line; three drivers, ranked and cited; sector heat map; breadth; closing OI and PCR snapshot; VIX; market lesson; Europe and US futures; tomorrow's calendar |
| Institutional Flows | exchange release → **20:00** | FII/FPI and DII buy, sell and net; combined flow; 20-day trend; participant-wise OI (FII index futures long/short); NSDL FPI data (T+1); bulk and block deals; insider trades; plain-language explanation; next-day setup; US pre-market and crypto check |

### Charts (Markets tab)

- **India:** Nifty 50, Sensex, Bank Nifty, Fin Nifty, India VIX, GIFT Nifty
- **US:** S&P 500, Nasdaq, Dow, VIX, US 10Y
- **Europe:** FTSE 100, DAX, CAC 40
- **Asia:** Nikkei 225, Hang Seng, Shanghai, Kospi, TAIEX
- **Macro:** DXY, USD/INR, Brent, WTI, gold, silver, copper, India 10Y
- **Crypto:** BTC, ETH, BTC dominance
- **Features:** 1D/5D/1M/3M/1Y, % compare overlay (indexed to 100, one axis), 30-day correlation grid, world market clock

### Data & stack

- **India data:** NSE/BSE indices, bhavcopy, F&O ban list, participant-wise OI, FII/DII provisional; NSDL FPI; NSE IX (GIFT Nifty); broker API (Kite, Dhan or Upstox); SEBI, RBI and PIB circulars; exchange corporate announcements.
- **Global data:** a licensed market-data API (e.g. Twelve Data, EODHD or Polygon) plus a second feed for reconciliation; CME FedWatch; US Treasury; Fed, ECB, BoJ, PBoC; US BLS. Crypto: CoinGecko or Binance public APIs plus ETF flow data.
- **News feeds:** RSS and official feeds from Moneycontrol, Livemint, Business Standard, Economic Times, BusinessLine, CNBC-TV18, Morningstar, Reuters, AP, CNBC, FT and WSJ headlines, Nikkei Asia, SCMP, TechCrunch, The Verge, CoinDesk, The Block.
- **Stack:** Next.js + Tailwind PWA · Supabase Postgres · Claude Agent SDK (a strong model for verification and synthesis, a fast model for classification and dedupe) · cloud-scheduled runs · Telegram bot + email. Store headlines, links and snippets of 25 words or fewer; never full articles.

## 8. Phasing: V0 → Nirvana

| Phase | Scope | Exit gate |
|---|---|---|
| **V0 · Proof of trust** (~3 wks) | Four scheduled reports as HTML/PDF to Telegram and email; ~15 curated sources; verification gate v1 (tiers, link check, match against one feed); citation on every claim; "flag as wrong" on each claim; simple archive; Markets page on chart widgets | 20 trading days in a row: ≥95% on time, zero unverified or wrong claims in spot checks, baseline research time measured |
| **V1 · Console** (~6 wks) | Full web app (Today, Reports, Markets, Flows, Crypto & Tech, Calendar); "what changed" view; story clustering; verification badges; fact-check drawer; corrections log; search and archive; derivatives panel; economic, results and expiry calendars; verified breaking alerts; second-feed reconciliation | Research time ≤ 15 min; usefulness ≥ 4.2/5 |
| **V2 · Analyst** | Ask Citebell (verified corpus only, cited); story timelines; impact tags with historical analogues; trade journal (manual or tradebook import, read-only); watchlist ranking; 2-min audio brief; weekly review | ≥ 70% of trades have a linked rationale |
| **V3 · Co-pilot + SaaS beta** | Descriptive pattern library; scenario planner (crude +5% → sector sensitivity); IV and OI shifts over news times; read-only broker positions → news on held stocks; accounts, onboarding, plans and billing; licensed data for redistribution; legal review of SEBI research-analyst rules | Primary source on ≥ 90% of days; 20 beta users meet the trust guardrails |
| **Nirvana** | A personal trading-intelligence system: continuous verified event stream; source reliability scores learned from each outlet's accuracy and corrections; analysis of which news types came before the best and worst trades; risk-regime detection; Hindi business press; voice interaction; fully auditable; a human in the loop, no auto-trading | The trader opens one app at 08:45 and trusts every line in it |

## 9. What else makes it a holistic platform

- **Calendars:** economic (India + global) with actual, consensus and prior; results and corporate actions; expiry calendar; NSE, US and Asia holidays.
- **Rules tracker:** SEBI F&O changes (lot sizes, margins, expiry rules), taken straight from exchange and SEBI circulars.
- **Derivatives:** OI, PCR, max pain, IV percentile, VIX, participant-wise OI, FII futures long/short ratio.
- **Macro:** RBI policy and system liquidity, Fed path, yields, INR, commodities including natural gas and base metals, IMD monsoon.
- **Crypto:** ETF flows, funding rates, liquidations, Indian crypto regulation and tax news.
- **Discipline:** trade journal; daily loss-limit reminder; warning on high-event-risk days; pre-trade checklist.
- **Alerts:** watchlists, price alerts, verified-story alerts; quiet hours; daily cap.
- **Records:** PDF export, searchable archive, public corrections log.
- **Operations:** system health page (agent runs, source uptime, spend); 2FA; secrets vault.

## 10. User flows

```mermaid
flowchart TD
  A0([08:45 push: Morning ready]) --> A1[Today]
  A1 --> A2[3 ranked takeaways · ~2 min]
  A2 --> A3{Doubt a claim?}
  A3 -- yes --> F1[Tap citation → fact-check drawer]
  F1 --> F2{Looks wrong?}
  F2 -- yes --> F3[Flag as wrong → re-verify ≤ 30 min → corrections log]
  F2 -- no --> A4
  A3 -- no --> A4[GIFT Nifty & Asia charts]
  A4 --> A5[Calendar + F&O ban list]
  A5 --> A6[Mark items relevant]
  A6 --> A7([Trade plan set by 09:00])
  A7 --> C1([12:15 Mid-day: what changed since 08:45])
  C1 --> D1([16:00 EOD: why it moved → tag trades in journal])
  D1 --> E1([20:00 Flows: FII/DII + participant OI → next-day setup → alerts])
  B0([Verified breaking alert]) --> B1[Story card · impact · sources] --> B2[Chart with news marker] --> B3[Journal note]
  G0([Report late or section withheld]) --> G1[Banner: reason + retry time] --> G2[Verified parts readable · last verified data dated] --> G3[Push when complete]
```

- **A · Pre-market (08:45):** push → Today → 3 takeaways (≈2 min) → tap [1] for the fact-check drawer → GIFT Nifty and Asia charts → calendar and ban list → mark items relevant → trade plan by 09:00.
- **B · Verified breaking news:** alert (verified only) → story card with impact and sources → chart with news marker → journal note.
- **C · Mid-day (12:15):** "changed since 08:45" → breadth and leaders → adjust positions.
- **D · End of day (16:00):** why the market moved → tag today's trades against the drivers → market lesson.
- **E · Flows (20:00):** FII/DII and participant OI → next-day setup → set alerts.
- **F · Fact-check & correction:** tap citation → quote, tier, time, archive → flag as wrong → re-verify in ≤ 30 min → corrected with changelog.
- **G · Late or withheld:** banner with reason and retry time → verified sections still readable → last verified data kept with dates → push when complete.
- **H · New subscriber (SaaS, later):** landing → sample report without signup → sign up → 3-step setup (skippable) → first morning report → trial → plan.

## 11. Market-ready UX

UX rules drawn from **ui-ux-pro-max** (financial dashboard, data-dense, density 8/10, subtle motion) and adapted to a product whose main feature is trust.

| Area | Rule |
|---|---|
| Trust patterns | Citation superscripts on every claim; three badges (Primary data · Verified · Attributed view); as-of chip on every number; source-tier chips; visible withheld states; changelog on corrected reports |
| Freshness | IST clock and market-status pills in the top bar; as-of chips turn orange, with an icon and "stale", past their freshness window; never colour alone |
| States | Skeletons reserve space (CLS < 0.1); empty states explain the rule ("No tech story met the two-source rule since 08:45"); errors offer a next step ("Feed B isn't responding. Showing NSE values only. Retry.") |
| Density | 12-column grid, max 1400 px, 13 px UI base, tabular numbers; summary before detail; Indian digit grouping for ₹ |
| Colour & accessibility | ▲▼ glyphs and signs on every change; candles filled vs hollow; 4.5:1 text contrast in both themes; a table view for every chart; aria-live on breaking alerts |
| Motion | 150–300 ms transitions for state changes only; no scrolling tickers or flashing prices; respects reduced-motion settings |
| Speed | `/` search · `J`/`K` next and previous story · `C` citations · `G` then `M` Markets; visible focus rings; 44 px touch targets on mobile |
| Notifications | Report-ready pushes plus verified breaking alerts, capped at 5 per day; quiet hours; digest option; toasts auto-dismiss after 3–5 s |
| Onboarding & pricing (SaaS) | Sample report without signup; 3 skippable setup steps (instruments, report times and channels, watchlist); three plans with the middle one highlighted and 20–30% off annual; FAQ answers "Is this investment advice?" (No.) |
| Themes & screens | Dark by default with a full light theme; breakpoints 375 / 768 / 1024 / 1440; no horizontal scroll; 5-item bottom tab bar on mobile |

## 12. High-fidelity wireframes

The clickable, themed mockups are in **[`prd.html`](prd.html) → §12**, with tabs W1–W11, a light/dark preview toggle and hover tooltips on charts. Layout specs:

| # | Screen | Layout | Key elements |
|---|---|---|---|
| W1 | Today (desktop, 08:52) | Side nav · top bar (search, market pills, IST clock) · report strip ×4 · main column (2.25fr) + right rail (1fr) | 3 ranked takeaways with citations and impact chips; 10 cross-market tiles with as-of chips; 6 sparklines; verified feed with tabs, urgency tags, source chips, "+N similar"; rail: calendar, previous-day flows, F&O ban, derivatives setup, verification health |
| W2 | Morning Insights report | Header with verification summary bar (primary / verified / withheld) · section tabs · content + source rail | Key takeaway with tone chip; GIFT Nifty and US futures tiles; US close and Asia tables; Kospi shown as withheld with reason; cue / support / risk rows; numbered source list with tier and archive |
| W3 | Fact-check drawer | Dimmed report + 440 px right drawer | Claim; rule applied; number check across NSE IX, Feed B and base close; sources with tier, time, quote ≤ 25 words, archived copy; collected → verified → published timeline; Flag as wrong |
| W4 | Markets | Region tabs · timeframe and compare toggles · compare chart (2.1fr) + world clock · correlation grid + small multiples | Three indices indexed to 100 on one axis, legend and direct labels, crosshair tooltip; live session pills; 6×6 correlation grid with signed values |
| W5 | Mid-day Markets | Driver hero with 4 tiles + "changed since 08:45" panel · breadth / leadership / cross-asset · "what this means" | Diff rows tagged UP / DOWN / NEW / FIXED (Kospi withheld at 08:45, now verified) |
| W6 | End-of-day Insights | Story + drivers + lesson (1.5fr) · heat map, closing derivatives, tomorrow (1fr) | Close badge; session in one line; drivers ranked by index-point contribution; 12-sector heat map with signed labels |
| W7 | Institutional Flows | Combined-net hero + official-data card · FII and DII buy/sell bars · 20-session bar chart + participant OI table | ₹ values match W1/W2 exactly; diverging bars with hover; OI in Indian digit grouping |
| W8 | Crypto & Tech | BTC candle chart + stat strip (1.5fr) · tech stories (1fr) | Filled-up / hollow-down candles; ETH, dominance, ETF flows, funding, fear & greed; transmission chains (export rules → US semis → Nasdaq-100 fut → Nifty IT) |
| W9 | Mobile | Three phones | Today brief with tiles and 5-item tab bar; verified breaking alert → story; fact-check bottom sheet; 44 px targets |
| W10 | System states | 2×3 grid | Loading skeleton; section withheld with retry; report running late with progress; empty state; feed error; corrections log |
| W11 | SaaS | Browser frame: nav · hero with sample report · plans · onboarding step | "Verified before the bell." hero; sample report before signup; Free / Pro (highlighted) / Desk; annual toggle; step 1 of 3 "What do you trade?" with Skip |

Illustrative pricing in W11 (Free ₹0 · Pro ₹599/mo annual · Desk ₹1,499/mo annual) is a hypothesis to test with beta users, not a decision.

## 13. Success metrics

**North star: time to trade plan.** Minutes from the 08:45 drop until the trader marks today's plan as set, using only Citebell. Target **≤ 15 minutes**.

| Metric | Definition | Target | How it's measured |
|---|---|---|---|
| Sole-source days | Trading days with no outside research before the open | ≥ 90% | One-tap daily check-in |
| On-time delivery | Reports ready by 08:45 / 12:15 / 16:00 / 20:00 | ≥ 98% each | Scheduler logs |
| Citation coverage | Factual claims with at least one working citation | 100% | Publish-gate audit |
| Corroboration depth | News events with 2+ independent sources | ≥ 90% | Claim store |
| User-found errors | Flags confirmed wrong | 0 target · ≤ 1 per 20 reports | Flag + corrections log |
| Missed major events | Events the user saw elsewhere first | ≤ 1 / month | "Missed story" button |
| Usefulness | Rating per report | ≥ 4.2 / 5 | In-report rating |
| Relevance | Items marked relevant | ≥ 30% | Relevant toggle |
| Engagement | Morning report opened; median read time | ≥ 90% of days · 5–8 min | Analytics |
| Alert usefulness | Verified alerts rated useful | ≥ 80% | Rate in notification |
| Decision linkage (V2) | Trades with a linked news rationale | ≥ 70% | Journal |

**SaaS stage (hypotheses to calibrate in beta):** activation (3 morning reports read in the first 7 days) ≥ 60% · week-4 retention ≥ 50% · trial → paid ≥ 15% · monthly churn ≤ 4%.

## 14. Guardrail metrics

| Guardrail | Threshold | If breached |
|---|---|---|
| Unverified claims published | 0 | **Sev-1:** pull the claim, publish a correction, freeze the rule or source, post-mortem within 24 h |
| Fabricated or non-matching citations | 0 | **Sev-1:** as above, plus add the case to the verifier's regression tests |
| Numbers outside tolerance of primary data | 0 | **Sev-1:** auto-withhold, alert, review the feed |
| Stale numbers | 0 without a valid as-of time | Block publishing that number |
| Dead citation links | 0 at publish · < 2% after 7 days | Serve the archived copy; replace the link |
| Corrections | ≤ 1% of claims · fixed ≤ 30 min after a flag | Review that source's tier |
| Source concentration | No outlet > 30% of a report's citations | Rebalance collectors; syndicated copies count once |
| Advice leakage | 0 buy/sell calls or targets in Citebell's voice | Gate blocks those phrasings; review the template |
| Late or missed reports | > 15 min late ≤ 1 / month · missed = 0 | Incident review; add schedule buffer |
| Alert fatigue | ≤ 5 pushes per trading day | Fold extra alerts into a digest |
| Report length | Morning read ≤ 8 min | Tighten the template |
| Cost | Within the monthly LLM + data budget | Cheaper models for non-critical steps; alert at 80% |
| Licensing | 0 full-article copies · snippets ≤ 25 words | Remove the content; audit the collectors |
| Security | 0 exposed secrets | Rotate keys; scan the repo in CI |

---

## Appendix

### Risks & mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Data licensing | Redistributing exchange data, especially real-time, needs a licence; many news sites forbid scraping in their terms | Personal-use broker and licensed APIs in V0–V2; RSS and official feeds only; exchange or vendor licence before any SaaS launch |
| Regulation | Charging users for market analysis may bring in SEBI research-analyst or investment-adviser rules | Stay factual and attributed; no advice in Citebell's voice; legal advice before V3 billing |
| LLM errors | A model can invent a number or a source | Numbers come from data, never generated text; independent verifier; fail-closed gate; regression set of known-tricky claims |
| Source outages and delays | Exchange files and feeds can arrive late | Second feed; withheld states with retry times; last verified values shown with dates |
| Paywalls | Some claims can't be read in full | Cite only what's verifiable in the free portion, or use an alternative source |
| Over-reliance | A trusted tool can be followed blindly | Clear badges, attributed views, journaling prompts, "information, not advice" copy |
| Name and trademark | A conflict discovered late forces a rebrand | Register domains now; formal trademark search before public launch |

### Assumptions to validate
- Current pre-market research takes 60–90 min (measure in V0).
- The named outlets offer usable RSS or official feeds.
- Provisional FII/DII data arrives in the evening; sample reports were timestamped between 18:59 and 19:40 IST.
- A broker API gives index data for personal use at acceptable cost.

### Open questions
1. Which broker API: Kite, Dhan or Upstox?
2. What monthly budget for data and LLM calls?
3. Delivery channel: Telegram, WhatsApp or email first?
4. Hindi business press in V1 or later?
5. The repo is public: should prompts and the source registry live in a private repo?

### Sources
- **[R1]** Moneycontrol Pro: [traderhq.com review](https://traderhq.com/moneycontrol-pro-review-expert-insights-smart-investors/) · [topstockmarketbroker.com 2026 review](https://www.topstockmarketbroker.com/2026/08/moneycontrol-pro-review-2026-app.html)
- **[R2]** Zerodha Pulse: [pulse.zerodha.com](https://pulse.zerodha.com/)
- **[R3]** Perplexity Finance India: [MediaNama](https://www.medianama.com/2025/08/223-perplexity-launches-bse-nse-tracking-tool-india/) · [TechCrunch](https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/)
- **[R4]** Sensibull and Opstra: [AlgoTest comparison](https://algotest.in/blog/opstra-vs-sensibull/) · [Strike review](https://www.strike.money/reviews/sensibull-alternatives)
- **[R5]** [LSEG Workspace](https://www.lseg.com/en/data-analytics/products/workspace) · [Bloomberg Terminal](https://www.bloomberg.com/professional/products/bloomberg-terminal/) (page blocked the automated check)
- **[R6]** [TradingView Lightweight Charts](https://www.tradingview.com/lightweight-charts/)
- **[R7]** Koyfin: [Atlantis review 2026](https://www.askatlantis.com/blog/koyfin-review-2026) · [Bullish Bears review](https://bullishbears.com/koyfin-review/)
- **[R8]** Benzinga Pro: [Squawk overview](https://www.benzinga.com/pro/blog/live-trading-audio-news-benzinga-pros-squawk) · [InvestingWithAI review](https://investingwithai.com/benzinga-pro-review/) · [DayTradingz review](https://daytradingz.com/benzinga-pro-review/)
- **[R9]** StockEdge and Trendlyne: [AlgoTest alternatives](https://algotest.in/blog/sensibull-alternatives-india/) · [Strike trading software list](https://www.strike.money/stock-market/trading-softwares)
- **[R10]** [Investing.com economic calendar](https://www.investing.com/economic-calendar/)
- **[R11]** [Tradar](https://trytradar.com/) · [MarketsEasy](https://marketseasy.in/)
- **[R12]** Design system: [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT)
- **[R13]** Domain checks: RDAP at rdap.verisign.com (.com), pubapi.registry.google (.app), rdap.nixiregistry.in (.in), rdap.identitydigital.services (.ai, .io), 14 Sep 2026
