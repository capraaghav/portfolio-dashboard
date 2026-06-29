# Engineering Design Specification — AI Portfolio Intelligence Engine

## 1. Title Page

| Field | Value |
|---|---|
| **Project** | Portfolio Dashboard — unified stock-portfolio analytics for Indian markets (NSE/BSE) |
| **Feature** | AI Portfolio Intelligence Engine |
| **Document type** | Engineering Design Specification (EDS) |
| **Version** | 1.0 (Draft for review) |
| **Status** | Proposed — pending design/eng review, no code written |
| **Author** | Principal PM / Staff Architect / Lead UX (acting) |
| **Date** | 2026-06-29 |
| **Owner** | Raaghav Pilaniwala |
| **Repository** | github.com/capraaghav/portfolio-dashboard |
| **Intended audience** | Engineering Managers · Product Managers · Staff Engineers · UX Designers · Technical Leads |
| **Related documents** | `product/PRD.md` (v2.0) · `docs/design-system.md` ("The After-Hours Desk") · `docs/explanation-architecture.md` |

This document specifies the design of a new intelligence layer for the Portfolio
Dashboard. It is a specification, not an implementation. No production code, Python,
SQL, Streamlit component, or Supabase schema is included. The objective is to remove
ambiguity so that a senior engineer (or Claude Code) can build the feature directly
from this text.

---

## 2. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-28 | Acting Staff Architect | Skeleton, problem framing, persona pass |
| 0.5 | 2026-06-29 | Acting Staff Architect | Pipeline, insight catalogue, data models drafted |
| 1.0 | 2026-06-29 | Acting Staff Architect | Complete draft for review; health score, NLG, roadmap, acceptance criteria finalised |

---

## 3. Table of Contents

1. Title Page
2. Revision History
3. Table of Contents
4. Executive Summary
5. Product Vision
6. Goals
7. Non-Goals
8. User Personas
9. User Stories
10. UX Specification
11. Functional Requirements
12. Non-Functional Requirements
13. System Architecture
14. AI Portfolio Intelligence Engine (the pipeline)
15. Insight Categories
16. Portfolio Health Score
17. Data Models
18. AI Reasoning (deterministic evidence → natural language)
19. Performance & Caching
20. Error Handling
21. Testing Strategy
22. Security
23. Future Roadmap
24. Implementation Roadmap
25. Acceptance Criteria

---

## 4. Executive Summary

### 4.1 Why this feature exists

The Portfolio Dashboard already computes everything an analyst needs — consolidated
holdings, technical signals, analyst targets, tax exposure, risk concentration,
dividends. But that depth is **layered behind eleven sections**, and the product's own
posture ("depth on demand") means the most important fact about a portfolio on any
given day can be three clicks deep. A user who opens the dashboard sees an accurate
picture but must *hunt* for what changed and what matters.

The AI Portfolio Intelligence Engine closes that gap. It runs every analytic the app
already has, detects the conditions that an institutional portfolio manager would flag,
ranks them by importance, and renders the top findings as a short, plainly-worded brief
at the top of the dashboard. It answers one question:

> **"What are the most important things I should know about my portfolio today?"**

### 4.2 The non-negotiable design constraint

**The AI never invents conclusions.** Every insight is produced by a deterministic
detector operating on real analytics output. The language model — used only at the final
stage — *summarises evidence that already exists*; it does not generate findings,
numbers, or recommendations of its own. If the deterministic layer found nothing, the AI
says nothing. This is the same "honesty over false precision" posture that defines the
ingestion engine (PRD §1.2), applied to intelligence.

### 4.3 Business value

- **Differentiation.** No free, private, multi-broker Indian tool offers an explained
  intelligence brief. This is the headline of the next product story.
- **Engagement & retention.** Success metric (PRD §4.2) is "a user returns regularly
  because the picture is clearer here than anywhere else." A daily brief is a reason to
  return that a static dashboard is not.
- **Premium framing.** The PRD positions this as a *premium intelligence layer*. It is
  the natural anchor for a future paid tier without compromising the free analytics.

### 4.4 User value

- Time-to-insight drops from "read eleven sections" to "read five sentences."
- Risks the user would not have looked for (a single position now 30% of book, a sector
  over-weight, a stock at a 52-week high while RSI screams overbought) are surfaced
  unprompted.
- Every sentence is traceable to a number the user can verify in the relevant section.

### 4.5 Success criteria

| # | Criterion | Target |
|---|---|---|
| SC-1 | Insights are evidence-backed | 100% of rendered insights link to a deterministic evidence object; 0 ungrounded claims |
| SC-2 | Brief is fast | Insight panel renders from warm cache in < 300 ms; cold compute adds < 2 s over existing load |
| SC-3 | Brief is relevant | In manual review of 20 real portfolios, ≥ 80% of top-3 insights judged "worth surfacing" by the owner |
| SC-4 | No false precision | 0 insights fire on missing/stale data without an explicit confidence downgrade or suppression |
| SC-5 | Graceful with no AI | With the LLM disabled or unreachable, the panel still renders insights using deterministic templates |

---

## 5. Product Vision

### 5.1 Current state

```
User opens dashboard
        │
        ▼
  Accurate, consolidated picture across 11 sections
        │
        ▼
  User manually scans sections to find what matters
        │
        ▼
  Insight found — but only if the user knew to look
```

The data is trustworthy and complete. The *attention routing* is entirely manual. The
product knows everything about the portfolio and tells the user nothing first.

### 5.2 Problems

- **P1 — Buried lede.** The single most important fact today (concentration spike,
  overbought leader, looming earnings, analyst downgrade implied by target collapse) has
  no privileged position. It competes with ten other sections for the eye.
- **P2 — Knowledge asymmetry.** The app assumes the user knows *which* metric to be
  worried about this week. A financially-literate user still has to do the routing an
  analyst would do for them.
- **P3 — No "what changed."** Snapshots exist but the user must open Performance and
  read a chart to infer movement. Nothing says "your book moved 2.1% today, driven by
  TITAN."
- **P4 — Depth without direction.** "Depth on demand" is correct, but demand requires
  knowing what to demand.

### 5.3 Desired future state

```
User opens dashboard
        │
        ▼
  Intelligence brief at the top: 3–5 ranked, explained insights
  ("Your top position is now 28% of book — concentration risk rising.")
        │
        ▼
  Each insight links to the section that proves it
        │
        ▼
  User reads the truth first, then drills only where it matters
```

The dashboard opens with a portfolio manager's read of the situation already done. The
eleven sections remain exactly as they are — the brief is a *lens over them*, not a
replacement. It transforms the product from "a place that holds the numbers" into "a
desk that has already reviewed the numbers for you."

### 5.4 How the engine transforms the product

The Intelligence Engine is the first feature that *speaks to the user about their
specific portfolio*. Everything before it presents data; this interprets it. It is the
narrative spine the PRD's vision ("Everything you own, in one honest view") implies but
the current product does not yet deliver — the *honest view* is there; the *one* view,
pre-read, is what this adds.

---

## 6. Goals

### 6.1 Business goals

- **BG-1** Establish a defensible, premium intelligence layer unique among free
  Indian-market tools.
- **BG-2** Increase return-visit frequency by giving every visit a fresh, personal "what
  matters today" brief.
- **BG-3** Create the anchor feature for an eventual paid tier without gating the
  existing free analytics.

### 6.2 User goals

- **UG-1** See the most important things about my portfolio without hunting.
- **UG-2** Trust every statement — be able to click through to the number that proves it.
- **UG-3** Understand *why* something is flagged, in plain language, not jargon.
- **UG-4** Never be misled by an insight built on missing or stale data.

### 6.3 Engineering goals

- **EG-1** Extend the existing modular architecture; do not redesign it. Add an
  `intelligence.py` (pure, no-I/O, like `analytics.py`) plus a thin NLG adapter and one
  UI section.
- **EG-2** Keep detection deterministic, pure, and unit-testable with inline fixtures —
  matching the repo's existing test pattern (no mocks, no network).
- **EG-3** Make new insight types pluggable via a registry, so adding one is a single
  function + registration, not a core-engine change.
- **EG-4** Reuse existing analytics (`risk_metrics`, `tax_breakdown`, `compute_signal`,
  `portfolio_totals`, snapshots) as evidence sources. Add new computation only where no
  existing function provides it.
- **EG-5** Degrade gracefully end-to-end: no AI key, no network, partial data, empty
  portfolio — all produce a sensible panel, never an exception.

### 6.4 AI goals

- **AIG-1** The LLM summarises deterministic evidence into calm, precise prose in the
  product's voice. It never originates a number, claim, or recommendation.
- **AIG-2** Every LLM output is constrained to the evidence passed in its prompt;
  hallucination is structurally prevented (closed-world prompt + post-generation
  validation, §18).
- **AIG-3** The system is fully functional with the LLM turned off — templates produce
  acceptable prose. The LLM is an enhancement, not a dependency.
- **AIG-4** Tone matches "The After-Hours Desk": reports, never celebrates; states
  facts; no hype.

---

## 7. Non-Goals

The engine is explicitly **not**:

- **NG-1 — An automated trading system.** It never places, suggests sizing for
  execution, or routes orders. (Consistent with PRD §4.3.)
- **NG-2 — Financial advice.** Insights are information and estimates. Every brief
  carries the same "information, not advice" disclaimer the Tax section already uses.
- **NG-3 — Predictive investing.** It does not forecast prices, returns, or which stock
  will rise. It describes the *present* state of the portfolio and the *known* facts
  (e.g. "earnings are scheduled in 4 days"), never a prediction of outcome.
