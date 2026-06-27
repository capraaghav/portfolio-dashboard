# Product

## Register

product

## Users

Individual retail investors in Indian markets (NSE/BSE) who hold equities across
multiple brokers — Zerodha, Groww, Upstox, Angel One, HDFC Securities, and others.
They are financially literate and self-directed: they read P/E and beta, think in
terms of XIRR and sector concentration, and want one consolidated, honest view of
what they actually own rather than logging into five broker portals.

Their context is reflective, not reactive. They open the dashboard to *understand*
their position — allocation, drift, tax exposure, risk concentration, dividend
income — on a weekly or monthly cadence, not to day-trade. The core job: **drop in a
broker export and immediately see the truth about my portfolio**, with enough depth
(technical, fundamental, tax, risk, analyst) to make a considered decision.

Although it began as a personal local-only tool, it is now intended as a **public
product**: anyone can sign up (optional Supabase accounts with cloud persistence and
opt-in email 2FA), so first-run clarity, trust, and account security matter as much
as the analytics.

## Product Purpose

Consolidate a person's entire equity portfolio from any broker's export (CSV, Excel,
or PDF) into a single, trustworthy dashboard with live NSE/BSE prices and layered
analysis — overview/allocation, holdings, performance (snapshots, XIRR, benchmark
backtest), technical signals, analyst targets, tax (LTCG/STCG), risk concentration,
dividends, per-stock detail, watchlist, and rebalancing.

It exists because no single broker shows a consolidated, analysis-rich, privacy-
respecting view, and generic portfolio apps don't understand Indian-market specifics
(ISIN resolution, NSE/BSE symbols, Zerodha's long-term quantity column, SENSEX/NIFTY
benchmarks, Indian tax rules). Success looks like: a user uploads a messy broker file
and within seconds trusts the numbers enough to act on them — and returns regularly
because the picture is clearer here than anywhere else.

## Brand Personality

Refined, composed, expert. The voice of a discreet private-banking statement, not a
trading-floor ticker. Three words: **calm, precise, trustworthy.** The interface
should feel like quiet expertise — it states facts plainly, lets the numbers carry
weight, and never sells excitement. Restraint signals confidence: one muted-gold
accent, deep near-black canvas, generous hierarchy. Emotional goal: the user feels
*in control and well-informed*, the way a good wealth report makes you feel, rather
than thrilled, anxious, or hurried.

## Anti-references

- **Loud retail trading apps** (Robinhood-style): no neon green/red dopamine
  styling, no gamification, no confetti-on-gains, nothing that nudges toward
  impulsive action. Gains and losses are reported, not celebrated.
- **Cluttered Bloomberg terminals**: no wall-to-wall data with zero hierarchy or
  breathing room. Depth is available on demand (toggles, tabs, detail views), not
  dumped all at once.
- **Cartoonish / playful fintech**: no bright mascot illustrations, no rounded
  "friendly money" styling. (Emoji tab icons are a pragmatic Streamlit affordance,
  not a license for a playful register.)
- **Generic SaaS dashboard slop**: no purple gradients, no identical icon-card
  grids, no gradient text, no hero-metric template.

## Design Principles

- **Numbers are the hero.** The data is the product; chrome recedes so figures,
  trends, and allocations read instantly. Typography and spacing do the work, not
  decoration.
- **Trust through honesty.** Never imply precision or success that isn't there.
  Surface un-priced tickers, missing dates, stale data, and assumptions plainly —
  an accurate "we couldn't price this" beats a confident wrong number.
- **Calm over urgency.** Reflective cadence, not reactive. The design never
  manufactures excitement or pressure around money.
- **Depth on demand.** Lead with the consolidated picture; let the user pull in
  heavier analysis (technicals, dividends, fundamentals) deliberately rather than
  forcing everything at once.
- **Restraint as identity.** One accent, one type family, a disciplined dark
  palette. The premium feel comes from what's left out.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**: body text ≥4.5:1 and large text ≥3:1 against the dark
canvas (watch muted grays like `#8B8B8B` on near-black — verify, don't assume),
fully keyboard-reachable controls, visible focus states, and `prefers-reduced-motion`
honored for the click-spark and skeleton-shimmer animations. Because this is a
finance tool, **gain/loss must not rely on red/green alone** — pair color with sign,
arrow, or label so color-blind users read P&L correctly. No other named user needs at
this time.
