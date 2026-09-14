# Citebell V0: Task checklist

Details, acceptance criteria and tests for each task: [plan.md](plan.md). Tick a task only when its Definition of Done (plan §7) is met.

## Your actions (owner-only)
- [ ] Merge PR #1 (Task 0.1)
- [ ] Supabase project in Mumbai; approve applying the migration; confirm the owner email for the allowlist (0.3)
- [ ] Vercel project and Railway service on your existing accounts; enter secrets in their dashboards, never in chat (0.3)
- [ ] Fine-grained GitHub token with read-only access to `citebell-private` contents, set on Railway (0.3)
- [ ] Google Cloud OAuth client (web application), added to Supabase's Google provider (0.4)
- [ ] Upstox developer app: API key, secret, redirect URL (Spike 1.1)
- [ ] Telegram bot from BotFather: token and your chat id (Spike 1.5)
- [ ] Keys:
  - [ ] Gemini API on the paid tier
  - [ ] FRED
  - [ ] CoinGecko Demo
  - [ ] Resend
  - [ ] search provider, if Spike 1.3 picks one
  - [ ] archive.org, if Spike 1.4 needs it
  - [ ] uptime monitor
- [ ] NSE holiday dates for the year into `citebell-private/nse_holidays.txt`
- [ ] Daily from Checkpoint C: Upstox login before 07:30; from Task 3.6: evening NSE file to the bot
- [ ] Labelling, ~15–20 h in weeks 5–6 (6.1)
- [ ] Spot checks, ~10–15 min per trading day during the gate run (8.1)

## Phase 0: Foundation close-out
- [ ] 0.1 Merge scaffold and protect `main`
- [ ] 0.2 Database tests in CI
- [ ] 0.3 Production environments
- [ ] 0.4 Sign in with Google
- [ ] **Checkpoint A:** production sign-in works (magic link and Google); worker deployed and idle; CI green

## Phase 1: Risk spikes
- [ ] 1.1 Upstox login and data
- [ ] 1.2 Article evidence feasibility (highest risk)
- [ ] 1.3 Search for wires and pre-market prices
- [ ] 1.4 PDF, archive and email
- [ ] 1.5 Telegram bot mode
- [ ] **Checkpoint B:** review spike findings; update PRD and plan

## Phase 2: Walking skeleton
- [ ] 2.1 Collector framework
- [ ] 2.2 Upstox client and daily login
- [ ] 2.3 India market facts
- [ ] 2.4 RSS collector
- [ ] 2.5 Article checker
- [ ] 2.6 Extract step
- [ ] 2.7 Verify step and corroboration
- [ ] 2.8 Writer and renderer
- [ ] 2.9 Publisher
- [ ] 2.10 Report page in the web app
- [ ] 2.11 Notifier
- [ ] **Checkpoint C:** real morning report published in production; recording starts

## Phase 3: Data coverage
- [ ] 3.1 Day recording
- [ ] 3.2 Global official data (FRED, US Treasury)
- [ ] 3.3 Crypto (CoinGecko plus a second price)
- [ ] 3.4 Official India sources (NSDL, FBIL, RBI, SEBI, PIB)
- [ ] 3.5 Upstox derivatives and India-traded commodities
- [ ] 3.6 NSE file upload via Telegram
- [ ] 3.7 Remaining publishers, search, GDELT
- [ ] 3.8 News-reported global prices
- [ ] 3.9 Event calendar
- [ ] **Checkpoint D:** all sources collecting; 5+ days recorded

## Phase 4: All four reports
- [ ] 4.1 Report template spec
- [ ] 4.2 Story grouping
- [ ] 4.3 Morning Insights, all sections
- [ ] 4.4 Mid-day Markets with "what changed"
- [ ] 4.5 End-of-day Insights
- [ ] 4.6 Institutional Flows
- [ ] 4.7 Publish as you go, retries and versions
- [ ] 4.8 PDF and citation pack
- [ ] 4.9 Email delivery
- [ ] **Checkpoint E:** 4 reports × 5 consecutive trading days; gate run starts

## Phase 5: Trust features and owner tools
- [ ] 5.1 Fact-check drawer
- [ ] 5.2 Flag as wrong and corrections
- [ ] 5.3 Archive and corrections log
- [ ] 5.4 Markets page on chart widgets
- [ ] 5.5 Sign-in hardening (2FA, aal2)
- [ ] 5.6 Daily check-in and ratings
- [ ] 5.7 Operations page

## Phase 6: Evals and bake-off
- [ ] 6.1 Labelling tool
- [ ] 6.2 AI pipeline eval runner
- [ ] 6.3 Bake-off and per-step model choice
- [ ] 6.4 Replay suite

## Phase 7: Hardening
- [ ] 7.1 Failure drills
- [ ] 7.2 Guardrail monitors
- [ ] 7.3 Web end-to-end tests
- [ ] 7.4 Accessibility and performance checks
- [ ] 7.5 Security and release pipeline
- [ ] 7.6 Runbook
- [ ] **Checkpoint F:** release readiness sign-off

## Phase 8: Exit-gate run
- [ ] 8.1 20 consecutive trading days: on time ≥ 95%, zero wrong or unverified claims in spot checks
- [ ] 8.2 V0 exit report and V1 go/no-go