- **NG-4 — A replacement for analytics.** The eleven sections remain the source of
  truth. The engine points at them; it does not supersede them.
- **NG-5 — A general chatbot.** There is no free-text Q&A in v1. The engine produces a
  fixed, ranked brief. (Conversational follow-up is a roadmap item, §23.)
- **NG-6 — A new data source.** It consumes existing market data and analytics. It adds
  *detection* over existing data, and (for earnings/ownership insights) two additional
  read-only yfinance endpoints already available via the installed `yfinance` dependency
  — no new third-party service, no new credential.
- **NG-7 — A real-time monitor.** It runs at dashboard load on cached data, on the same
  reflective cadence as the rest of the product. No alerts, no streaming in v1.

---

## 8. User Personas

These extend the PRD §3 personas with the specific value the Intelligence Engine adds.

### 8.1 Priya — The multi-account retail investor (primary)

35, product manager, holds ~40 stocks across Zerodha, HDFC, and a spouse's Groww
account. Reviews monthly. Financially literate but time-poor.

**Benefit:** Opens the dashboard once a month and reads a five-line brief instead of
re-deriving her situation across eleven sections. The engine tells her TITAN is now her
largest position at 14% and her IT sector weight has crept to 31% — facts she would not
have computed herself.

### 8.2 Rahul — The swing trader (active)

28, trades around a core book on a weekly cadence. Cares about technical extremes and
momentum. *Note: the product is deliberately not real-time; Rahul is an edge user, not
the core.*

**Benefit:** The engine flags technical breakouts and overbought/oversold extremes
(RSI > 70 at a 52-week high) across his whole book at once, instead of him scanning the
Technical section stock-by-stock. He still executes elsewhere — the engine never trades.

### 8.3 Anita — The long-term investor

52, buy-and-hold, 25 quality names, reviews quarterly. Cares about valuation
discipline, dividend income, and not drifting into concentration.

**Benefit:** The engine surfaces overvaluation (a holding trading well above analyst
mean target, or P/E far above its sector) and concentration drift — the slow risks a
quarterly reviewer is most likely to miss.

### 8.4 Vikram — The high-net-worth investor

61, ₹3–4 cr book across five demat accounts, manages family money. Risk-first mindset.

**Benefit:** The Portfolio Health Score and the Portfolio Risk insights give him a
single, explainable read on whether the book is getting fragile (concentration, beta,
sector skew) without trawling the Risk section for every member's account.

### 8.5 Deepa — The institutional analyst (aspirational/secondary)

Uses the tool informally to sanity-check a personal book. Wants rigour: evidence,
confidence, no hand-waving.

**Benefit:** Every insight exposes its evidence and confidence on demand. Deepa can
verify the engine's read against her own and trusts it precisely because it shows its
work and refuses to speak when data is thin.

---

## 9. User Stories

Each story carries acceptance criteria (AC).

**US-1 — Daily brief.** *As a retail investor,* when I open the dashboard, I see a brief
of the most important things about my portfolio today, ranked by importance.
- AC-1.1 The brief shows 3–5 insights ordered by priority score (descending).
- AC-1.2 Each insight has a title, one-to-two-sentence body, a severity indicator, and a
  link to the proving section.
- AC-1.3 The brief renders within the existing cold-load budget plus < 2 s.

**US-2 — Traceable claims.** *As any user,* I want to verify any statement the engine
makes.
- AC-2.1 Every insight exposes its underlying evidence (the exact metric values and
  thresholds that fired it) via an expander.
- AC-2.2 Clicking an insight's "View in [Section]" navigates to the relevant section.

**US-3 — Concentration risk.** *As a long-term investor,* I want to be warned when my
portfolio becomes concentrated.
- AC-3.1 When any single position ≥ 25% of book, or top-5 ≥ 60%, or effective-N drops
  below a threshold, a Portfolio Risk insight fires.
- AC-3.2 The insight names the position(s) and the exact weight, and links to Risk.

**US-4 — Technical extremes.** *As an active trader,* I want to know which of my holdings
are at technical extremes.
- AC-4.1 A breakout/overbought/oversold insight fires per the §15 thresholds and groups
  affected tickers.
- AC-4.2 No technical insight fires for a stock with < 50 closes (insufficient data is
  declared, not guessed).

**US-5 — Valuation discipline.** *As a value-conscious investor,* I want to know when I
hold something the market and analysts consider expensive.
- AC-5.1 An overvaluation insight fires when a position trades materially above analyst
  mean target and/or at an extreme P/E relative to peers, with both signals named.

**US-6 — Honest silence.** *As a privacy- and accuracy-conscious user,* I do not want the
engine to invent insights when there is nothing to say or the data is thin.
- AC-6.1 With an empty/unpriced portfolio, the panel shows an honest empty state, not
  fabricated insights.
- AC-6.2 An insight whose evidence relies on stale (> cache TTL) or missing data is
  either suppressed or rendered with a reduced confidence label.

**US-7 — Works without AI.** *As a self-hosting user with no AI key,* I still get a useful
brief.
- AC-7.1 With no LLM configured, insights render via deterministic templates in the same
  layout, with no error and no degraded ranking.

**US-8 — Health at a glance.** *As an HNW investor,* I want one explainable score for my
book's health.
- AC-8.1 A 0–100 Portfolio Health Score renders with a band label (e.g. Resilient /
  Balanced / Fragile) and a breakdown of its component sub-scores.
- AC-8.2 Every point of the score traces to a named, weighted metric — no opaque number.

---

## 10. UX Specification

The Intelligence Engine surfaces in **two places**: a new top-of-Overview **Intelligence
Brief** (the headline), and a dedicated **🧠 Intelligence** section (the full list +
health score + evidence). It is rendered entirely in the existing "After-Hours Desk"
language — no new colours, no new fonts, no shadows.

### 10.1 Navigation placement

`SECTIONS` gains one entry. Proposed order places it first, as the lens over everything:

```
["🧠 Intelligence", "📊 Overview", "📋 Holdings", "📈 Performance", "🔬 Technical",
 "🔎 Screener", "🎯 Analysts", "🧮 Tax", "⚠️ Risk", "💰 Dividends",
 "🔍 Stock Detail", "👁️ Watchlist", "⚖️ Rebalance"]
```

The Overview section additionally hosts a **condensed brief** (top 3 insights) directly
under the hero value, because Overview is the default landing section and the brief must
be seen without a click. Selecting "🧠 Intelligence" shows the full experience.

### 10.2 Page layout — the 🧠 Intelligence section

```
┌─────────────────────────────────────────────────────────────────────┐
│  INTELLIGENCE                                          [↻ Re-analyse] │   ← eyebrow (label type) + secondary button
│  What matters about your portfolio today                             │   ← headline (1.5rem/700)
│                                                                       │
│  ┌───────────────────────────┐   ┌───────────────────────────────┐  │
│  │ PORTFOLIO HEALTH          │   │  Today's move                  │  │   ← health gauge card (container) + move card
│  │        72 / 100           │   │  +₹38,200  ▲ +1.4%             │  │
│  │        Balanced           │   │  led by TITAN +4.1%            │  │
│  │  ▸ breakdown              │   │                                │  │
│  └───────────────────────────┘   └───────────────────────────────┘  │
│                                                                       │
│  ─────────────────────────  INSIGHTS  ────────────────────────────   │   ← divider (hairline) + label
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ ⚠  RISK   ·  high                                            │    │   ← insight card: severity glyph + category chip + severity
│  │ Your largest position is now 28% of the book                 │    │   ← title (title type)
│  │ TITAN has grown to ₹4.2L, 28% of portfolio value — up from   │    │   ← body (body type, 1–2 sentences)
│  │ 21% at last snapshot. Concentration risk is rising.          │    │
│  │ ▸ Evidence            View in Risk →                         │    │   ← evidence expander + section link
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ ◆  VALUATION  ·  medium                                      │    │
│  │ Two holdings trade above analyst targets …                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  … (up to N cards, ranked) …                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.3 Cards

- **Insight card.** Container-card surface (`#121212`, hairline `#232323`, radius 16px,
  no shadow — Tonal-Depth Rule). One per insight. Never nested inside another card.
  Anatomy: severity glyph + category chip (small uppercase label type) + severity word;
  title (title type, ink); body (body type, ink-soft); footer row with an **Evidence**
  expander and a **View in [Section] →** link.
- **Severity is never colour-alone** (P&L-Is-Not-Just-Colour Rule generalised). Each
  severity pairs a glyph and a word with its tint:
  - `high` → ⚠ + "high", tint coral (`#F0564A`) used *only on the glyph/word*, not the
    card.
  - `medium` → ◆ + "medium", tint gold (`#C9A87A`).
  - `low` / informational → • + "info", tint muted (`#8B8B8B`).
  - Gold stays within the One-Lamp Rule (≤ ~10% of screen): it marks severity and the
    health value, nothing decorative.
- **Health card.** Container card with a gold radial gauge (reusing the `wk52_gauge`
  Plotly idiom in `charts.py` as a starting point) showing 0–100, the band label beneath,
  and a "▸ breakdown" expander listing component sub-scores.
- **Today's-move card.** Metric-card surface; value coloured mint/coral by sign with
  explicit `+`/`−` and `%`, plus the leading contributor.

### 10.4 Loading states

Reuse the existing **dashboard-shaped skeleton** (FR-9.1). While the engine computes on
a cold load, the Intelligence section shows: a shimmer health card, a shimmer move card,
and three shimmer insight cards (eyebrow + two text bars each), using the same
`linear-gradient(90deg,#141414,#1F1F1F,#141414)` ~1.4 s sweep. Honor
`prefers-reduced-motion` (hold mid-tone). On warm reruns, render immediately — no
skeleton flicker.

If the deterministic insights are ready but the **LLM narration is still streaming**,
render each card with its **template body immediately**, then swap in the LLM prose when
it arrives (progressive enhancement). The card never sits empty waiting on the model.

### 10.5 Empty states

- **No portfolio loaded.** "Upload a portfolio to get your intelligence brief." Matches
  the existing pre-upload empty state styling.
- **Portfolio loaded, no insights fired.** This is a *positive* state, not an error:
  "Nothing demands attention today. Your book looks balanced — no concentration,
  valuation, or technical flags." Shown with the health score still present. This is the
  honest-silence requirement (US-6) made visible.
- **Single un-priced holding / file-value-only book.** "Insights need live prices. [N]
  of your holdings could not be priced, so the engine has limited evidence." Renders any
  insights that *can* be computed from file values (e.g. concentration by file value),
  flagged as such.

### 10.6 Error states

- **Market data partially failed.** Insights compute from whatever resolved; a quiet
  caption notes "Some data was unavailable; insights reflect [N] priced holdings."
- **LLM unreachable / errored / no key.** Silent fallback to template prose. No error
  shown to the user (an AI outage must not look like a product failure). A one-line
  caption "Narration unavailable — showing summaries" is acceptable but optional.
- **Engine exception (should never happen).** The section catches at its boundary and
  renders the empty/positive state plus the existing analytics unaffected. The
  Intelligence section failing must never take down the other ten sections.

### 10.7 Responsive behaviour

Streamlit single-column flow. On narrow viewports the health and move cards stack
vertically (existing `st.columns` collapse behaviour). Insight cards are full-width at
all sizes. Prose wraps at the design system's 65–75ch cap; tables/evidence may run wider.

### 10.8 Accessibility (WCAG 2.1 AA)

- All insight body text uses ink (`#EDEDED`) or ink-soft (`#B9B9B9`); category chips and
  captions never fall below `#808080` for text (NFR-A1).
- Severity is glyph + word + tint, never tint alone (NFR-A2 generalised).
- Evidence expanders and section links are keyboard-reachable with the gold-shifting
  visible focus ring (NFR-A3).
- Skeleton shimmer respects `prefers-reduced-motion` (NFR-A4).

### 10.9 Interaction flows

```
Open dashboard (Overview)
   └─> Condensed brief (top 3) renders under hero
         ├─> click "View in Risk →"  ──> nav switches to ⚠️ Risk
         └─> click 🧠 Intelligence in sidebar ──> full section
                ├─> expand "Evidence" ──> shows metric values + thresholds that fired
                ├─> expand health "breakdown" ──> component sub-scores
                └─> click "↻ Re-analyse" ──> clears intelligence cache, recomputes
```

### 10.10 Design consistency checklist

- One accent (gold) ≤ 10% of screen — severity tints used sparingly. ✔
- No box-shadows; tonal layering only. ✔
- Inter only, weight for hierarchy. ✔
- No nested cards. ✔
- Gains/losses and severities carry sign/word, not colour alone. ✔
- Reports, never celebrates — copy guidelines in §18.6. ✔

---

## 11. Functional Requirements

Each requirement is individually testable.

### 11.1 Detection & evidence

- **FR-1** The engine SHALL compute a set of *evidence* objects from existing analytics
  outputs (holdings, totals, risk metrics, TA signals, tax breakdown, metadata,
  snapshots) without performing any new network I/O in the pure layer.
- **FR-2** Each registered *detector* SHALL be a pure function `(context) -> list[Insight]`,
  returning zero or more insights, deterministic for identical input.
- **FR-3** A detector SHALL NOT fire when its required evidence is missing, NaN, or based
  on fewer data points than its declared minimum; it SHALL instead return no insight or
  a confidence-reduced insight, per its spec in §15.
- **FR-4** Every produced `Insight` SHALL carry: id, category, severity, priority score,
  confidence, title (template), body (template), an `Evidence` object, and a target
  section link.
- **FR-5** The engine SHALL rank all produced insights by a deterministic priority score
  (§14.6) and return the top N (default N=5; configurable) for the full section and top 3
  for the condensed brief.

### 11.2 Insight categories (v1)

- **FR-6** The engine SHALL implement, at minimum, detectors for: Portfolio Risk
  (concentration/beta/sector), Earnings Surprises (recent reported surprise and/or
  upcoming earnings date), Overvaluation (vs analyst target and vs P/E), Technical
  Breakouts (and overbought/oversold extremes), and Institutional/Holder Ownership
  changes — each per §15.
- **FR-7** The engine SHALL additionally implement the supplementary detectors proposed
  in §15.6 (Today's Move, Concentration Drift, Analyst Target Shift, Tax-Loss
  Opportunity, Dividend Concentration, Unresolved-Holdings Data-Quality) where the
  required data exists.

### 11.3 Health score

- **FR-8** The engine SHALL compute a 0–100 Portfolio Health Score from named, weighted
  component sub-scores (§16), each itself in 0–100, with the breakdown exposed in the UI.
- **FR-9** The health score SHALL be deterministic and reproducible from holdings + risk
  metrics + metadata alone (no LLM).

### 11.4 Natural-language layer

- **FR-10** When an LLM is configured, the engine SHALL render each insight's body by
  passing **only** that insight's evidence to the model under a closed-world prompt
  (§18), producing prose constrained to the supplied facts.
- **FR-11** The engine SHALL validate every LLM output against its evidence (numeric and
  entity checks, §18.4) and SHALL fall back to the deterministic template body if
  validation fails.
- **FR-12** When no LLM is configured or it is unreachable, the engine SHALL render the
  deterministic template body, with no functional difference in layout or ranking.

### 11.5 UI

- **FR-13** The dashboard SHALL render a condensed brief (top 3) on Overview and a full
  brief + health score + evidence in a new 🧠 Intelligence section.
- **FR-14** Each insight SHALL provide an Evidence expander (raw metrics + thresholds)
  and a navigation link to its proving section.
- **FR-15** A "↻ Re-analyse" control SHALL clear the intelligence cache and recompute.

### 11.6 Persistence (optional, additive)

- **FR-16** The engine MAY persist the day's insight set to the existing snapshot store
  so "what changed since yesterday" detectors can compare. This SHALL reuse the existing
  `store` abstraction (`db` or `storage`) and SHALL NOT introduce a new persistence path.

---

## 12. Non-Functional Requirements

- **NFR-1 Performance.** Deterministic detection over a 150-stock book SHALL complete in
  < 500 ms on warm market-data caches. LLM narration SHALL be non-blocking
  (template-first render). Full panel from warm cache < 300 ms.
- **NFR-2 Reliability.** Zero unhandled exceptions in any detector for any supported
  portfolio (mirrors NFR-4 of the PRD). The Intelligence section failing SHALL NOT affect
  the other sections.
- **NFR-3 Maintainability.** Adding an insight type SHALL require only writing one pure
  detector function and registering it — no change to the engine, ranking, or NLG core.
- **NFR-4 Scalability.** Detection is O(holdings) per detector; the registry is small.
  The design SHALL hold for books up to ~500 holdings without architectural change.
- **NFR-5 Security.** The LLM SHALL receive only the minimal evidence needed, never raw
  account labels or PII; the API key SHALL live only in Streamlit secrets (§22).
- **NFR-6 Accessibility.** WCAG 2.1 AA per §10.8.
- **NFR-7 Latency budget.** Earnings/ownership detectors that require *additional*
  yfinance endpoints SHALL be cached (≥ 6 h) and SHALL degrade to "data unavailable"
  rather than block the panel.
- **NFR-8 Caching.** Intelligence output SHALL be cached per portfolio fingerprint with a
  TTL aligned to the shortest upstream cache (quotes, ~5 min), invalidated by "Refresh
  data" and "Re-analyse".
- **NFR-9 Code quality.** The pure layer SHALL carry no Streamlit or I/O imports
  (mirrors `analytics.py`), enabling the existing unittest + inline-fixture test pattern.
- **NFR-10 Privacy.** No holdings data leaves the machine except (a) the existing
  anonymous market-data lookups and (b) — only if the user enables AI — the minimal,
  de-identified evidence sent to the LLM provider (§22.4). AI is opt-in.

---

## 13. System Architecture

### 13.1 Principle: extend, do not redesign

The engine slots into the existing pipeline as a new pure-computation module
(`intelligence.py`, sibling to `analytics.py`), a thin LLM adapter (`ai_narrator.py`),
and one new UI section block in `app.py`. It reuses `analytics`, `market_data`,
`charts`, `formatting`, and `store` unchanged. The data flow gains one stage *after*
`build_holdings` and *before* section rendering.

### 13.2 Data flow (extended)

```
upload
  → parsers.parse_all
  → market_data.resolve_symbols (3-pass)
  → market_data.fetch_quotes (+ metadata / TA / dividends)
  → analytics.build_holdings ─────────────────────────────────┐
                                                               │
        ┌──────────────── existing sections render ───────────┘
        │
        ▼   NEW
  intelligence.build_context(holdings, raw, totals, risk, ta,
                             tax, meta, snapshots, extras)
        │
        ▼
  intelligence.detect_all(context)   # runs registered detectors
        │
        ▼
  intelligence.rank(insights)        # priority score, top-N
        │
        ▼
  ai_narrator.narrate(insights)      # optional LLM pass, template fallback
        │
        ▼
  app.py  🧠 Intelligence section  +  Overview condensed brief
```

### 13.3 Component responsibilities

| Component | New? | Responsibility |
|---|---|---|
| `intelligence.py` | **new** | Pure, no-I/O. `Evidence`/`Insight`/`HealthScore` builders, the detector registry, all detectors, ranking, health score. Mirrors `analytics.py`'s purity. |
| `ai_narrator.py` | **new** | The only module that talks to an LLM. Builds closed-world prompts from evidence, calls the provider (Anthropic Claude by default), validates output, returns prose or falls back to template. Holds all I/O + secrets handling for AI. |
| `market_data.py` | extend | Add two cached read-only fetchers: `fetch_earnings(tickers, _suffix_map)` (next/last earnings date + reported surprise where available via `yfinance` `Ticker.earnings_dates`) and `fetch_holders(tickers, _suffix_map)` (institutional/major-holder snapshot via `Ticker.institutional_holders` / `major_holders`). Both cached ≥ 6 h, both degrade to `{}` on failure. |
| `charts.py` | extend | Add `health_gauge(score)` (gold 0–100 gauge) reusing the existing gauge idiom. No other chart changes. |
| `app.py` | extend | One new section block `elif section == "🧠 Intelligence":`, a condensed brief on Overview, the new `SECTIONS` entry, and the intelligence cache wiring. No changes to existing section logic. |
| `formatting.py` | extend | Add severity glyph/label/tint constants and a `SEVERITY_ORDER`, alongside the existing `SIGNAL_*`/`REC_*` constants. |
| `analytics.py` | reuse | Source of evidence: `risk_metrics`, `portfolio_totals`, `compute_signal`, `tax_breakdown`, `harvest_candidates`. Add at most one helper (e.g. `sector_weights`) if a needed aggregate is missing. |
| `store` (`db`/`storage`) | reuse | Snapshot read for "what changed"; optional insight persistence (FR-16) via existing signatures. |

### 13.4 Module boundaries

```
            ┌──────────────────────────────────────────────┐
            │                  app.py (UI)                  │
            │   Overview brief · 🧠 Intelligence section    │
            └───────────────┬───────────────┬──────────────┘
                            │               │
                  (pure, no I/O)        (I/O, secrets)
                            ▼               ▼
                 ┌──────────────────┐  ┌──────────────────┐
                 │ intelligence.py  │  │  ai_narrator.py  │
                 │  detectors,      │  │  LLM adapter,    │
                 │  ranking, health │  │  validation,     │
                 │                  │  │  template fallbk │
                 └───────┬──────────┘  └──────────────────┘
                         │ consumes evidence from
        ┌────────────────┼─────────────────────────────┐
        ▼                ▼                ▼              ▼
  analytics.py     market_data.py    formatting.py    store
  (risk, tax, TA)  (quotes, meta,    (severity tokens) (snapshots)
                    earnings, holders)
```

`intelligence.py` imports only `analytics`, `formatting`, `numpy`, `pandas` — **never**
`streamlit`, `market_data`, or `ai_narrator`. Market data and snapshots are *passed in*
by `app.py`, preserving testability (same discipline as `analytics.py`).

### 13.5 Folder structure (additions only)

```
portfolio-dashboard/
├── intelligence.py          ← NEW  (pure detection + ranking + health)
├── ai_narrator.py           ← NEW  (LLM adapter + validation + fallback)
├── analytics.py             ← reuse (+ maybe 1 helper)
├── market_data.py           ← extend (fetch_earnings, fetch_holders)
├── charts.py                ← extend (health_gauge)
├── formatting.py            ← extend (severity tokens)
├── app.py                   ← extend (section + brief + wiring)
├── tests/
│   ├── test_intelligence.py ← NEW  (detectors, ranking, health — inline fixtures)
│   └── test_ai_narrator.py  ← NEW  (validation + fallback, no network)
└── docs/
    └── explanation-intelligence-engine.md  ← NEW (architecture explainer, post-build)
```

### 13.6 Dependency graph (new edges)

```
app.py ─────────► intelligence.py ─────► analytics.py
   │                    │                  formatting.py
   │                    └────────────────► (numpy, pandas)
   ├───────────► ai_narrator.py ─────────► anthropic SDK (optional)
   │                    └────────────────► intelligence.py (types only)
   └───────────► market_data.py (fetch_earnings, fetch_holders)
```

The only *new third-party dependency* is the optional `anthropic` SDK, gated exactly
like Supabase: absent key/package → AI silently off, templates used. No new dependency is
required for the engine's core.

### 13.7 Configuration & gating

| Mode | Trigger | Behaviour |
|---|---|---|
| **Deterministic only (default)** | No AI key | Full engine, template prose. |
| **AI-narrated** | `ANTHROPIC_API_KEY` (or `AI_*`) in `st.secrets` AND `anthropic` installed | Template-first render, LLM enhancement, validated. |
| **Engine off** | `PORTFOLIO_INTELLIGENCE = "0"` secret/env | Section hidden, brief hidden. Escape hatch. |

This mirrors the product's existing additive-gating philosophy (`db.is_enabled()`).

---

## 14. AI Portfolio Intelligence Engine (the pipeline)

The pipeline is eight stages. Stages 1–6 are deterministic and pure; stage 7 is the
optional LLM pass; stage 8 is rendering.

```
Portfolio (holdings + raw rows)
        │  (1) gather
        ▼
Market Data (quotes, metadata, TA, dividends, earnings, holders)
        │  (2) compute analytics
        ▼
Analytics (totals, risk, tax, signals, snapshots diff)
        │  (3) build evidence
        ▼
Evidence objects  (typed, named metrics + thresholds + freshness)
        │  (4) run detectors
        ▼
Insight detection  (registry of pure detectors → candidate insights)
        │  (5) score
        ▼
Priority ranking  (severity × magnitude × confidence × freshness)
        │  (6) select top-N + health score
        ▼
Selected insights + Portfolio Health Score
        │  (7) narrate (optional LLM, validated, template fallback)
        ▼
Natural-language insights
        │  (8) render
        ▼
Dashboard (Overview brief + 🧠 Intelligence section)
```

### 14.1 Stage 1 — Gather

`app.py` already produces `holdings`, `raw`, `prices`, `meta`, `quotes`, `ta_signals`.
The engine additionally requests `snapshots_df()` from `store` (for diff/drift) and, when
AI/earnings/ownership detectors are active, `market_data.fetch_earnings` and
`fetch_holders`. All gathering happens in `app.py`; the pure layer receives a single
`context` dict.

### 14.2 Stage 2 — Compute analytics

Reuse existing functions: `portfolio_totals(holdings)`, `risk_metrics(holdings,
fundamentals)`, `tax_breakdown(raw, prices, meta)`, and per-stock `compute_signal` is
already embedded in `ta_signals`. The snapshot diff (today vs most-recent prior snapshot)
is computed by a small new pure helper in `intelligence.py`.

### 14.3 Stage 3 — Build evidence

`intelligence.build_context(...)` assembles a typed `Evidence` set: each evidence is a
named bundle of metric values, the relevant threshold(s), the entities involved
(tickers), and a **freshness** stamp (derived from cache age / data presence). Evidence is
the *only* thing detectors and the LLM ever see — they never touch raw market data
directly. This is the firewall that makes hallucination structurally hard: the LLM's
world is exactly the evidence and nothing else.

### 14.4 Stage 4 — Insight detection

A **registry** maps category → detector function. `detect_all(context)` iterates the
registry, calls each detector, and collects candidate insights. Detectors are pure and
independent; order does not matter. A detector returns `[]` when its condition is not met
or its data is insufficient (FR-3).

```
DETECTORS = [
  detect_portfolio_risk,
  detect_technical_extremes,
  detect_overvaluation,
  detect_earnings,
  detect_ownership_change,
  detect_todays_move,
  detect_concentration_drift,
  detect_analyst_target_shift,
  detect_tax_loss_opportunity,
  detect_dividend_concentration,
  detect_data_quality,
]
```

Adding a detector = append one pure function here (NFR-3).

### 14.5 Stage 5 — Scoring

Each insight carries a **priority score** in [0, 100]:

```
priority = w_sev · severity_weight        # high=1.0, medium=0.6, low=0.3
         + w_mag · magnitude_norm         # detector-specific 0..1 (how far past threshold)
         + w_conf · confidence            # 0..1 (data completeness/freshness)
         + w_fresh · freshness            # 0..1 (1=fresh quotes, lower if stale/file-value)
         (weights sum to 1; scaled ×100)
```

Default weights: `w_sev=0.40, w_mag=0.30, w_conf=0.20, w_fresh=0.10`. The weights live in
one constants block in `intelligence.py` and are the single tuning surface. Magnitude
normalisation is defined per detector in §15 (e.g. for concentration, `magnitude_norm =
clip((top1_pct − 25) / 25, 0, 1)`).

### 14.6 Stage 6 — Select + health

Sort by priority descending; take top N (default 5). De-duplicate across detectors that
reference the same ticker+theme (keep the higher-priority one). Compute the Portfolio
Health Score (§16) in the same pass — it is independent of the insight selection but
rendered alongside.

### 14.7 Stage 7 — Narrate (optional)

`ai_narrator.narrate(insights)` enriches each insight's `body` (§18). Template bodies
are always present first; the LLM pass replaces them only on successful validation.

### 14.8 Stage 8 — Render

`app.py` renders the condensed brief (Overview) and full section (🧠 Intelligence) from
the ranked, narrated insight list + health score (§10).

---

## 15. Insight Categories

Each category below specifies: business rationale, detection algorithm, thresholds,
evidence, severity, confidence, an example output, acceptance criteria, required data,
and future improvements. Thresholds are defaults in one constants block, tunable without
code restructure.

### 15.1 Portfolio Risk (concentration / beta / sector)

**Business rationale.** The single biggest avoidable risk for a retail book is silent
concentration — one position or sector quietly dominating. The Risk section already
computes the metrics; this detector decides when they cross into "tell the user."

**Detection algorithm.** From `risk_metrics(holdings, fundamentals)`:
- Single-position: fire if `top1_pct ≥ 25`.
- Top-5: fire if `top5_pct ≥ 60`.
- Sector: fire if `top_sector_pct ≥ 35`.
- Diversification: fire if `effective_n < max(5, 0.25 × n_positions)`.
- Beta: fire (informational) if `portfolio_beta ≥ 1.3` or `≤ 0.7`.

Each sub-condition emits at most one insight; the highest-magnitude one is kept if
several fire on the same dimension.

**Thresholds.** `TOP1=25%`, `TOP5=60%`, `SECTOR=35%`, `BETA_HI=1.3`, `BETA_LO=0.7`,
`EFF_N_FLOOR=5`. All in constants.

**Evidence.** `{top1_ticker, top1_pct, top5_pct, top_sector, top_sector_pct,
effective_n, portfolio_beta, n_positions}` — straight from `risk_metrics`.

**Severity.** `top1_pct ≥ 35` or `top5_pct ≥ 75` → high; else medium; beta-only → low.

**Confidence.** 1.0 when all named positions are live-priced; reduced proportionally to
the share of book value that is file-value-only.

**Example output (template).** "Your largest position is 28% of the book. TITAN has
grown to ₹4.2L of ₹15.1L total. Concentration above 25% in one name raises single-stock
risk."

**Acceptance criteria.** AC-3.1/3.2. Fires exactly at thresholds; names exact
tickers/percentages; links to ⚠️ Risk; never fires on an empty `risk_metrics` (`{}`).

**Required data.** Holdings with `Current Value (₹)`; fundamentals for beta (optional).

**Future improvements.** Correlation-adjusted concentration; factor exposure.

### 15.2 Earnings Surprises (and upcoming earnings)

**Business rationale.** A scheduled earnings date is a known, dateable fact a PM always
tracks; a recent reported surprise explains a move. This is *information*, never a
prediction (NG-3).

**Detection algorithm.** From `fetch_earnings(tickers)` (new, cached ≥ 6 h):
- **Upcoming:** if a holding's next earnings date is within `EARN_HORIZON=7` days, fire
  an informational insight naming the date and the position's weight.
- **Recent surprise:** if a holding reported within `EARN_LOOKBACK=5` days and a
  surprise % is available, fire, naming reported vs estimate and the surprise sign.

Aggregate multiple holdings into one grouped insight ("3 of your holdings report this
week") with a per-ticker evidence list.

**Thresholds.** `EARN_HORIZON=7d`, `EARN_LOOKBACK=5d`, surprise materiality `≥ 5%` to
escalate severity.

**Evidence.** `[{ticker, earnings_date, eps_estimate?, eps_reported?, surprise_pct?,
weight_pct}]`.

**Severity.** Upcoming → low/info; recent surprise with `|surprise| ≥ 5%` on a position
`≥ 5%` of book → medium.

**Confidence.** Earnings data for Indian tickers via yfinance is **partial and
inconsistent**. Confidence = 1.0 only when a concrete date/surprise is present; the
detector emits nothing (not a guess) when the field is absent. This honesty is mandatory.

**Example output.** "Three holdings report earnings this week — TITAN (Jul 2), INFY
(Jul 4), HDFCBANK (Jul 5). Together they are 22% of your book."

**Acceptance criteria.** Fires only on present dates/surprises; never fabricates a date;
groups correctly; links to 🔍 Stock Detail for the named ticker.

**Required data.** `Ticker.earnings_dates` (yfinance). Degrades to `{}` → no insight.

**Future improvements.** AMFI/NSE corporate-announcements feed for reliable Indian dates;
post-earnings drift context.

### 15.3 Overvaluation

**Business rationale.** Valuation discipline is the long-term investor's core job. The
app already fetches analyst targets and P/E; this detector flags holdings the market and
analysts jointly consider stretched — without ever predicting a fall (NG-3).

**Detection algorithm.** For each holding with metadata:
- **Vs target:** if `live_price > target_mean × (1 + OVER_TARGET)`, the position trades
  above analyst consensus.
- **Vs P/E:** if `pe` is present and `pe > sector_pe_median × OVER_PE_MULT` (sector
  median computed across the user's own holdings as a cheap proxy, or a static sector
  band if too few peers), flag rich valuation.
- Fire when **either** signal triggers; escalate when **both** do.

**Thresholds.** `OVER_TARGET=0.10` (10% above mean target), `OVER_PE_MULT=1.5`,
minimum `n_analysts ≥ 3` to use the target signal.

**Evidence.** `{ticker, live_price, target_mean, n_analysts, upside_pct, pe,
sector_pe_proxy}`.

**Severity.** Both signals on a position `≥ 5%` of book → medium-high; single signal →
low-medium.

**Confidence.** Requires `target_mean` with `n_analysts ≥ 3` and/or a valid `pe`;
otherwise the relevant sub-signal is skipped, not assumed.

**Example output.** "INFY trades 14% above the analyst mean target of ₹1,520 with 31
analysts covering it, and its P/E of 29 is well above your IT holdings' median. The
market is pricing it richly."

**Acceptance criteria.** AC-5.1. Names both the target and P/E facts when both fire;
never asserts a price will fall; links to 🎯 Analysts.

**Required data.** `meta.analyst` (`target_mean`, `n_analysts`), `meta.fundamentals.pe`,
`prices`.

**Future improvements.** PEG, forward-PE vs trailing, history of target revisions.

### 15.4 Technical Breakouts (and overbought/oversold extremes)

**Business rationale.** Technical extremes across a whole book are tedious to scan
manually. The Technical section already computes per-stock signals; this rolls them up.

**Detection algorithm.** From `ta_signals` (already computed via `compute_signal`):
- **Breakout / Strong trend:** group holdings whose `signal == "Strong Bullish"` (golden
  cross + above 50MA) or `"Strong Bearish"`.
- **Overbought:** `rsi ≥ 70`; **Oversold:** `rsi ≤ 30`.
- **52-week proximity:** if `live_price ≥ 0.98 × wk52_high` (from fundamentals), flag
  "at/near 52-week high"; combine with RSI for an "overbought at highs" escalation.

Emit grouped insights (one for breakouts, one for overbought-at-highs, etc.), each with a
per-ticker evidence list.

**Thresholds.** `RSI_HI=70`, `RSI_LO=30`, `WK52_NEAR=0.98`. Minimum 50 closes for any
technical signal (already enforced upstream — `compute_signal` returns N/A below 20, and
strong signals require 200 closes for the golden-cross arm).

**Evidence.** `[{ticker, signal, rsi, vs_50ma, near_52w_high}]`.

**Severity.** Overbought (RSI ≥ 70) at a 52-week high on a `≥ 5%` position → medium;
pure breakout grouping → low/info.

**Confidence.** 1.0 for stocks with full 200-day history; reduced/omitted for "N/A"
signals (AC-4.2).

**Example output.** "Two holdings look stretched: TITAN (RSI 76, at its 52-week high) and
BAJFINANCE (RSI 72). Strong runs, but technically overbought."

**Acceptance criteria.** AC-4.1/4.2. Never fires for N/A-signal stocks; groups correctly;
links to 🔬 Technical.

**Required data.** `ta_signals`, `meta.fundamentals.wk52_high`, `prices`.

**Future improvements.** Volume confirmation, MACD, breakout vs range classification.

### 15.5 Institutional / Holder Ownership Changes

**Business rationale.** Institutional accumulation/distribution is a classic
quality/conviction signal a PM tracks. **Caveat (honest):** yfinance ownership data for
Indian listings is sparse and often stale; this detector must be conservative.

**Detection algorithm.** From `fetch_holders(tickers)` (new, cached ≥ 6 h):
- Capture `% held by institutions` and the top institutional holders snapshot.
- Fire an **informational** insight only when (a) the data is present AND (b) it is
  notably high/low (`INST_HI=50%`, `INST_LO=10%`) for a position `≥ 5%` of book. Change
  detection ("up/down vs last quarter") fires **only** if a prior snapshot exists in the
  insight store (FR-16); otherwise the insight is a static level, clearly worded as such.

**Thresholds.** `INST_HI=50%`, `INST_LO=10%`, position weight `≥ 5%`.

**Evidence.** `{ticker, pct_institutions, top_holders[], as_of?, prior_pct?}`.

**Severity.** Always low/informational in v1 (the data is not reliable enough to drive
high-severity action).

**Confidence.** Capped at 0.6 in v1 due to data sparsity; the UI labels it
"informational, data may be stale." When data absent → no insight.

**Example output.** "HDFCBANK shows ~58% institutional ownership in the latest available
data — a heavily institutionally-held name. (Ownership data can lag a quarter.)"

**Acceptance criteria.** Never fires without present data; never claims a *change* without
a prior snapshot; confidence visibly capped; links to 🔍 Stock Detail.

**Required data.** `Ticker.institutional_holders` / `major_holders` (yfinance).

**Future improvements.** NSE shareholding-pattern filings (reliable Indian source);
promoter-pledge tracking.

### 15.6 Additional proposed insight types

These fit the product naturally and reuse existing analytics. Specified more briefly;
each follows the same evidence→detector→template structure.

**(a) Today's Move.** *Rationale:* the first thing anyone wants. *Detection:* compare
today's total value to the most recent prior snapshot; identify top ±contributors by
`Δvalue`. *Threshold:* always render as the move card (not gated). *Evidence:* `{today_pct,
today_abs, top_gainer, top_loser}`. *Severity:* informational unless `|move| ≥ 3%` →
low. *Links:* 📈 Performance.

**(b) Concentration Drift.** *Rationale:* slow risk. *Detection:* `top1_pct` or
`top_sector_pct` increased by `≥ 5 pp` vs a prior snapshot. *Evidence:* current vs prior
weights. *Severity:* medium. *Links:* ⚠️ Risk. (Requires a prior snapshot; otherwise
silent.)

**(c) Analyst Target Shift.** *Rationale:* implied upgrade/downgrade. *Detection:* the
gap between `live_price` and `target_mean` has widened/narrowed materially vs a prior
metadata snapshot, OR `rec_mean` crossed a band boundary. *Severity:* medium. *Links:* 🎯
Analysts. (yfinance does not expose target history directly → needs prior snapshot of
`target_mean`; silent without one.)

**(d) Tax-Loss Opportunity.** *Rationale:* actionable, India-specific. *Detection:* reuse
`harvest_candidates(holdings)`; if aggregate harvestable loss `≥ TAX_LOSS_MIN` (e.g.
₹25,000) and there are net taxable gains in `tax_breakdown`, surface it. *Severity:*
medium. *Links:* 🧮 Tax. Carries the "estimate, not advice" disclaimer.

**(e) Dividend Concentration.** *Rationale:* income reliability. *Detection:* if `≥ 50%`
of TTM portfolio dividend income comes from one stock (from existing dividend data).
*Severity:* low. *Links:* 💰 Dividends.

**(f) Data-Quality / Unresolved Holdings.** *Rationale:* the product's honesty posture
made into an insight. *Detection:* if `N` holdings are unresolved/un-priced/file-value
only, surface it so the user knows the brief's blind spots. *Severity:* low but
*always shown* when present, because it scopes the trust of every other insight. *Links:*
📋 Holdings.

---

## 16. Portfolio Health Score

### 16.1 Goal

A single 0–100 score that is **fully explainable** — every point traces to a named,
weighted, normalised metric the user can verify. No black box, no arbitrary constant. It
is a *composite of conditions the engine already detects*, not a new opinion.

### 16.2 Components

Five sub-scores, each 0–100 (100 = healthiest), each from existing metrics:

| Sub-score | Source metric | Maps to 100 when… | Maps to 0 when… | Weight |
|---|---|---|---|---|
| **Diversification** | `effective_n`, `top1_pct` | effective_n ≥ 15 and top1 ≤ 10% | effective_n ≤ 2 or top1 ≥ 40% | 0.30 |
| **Sector balance** | `top_sector_pct` | ≤ 20% | ≥ 60% | 0.20 |
| **Valuation** | share of book above analyst target / rich P/E | 0% stretched | ≥ 50% stretched | 0.20 |
| **Volatility** | `portfolio_beta` | 0.8–1.1 band | ≥ 1.6 or ≤ 0.4 | 0.15 |
| **Data quality** | live-price coverage, resolved share | 100% priced/resolved | ≤ 50% | 0.15 |

### 16.3 Normalisation

Each sub-score uses an explicit piecewise-linear map between its "best" and "worst"
anchor (table above), clamped to [0, 100]. Example (Diversification, using top1_pct):
`score = clip(100 × (40 − top1_pct) / (40 − 10), 0, 100)`, then averaged with the
`effective_n` map. The anchors live in one constants block; tuning is changing a number,
not logic.

### 16.4 Composite

```
health = Σ (weight_i × subscore_i)        # weights sum to 1 → 0..100
band   = Resilient (≥ 75) | Balanced (50–74) | Watchful (30–49) | Fragile (< 30)
```

### 16.5 Explainability

The "▸ breakdown" expander lists each sub-score, its value, its weight, and the one-line
reason ("Sector balance 62/100 — IT is 31% of book"). The score is **never** shown
without the path to its components (FR-9, AC-8.2).

### 16.6 Worked example

Book: 40 stocks, top1 = 14%, top sector = 31%, 10% of value above target, beta = 1.15,
100% priced.

| Sub-score | Value | × Weight |
|---|---|---|
| Diversification | 86 | 25.8 |
| Sector balance | 73 | 14.6 |
| Valuation | 80 | 16.0 |
| Volatility | 88 | 13.2 |
| Data quality | 100 | 15.0 |
| **Health** | | **84.6 → 85 (Resilient)** |

### 16.7 What it is not

Not a buy/sell signal, not a prediction, not a peer-relative percentile. It is a present
snapshot of structural health, by construction reproducible and disclosed.

---

## 17. Data Models

All models are plain, serialisable structures (dataclasses or typed dicts) in
`intelligence.py`. No ORM, no DB tables in v1 (optional persistence in FR-16 reuses the
existing snapshot JSON shape).

### 17.1 `Evidence`

The atomic, deterministic fact bundle. The **only** thing detectors and the LLM see.

| Field | Type | Meaning |
|---|---|---|
| `kind` | str | e.g. `"concentration"`, `"earnings"`, `"valuation"` |
| `metrics` | dict[str, float\|str] | named metric values (e.g. `top1_pct: 28.0`) |
| `thresholds` | dict[str, float] | the thresholds that were tested |
| `entities` | list[str] | tickers involved |
| `freshness` | float (0–1) | 1 = fresh live data; lower = stale/file-value |
| `as_of` | str (ISO) | when the underlying data was fetched |

### 17.2 `Insight`

| Field | Type | Meaning |
|---|---|---|
| `id` | str | stable id (`category:tickers:date`) for de-dup and persistence |
| `category` | `InsightCategory` | enum (see 17.4) |
| `severity` | enum | `high` \| `medium` \| `low` |
| `priority` | float (0–100) | ranking score (§14.5) |
| `confidence` | float (0–1) | data completeness/reliability |
| `title` | str | template title (short) |
| `body_template` | str | deterministic prose (always present) |
| `body` | str | final prose (LLM or template) |
| `evidence` | `Evidence` | the proving facts |
| `section` | str | target section label for the "View in …" link |
| `tickers` | list[str] | involved tickers (for grouping/links) |

### 17.3 `HealthScore`

| Field | Type | Meaning |
|---|---|---|
| `score` | int (0–100) | composite |
| `band` | str | Resilient/Balanced/Watchful/Fragile |
| `components` | list[`HealthComponent`] | each with name, value, weight, reason |

`HealthComponent`: `{name: str, subscore: float, weight: float, reason: str}`.

### 17.4 `InsightCategory` (enum)

`PORTFOLIO_RISK, EARNINGS, OVERVALUATION, TECHNICAL, OWNERSHIP, TODAYS_MOVE,
CONCENTRATION_DRIFT, ANALYST_SHIFT, TAX_LOSS, DIVIDEND_CONCENTRATION, DATA_QUALITY`.
Each maps to: a display chip label, a default target section, and a severity-tint default
(in `formatting.py`).

### 17.5 `Recommendation` (deliberately constrained)

The product is **not** advisory (NG-2). The model is therefore an *observation with a
suggested place to look*, never an instruction:

| Field | Type | Meaning |
|---|---|---|
| `observation` | str | what is true ("28% in one name") |
| `consider` | str \| None | a neutral, optional pointer ("you may want to review concentration") — never "sell" |
| `section` | str | where to verify |

`consider` text is drawn from a fixed, reviewed phrase set (§18.6), never free-generated,
so the product cannot drift into advice.

### 17.6 Relationships

```
HealthScore 1───* HealthComponent
context ──► detect_all ──► [Insight]*
Insight 1───1 Evidence
Insight 1───0..1 Recommendation
Insight *───1 InsightCategory
```

---

## 18. AI Reasoning (deterministic evidence → natural language)

### 18.1 Role of the LLM

The LLM does exactly one thing: **rewrite a single insight's deterministic template body
into one or two natural sentences in the product's voice, using only the supplied
evidence.** It does not rank, detect, score, decide severity, or see the whole portfolio.
It is a *narrator of one fact bundle at a time*. This bounded role is the core
hallucination defence.

### 18.2 Why per-insight, not whole-portfolio

Passing the whole portfolio invites the model to invent cross-stock conclusions. Passing
one insight's `Evidence` gives it a closed world: a handful of named numbers and tickers.
There is nothing to hallucinate *from* — the facts are the prompt.

### 18.3 Prompt architecture

```
SYSTEM:
  You are a portfolio analyst's writing assistant. You rewrite a single
  pre-computed finding into 1–2 calm, precise sentences for an Indian retail
  investor. You may ONLY use the numbers and tickers in EVIDENCE. You may not
  add, infer, predict, or recommend. No price predictions. No buy/sell advice.
  Report; never celebrate. If a number is not in EVIDENCE, do not state it.

USER:
  CATEGORY: <category>
  SEVERITY: <severity>
  EVIDENCE: <json of Evidence.metrics + entities + thresholds>
  TEMPLATE: <deterministic body — the ground truth to paraphrase>
  Rewrite TEMPLATE into 1–2 sentences. Keep every number identical. Do not
  introduce numbers, tickers, or claims absent from EVIDENCE.
```

Default model: **Claude (claude-opus-4-8 or a cheaper Claude tier — `claude-haiku-4-5` is
sufficient for paraphrase and lowers cost/latency)**. Temperature low (≤ 0.3). Max tokens
small (the output is two sentences). One call per insight, fired in parallel for the
top-N; cached by insight `id`.

### 18.4 Hallucination prevention (defence in depth)

1. **Closed-world prompt** — only `Evidence` + `template` in context (18.3).
2. **Template ground truth** — the model paraphrases an already-correct sentence; the
   template is the canonical body and is never discarded.
3. **Numeric validation** — after generation, extract every number and ticker from the
   model output; assert each appears in the `Evidence` (numbers within rounding, tickers
   exact). Any extra/altered number or unknown ticker → **reject, use template**.
4. **No-new-claims guard** — reject outputs containing forbidden lexemes (a small
   blocklist: "will rise", "will fall", "buy", "sell", "guaranteed", "prediction",
   "target price of" not in evidence, etc.).
5. **Length guard** — reject > 2 sentences / > N chars; use template.
6. **Total fallback** — any exception, timeout, or no-key → template. The product is
   fully functional with the LLM entirely off (AIG-3, FR-12).

The net guarantee: **a rendered body either equals the validated paraphrase of the
template or equals the template itself.** It can never contain a fact the deterministic
layer did not produce.

### 18.5 Confidence scoring

`Insight.confidence` is deterministic (data completeness/freshness), set *before* the LLM
runs. The LLM never sets or changes confidence. The UI may show "high/medium confidence"
derived from this number; the model has no influence over it.

### 18.6 Output format, tone, and writing guidelines

- **Format:** 1–2 sentences, plain prose, no markdown, no emoji, no exclamation.
- **Tone (After-Hours Desk):** calm, precise, trustworthy. *Reports* facts. Gains and
  losses are stated, never celebrated. No hype, no urgency, no second person imperatives
  ("you must"). Neutral, advisory-free pointers only ("you may want to review …").
- **Numbers:** Indian formatting via existing `fmt_inr`/`fmt_pct` is applied in the
  *template* (the model preserves the already-formatted strings). The model is told to
  keep numbers identical.
- **The `consider` pointer** (Recommendation): drawn from a fixed reviewed phrase set, not
  generated, so advice cannot creep in.
- **Forbidden:** predictions, advice, certainty language, celebration, marketing, any
  number/ticker not in evidence.

### 18.7 Template bodies

Every detector ships a deterministic template body (a format string over its evidence).
Templates are the spec's ground truth, are unit-tested, and are what renders when AI is
off. The LLM is a *finish*, never the *substance*.

---

## 19. Performance & Caching

### 19.1 Targets

| Operation | Budget |
|---|---|
| Deterministic detection (150 stocks, warm caches) | < 500 ms |
| Full panel render from warm intelligence cache | < 300 ms |
| Cold compute added over existing load | < 2 s (excl. LLM) |
| LLM narration | non-blocking; template shows first; enrichment as it streams |

### 19.2 Caching strategy

- **Intelligence cache.** Wrap `detect_all`+`rank`+health in a `@st.cache_data` keyed by a
  **portfolio fingerprint** (hash of tickers + shares + quote timestamps) plus the
  threshold-constants version. TTL aligned to the shortest upstream (quotes ~5 min).
  Cleared by "Refresh data" and "↻ Re-analyse".
- **New fetchers.** `fetch_earnings`/`fetch_holders` cached ≥ 6 h (these change slowly),
  parallelised with a bounded `ThreadPoolExecutor` exactly like `fetch_metadata`.
- **LLM cache.** Narrated bodies cached by insight `id` (which encodes category+tickers+
  date), so a re-render within the day costs no tokens.

### 19.3 Parallelism

- The earnings/holders fetchers reuse the existing `ThreadPoolExecutor(max_workers≤8)`
  pattern.
- The top-N LLM calls fire concurrently (one per insight); each is small and independent.

### 19.4 API rate limiting

- LLM: cap concurrency at N (= panel size, ≤ 5); exponential backoff on 429; on repeated
  failure, fall back to templates (no user-visible error).
- Market data: reuse existing bulk-download + per-ticker fallback + retry/backoff; the new
  fetchers inherit the same degrade-to-empty behaviour.

### 19.5 Failure recovery & lazy loading

- The 🧠 Intelligence section computes lazily — only when the section is selected *or* the
  Overview brief is shown (which it always is). Deep/optional fetchers (earnings,
  holders) only run when their detectors are enabled.
- Any fetcher failure → that detector silently no-ops; the rest of the panel renders.

---

## 20. Error Handling

| Condition | Behaviour |
|---|---|
| **Empty portfolio** | Panel shows "Upload a portfolio…" empty state. No detectors run. |
| **No insights fired** | Positive empty state ("Nothing demands attention today") + health score. |
| **Missing data for a detector** | That detector returns `[]` (FR-3). No partial/garbage insight. |
| **Stale data (> TTL)** | Affected insight's `freshness` drops → lower priority + "data may be stale" caption, or suppression if below a floor. |
| **API failure (quotes/meta)** | Existing graceful degradation; insights compute from resolved subset; caption notes coverage. |
| **earnings/holders fetch fails** | Fetcher returns `{}`; earnings/ownership detectors no-op. |
| **LLM timeout/error/no key** | Template body used; optional "narration unavailable" caption; no error surfaced. |
| **Invalid portfolio (all file-value)** | Concentration-by-file-value insights may still fire, flagged "based on file values"; price-dependent detectors no-op. |
| **Partial data (some unpriced)** | Data-Quality insight fires (§15.6f); other insights compute on priced subset; confidence reduced. |
| **Detector raises (must not happen)** | Caught at `detect_all` boundary per-detector; the offending detector is skipped, logged, others proceed. Section never crashes the app. |

Guiding rule (PRD posture): **the engine is silent or qualified before it is wrong.**

---

## 21. Testing Strategy

Follows the repo's existing pattern: `unittest` + inline DataFrame fixtures, no mocks, no
network (the pure layer needs none).

### 21.1 Unit tests (`tests/test_intelligence.py`)

- Each detector: a fixture that *just* crosses its threshold fires exactly one correctly
  shaped insight; a fixture just under does not fire; a missing-data fixture returns `[]`.
- Ranking: a hand-built insight list sorts by priority; ties broken deterministically;
  top-N selection and de-dup correct.
- Health score: the §16.6 worked example reproduces 85 exactly; boundary inputs hit band
  edges; all-missing inputs produce a defined (not NaN) score.
- Evidence freshness: file-value-only holdings yield reduced freshness/confidence.

### 21.2 Unit tests (`tests/test_ai_narrator.py`, no network)

- Validation: a synthetic LLM output with an extra number → rejected → template returned.
- Validation: an output with a forbidden lexeme → rejected.
- Validation: a faithful paraphrase → accepted.
- No-key path: returns templates, no exception.
(The actual provider call is dependency-injected so tests pass a stub function — no real
API hit.)

### 21.3 Integration tests

- Full pipeline on a realistic multi-account fixture: `build_context → detect_all → rank →
  narrate(stub) → assert top-N shape, links valid, every body traces to evidence`.
- Three storage modes: with/without a prior snapshot, drift detectors behave correctly.

### 21.4 End-to-end (manual + scripted Streamlit smoke)

- Load sample portfolios; assert the section renders, no exception, brief shows ≤ 5 cards,
  health gauge present, evidence expanders populated, section links navigate.

### 21.5 Performance tests

- A 150- and 500-stock synthetic book: detection < 500 ms / acceptable; assert no
  detector is O(n²).

### 21.6 Edge cases

Empty book; single holding (100% concentration — must fire cleanly, not divide-by-zero);
all-unpriced; all-N/A signals; no metadata; no snapshots; NaN-laden rows; one account vs
many.

### 21.7 Acceptance tests

Map 1:1 to §25; the feature is done only when all pass.

---

## 22. Security

### 22.1 API keys & secrets

- The LLM key (`ANTHROPIC_API_KEY`) lives **only** in `st.secrets` / environment, never in
  code or repo, gitignored locally — identical handling to the Supabase keys. Absent key →
  AI silently off.

### 22.2 Rate limiting & abuse

- LLM concurrency capped; backoff on 429; hard ceiling on calls per render (= panel
  size). A single dashboard load can never fan out beyond N small calls.

### 22.3 Prompt injection

- The LLM input is **structured evidence the engine itself produced**, plus ticker
  symbols. It does **not** include free user text. The one user-influenced field is the
  account *label* and ticker symbols — and account labels are **excluded** from prompts
  (§22.4). Tickers are validated NSE symbols. There is therefore no untrusted free-text
  channel into the prompt in v1. (If conversational follow-up is added later — §23 — that
  *does* introduce user text and MUST add input sanitisation + the same output validation.)

### 22.4 Data privacy

- AI is **opt-in** (requires a key). When on, the engine sends the LLM only the minimal
  evidence: tickers, metric values, thresholds — **never** account labels, user identity,
  email, or the full holdings list. The model sees one anonymised fact bundle at a time.
- In local mode with AI off (default), nothing about holdings leaves the machine beyond
  the existing anonymous market-data lookups (NFR-10).
- The "minimal evidence" rule is enforced in `ai_narrator` by constructing the prompt from
  an explicit allowlist of evidence fields, not by dumping objects.

### 22.5 Output safety

- Validated outputs (§18.4) cannot introduce numbers/claims; the blocklist prevents
  advice/prediction language reaching the user, protecting the "not financial advice"
  posture legally and ethically.

---

## 23. Future Roadmap

The architecture (registry of pure detectors + evidence firewall + thin NLG) is designed
so every item below is **a new detector + optional new cached fetcher**, with **no change
to the engine core, ranking, health score, or NLG**.

| Future insight | What it adds | New detector | New data |
|---|---|---|---|
| **Insider / promoter activity** | promoter pledge/buy-sell | `detect_insider` | NSE filings feed |
| **News sentiment** | headline tone per holding | `detect_news_sentiment` | existing `fetch_news_single` + a sentiment pass |
| **ESG exposure** | ESG flags | `detect_esg` | ESG data source |
| **Dividend risk** | payout sustainability | `detect_dividend_risk` | payout ratio (fundamentals) |
| **Options exposure** | (if positions added) | `detect_options` | — |
| **Macro exposure** | rate/FX sensitivity by sector | `detect_macro` | sector→factor map |
| **Correlation analysis** | true diversification | `detect_correlation` | history matrix |
| **Sector rotation** | momentum across sectors | `detect_rotation` | sector index history |
| **Analyst upgrades/downgrades** | rating changes | `detect_rating_change` | target/rec history snapshots |
| **Portfolio stress testing** | drawdown under scenarios | `detect_stress` | factor shocks |
| **Conversational follow-up** | ask "why?" about an insight | (NLG extension) | adds user text → requires §22.3 hardening |

Each is independently shippable. The registry guarantees additive growth.

---

## 24. Implementation Roadmap

Five phases. Each phase ships something testable and demoable.

### Phase 0 — Foundations & types

- **Deliverables:** `intelligence.py` with `Evidence`, `Insight`, `HealthScore`,
  `InsightCategory`, the registry scaffold, ranking, and `build_context`. Severity tokens
  in `formatting.py`.
- **Files created:** `intelligence.py`, `tests/test_intelligence.py`.
- **Files modified:** `formatting.py`.
- **Dependencies:** none new.
- **Testing:** ranking + type tests; empty/edge inputs.
- **DoD:** types finalised; `detect_all([])` returns `[]`; ranking unit-tested; no
  Streamlit import in `intelligence.py`.

### Phase 1 — Core deterministic detectors + health score

- **Deliverables:** detectors for Portfolio Risk, Technical Extremes, Overvaluation,
  Today's Move, Tax-Loss, Data-Quality; the Portfolio Health Score; deterministic
  templates for all.
- **Files modified:** `intelligence.py`, `analytics.py` (≤ 1 helper if needed).
- **Dependencies:** existing analytics only.
- **Testing:** §21.1 threshold/boundary/missing-data tests per detector; §16.6 health
  example.
- **DoD:** each detector fires exactly at threshold, no-ops on missing data, ≥ 90%
  branch coverage on detectors; health reproduces the worked example.

### Phase 2 — UI integration (deterministic, no AI)

- **Deliverables:** 🧠 Intelligence section + Overview condensed brief; insight cards;
  health gauge; evidence expanders; section links; skeleton + empty/positive/error
  states; `SECTIONS` entry; intelligence cache + "↻ Re-analyse".
- **Files modified:** `app.py`, `charts.py` (`health_gauge`).
- **Dependencies:** Phase 1.
- **Testing:** Streamlit smoke E2E (§21.4); accessibility pass (§10.8); the brief renders
  for all sample portfolios with no exception.
- **DoD:** full panel works with **no LLM**; all §10 states render; design-review clean
  (One-Lamp, no nested cards, severity not colour-alone).

### Phase 3 — New data fetchers + earnings/ownership detectors

- **Deliverables:** `fetch_earnings`, `fetch_holders` (cached, parallel, degrade-to-empty);
  Earnings and Ownership detectors; Concentration-Drift, Analyst-Shift,
  Dividend-Concentration detectors (snapshot-aware).
- **Files modified:** `market_data.py`, `intelligence.py`. Optional: insight persistence
  via `store` (FR-16).
- **Dependencies:** Phase 2; existing snapshot store.
- **Testing:** fetcher degrade-to-empty; detectors no-op without data/prior snapshot.
- **DoD:** earnings/ownership insights appear only with present data; never fabricate a
  date/change; confidence capped per §15.5.

### Phase 4 — AI narration layer

- **Deliverables:** `ai_narrator.py` — closed-world prompt, provider call (Claude),
  numeric/entity/lexeme validation, template fallback, per-insight cache; template-first
  progressive render in `app.py`.
- **Files created:** `ai_narrator.py`, `tests/test_ai_narrator.py`.
- **Files modified:** `app.py` (swap template→narrated body when ready), `requirements.txt`
  (optional `anthropic`).
- **Dependencies:** Phases 1–3; `ANTHROPIC_API_KEY` secret (optional).
- **Testing:** §21.2 validation tests with a stubbed provider (no network); no-key path.
- **DoD:** with AI on, bodies are validated paraphrases; with AI off, identical layout via
  templates; **0** rendered numbers/tickers absent from evidence in a 50-portfolio audit.

### Phase 5 — Polish, docs, acceptance

- **Deliverables:** tuning of thresholds/weights against real portfolios; performance
  pass; `docs/explanation-intelligence-engine.md`; PRD update (new section).
- **DoD:** all §25 acceptance criteria pass; SC-1..SC-5 met.

---

## 25. Acceptance Criteria

The feature is complete only when **every** box is satisfied.

### 25.1 Evidence & honesty
- [ ] Every rendered insight links to a populated `Evidence` object (SC-1).
- [ ] No insight contains a number or ticker absent from its evidence (50-portfolio audit, SC-4, Phase 4 DoD).
- [ ] No detector fires on missing/NaN/insufficient data; it returns `[]` instead (FR-3).
- [ ] Insights on stale/file-value data are confidence-reduced or suppressed (US-6, §20).
- [ ] The "positive empty state" shows when nothing fires (no fabricated insights).

### 25.2 Detectors
- [ ] Portfolio Risk, Earnings, Overvaluation, Technical, Ownership detectors implemented per §15 (FR-6).
- [ ] Today's-Move, Concentration-Drift, Analyst-Shift, Tax-Loss, Dividend-Concentration, Data-Quality implemented where data exists (FR-7).
- [ ] Each detector fires exactly at its threshold and not just below (unit tests).
- [ ] Earnings/Ownership never fabricate a date or a "change" without real/prior data (§15.2/15.5).

### 25.3 Health score
- [ ] 0–100 score with band renders, reproducing the §16.6 example (FR-8).
- [ ] Every point traces to a named, weighted sub-score in the breakdown expander (AC-8.2).

### 25.4 Ranking & selection
- [ ] Insights ranked by the §14.5 priority score; top-3 (brief) / top-5 (section) selected.
- [ ] Cross-detector duplicates on the same ticker+theme de-duplicated.

### 25.5 AI layer
- [ ] With AI on, each body is a validated paraphrase of its template (FR-10/11).
- [ ] With AI off/unreachable/no key, templates render with identical layout and ranking (FR-12, US-7).
- [ ] Validation rejects extra numbers, unknown tickers, forbidden advice/prediction lexemes, over-length (§18.4).
- [ ] The LLM never sets severity, priority, or confidence.

### 25.6 UX & design
- [ ] 🧠 Intelligence section + Overview condensed brief render (FR-13).
- [ ] Insight cards: category chip, severity (glyph+word+tint, never colour-alone), title, body, Evidence expander, section link (FR-14, §10.8).
- [ ] Skeleton on cold load; positive/empty/error states per §10.5/10.6.
- [ ] Design review passes: gold ≤ 10%, no nested cards, no shadows, Inter-only (§10.10).
- [ ] WCAG 2.1 AA: text contrast, keyboard focus, `prefers-reduced-motion` (§10.8).

### 25.7 Performance
- [ ] Detection < 500 ms (150 stocks, warm); warm panel < 300 ms; cold adds < 2 s ex-LLM (NFR-1).
- [ ] LLM narration is non-blocking (template-first); narrated bodies cached by id.
- [ ] New fetchers cached ≥ 6 h, parallel, degrade to `{}` (NFR-7).

### 25.8 Reliability & security
- [ ] Zero unhandled exceptions across the section for any supported portfolio (NFR-2).
- [ ] The Intelligence section failing never affects the other ten sections (§10.6, §20).
- [ ] LLM receives only allowlisted evidence — never account labels/identity/PII (§22.4).
- [ ] No untrusted free-text reaches the prompt in v1 (§22.3).
- [ ] API key only in secrets; AI fully opt-in; "↻ Re-analyse" and "Refresh data" clear caches.

### 25.9 Architecture & tests
- [ ] `intelligence.py` is pure (no `streamlit`/I/O imports) (NFR-9).
- [ ] Adding a new detector requires only a function + registry entry (NFR-3).
- [ ] `tests/test_intelligence.py` and `tests/test_ai_narrator.py` pass with no network (§21).
- [ ] `docs/explanation-intelligence-engine.md` written; PRD updated.

---

*End of Engineering Design Specification v1.0.*
