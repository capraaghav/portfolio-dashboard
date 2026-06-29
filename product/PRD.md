# Product Requirements Document — Portfolio Dashboard

| | |
|---|---|
| **Product** | Portfolio Dashboard — unified stock-portfolio analytics for Indian markets (NSE/BSE) |
| **Document version** | 2.1 |
| **Status** | Live (shipped) |
| **Last updated** | 2026-06-29 |
| **Owner** | Raaghav Pilaniwala |
| **Repository** | github.com/capraaghav/portfolio-dashboard |
| **Landing page** | capraaghav.github.io/portfolio-dashboard/ (standalone GitHub Pages) |
| **Tech stack** | Python · Streamlit · pandas · numpy · yfinance · Plotly · pdfplumber · openpyxl · Supabase (optional) |

---

## 1. Product overview & vision

Portfolio Dashboard is a **single-page web application that consolidates a retail
investor's stock holdings from any Indian brokerage account into one unified,
trustworthy analytics dashboard.** A user drops in one or more account exports (CSV,
Excel, or PDF), and the app normalises wildly different broker formats into a single
dataset, resolves each holding to its live NSE/BSE ticker, fetches live prices and
fundamentals from Yahoo Finance, and presents valuation, allocation, technicals,
analyst targets, tax, risk, dividends, per-stock detail, benchmarking, and
rebalancing across thirteen layered sections, with an AI intelligence layer that
surfaces the most important findings first.

### 1.1 Vision

> **Everything you own, in one honest view.**

No single broker shows a consolidated, analysis-rich picture, and generic portfolio
apps don't understand Indian-market specifics. The vision is a calm, precise,
trustworthy desk — the feeling of a discreet private-banking statement rather than a
trading-floor ticker — where a person can **drop in a messy broker export and, within
seconds, trust the numbers enough to act on them.** Depth (technical, fundamental,
tax, risk, analyst) is available on demand, layered behind the consolidated picture
rather than dumped all at once.

The product is **local-first and privacy-respecting** by design: holdings are
processed on the user's own machine and never uploaded to a third party — the only
outbound calls are anonymous market-data lookups. It can also be **hosted as a
zero-install shared link**, in which case each visitor's data is isolated to their own
session, and optionally placed behind **email-login accounts with per-user cloud
persistence and opt-in two-factor authentication**, so a portfolio follows its owner
across devices while staying private to their account.

### 1.2 The defining capability

The differentiator is the **ingestion & resolution engine.** It accepts the messy,
inconsistent exports Indian brokers actually produce — company names instead of
tickers, ISIN-only rows, NSE series suffixes, multi-sheet workbooks, metadata
headers, footers/disclaimers, formatted PDF statements — and reliably turns them into
clean, live-priced, consolidated holdings. Crucially, it **never mis-assigns**: a
holding it cannot resolve with confidence is kept at its file value and flagged,
rather than guessed. Honesty over false precision is the product's posture, not an
afterthought.

### 1.3 Voice & posture

The product speaks in the voice of **quiet expertise — calm, precise, trustworthy.**
It states facts plainly, lets the numbers carry weight, and never sells excitement.
Gains and losses are *reported*, not *celebrated*. It rejects the loud retail trading
app (neon, gamification, confetti), the cluttered Bloomberg terminal (wall-to-wall
data with no hierarchy), cartoonish fintech (mascots, "friendly money"), and generic
SaaS slop (purple gradients, hero-metric templates). The full visual expression of
this posture lives in `DESIGN.md` ("The After-Hours Desk").

---

## 2. Problem statement

### 2.1 The investor's reality

A typical Indian retail investor holds stocks across **several brokerage accounts**
(e.g. Zerodha, HDFC Securities, Groww) and often across **multiple family members'
demat accounts**. Each broker:

- Exports in a **different file format** (CSV, Excel, PDF) with different column
  names, layouts, sheet structures, and number formatting.
- Identifies holdings inconsistently — some give clean tickers (`RELIANCE`), some
  give full company names (`"ABB INDIA LIMITED EQ NEW RS. 2/-"`), some give only an
  **ISIN** (`INE263A01024`), some append **NSE series suffixes** (`INDOWIND-BE`).
- Provides **partial data** — some omit cost basis, some omit purchase dates, some
  mix mutual funds and bonds in with equities.

As a result there is **no single place** where the investor can see their *true*
consolidated position, total gain/loss, allocation, concentration risk, or tax
exposure across all accounts.

### 2.2 Why existing solutions fall short

| Alternative | Why it falls short |
|---|---|
| **Broker portals** | Each shows only its own account. None offers a consolidated, multi-broker view; the investor must mentally stitch 3–5 portals together. |
| **Credential-linking aggregators** | Require handing over broker logins — a privacy/security concern for personal financial data — and often charge a subscription. |
| **Generic / Western portfolio apps** | Miss Indian-market specifics: ISIN↔NSE/BSE symbol resolution, NSE series suffixes, Zerodha's *Quantity Long Term* column, NIFTY 50 / SENSEX benchmarks, and Indian tax rules (LTCG/STCG, ₹1.25 L exemption). |
| **Spreadsheets** | Manual, error-prone, no live prices, no technical/analyst/risk layers, and re-built from scratch every quarter. |

There is no **free, private, multi-broker, multi-format** tool that "just works" on
the files these brokers actually produce — and that understands the Indian market
deeply enough to be trusted. That gap is the product.

---

## 3. Target users & personas

The audience is **self-directed Indian retail investors** in NSE/BSE equities who
hold positions across multiple brokers. They are financially literate — they read P/E
and beta, think in terms of XIRR and sector concentration — and their context is
**reflective, not reactive**: they open the dashboard on a *weekly or monthly cadence*
to understand their position, not to day-trade. The core job is **"drop in a broker
export and immediately see the truth about my portfolio,"** with enough depth to make
a considered decision. Privacy of financial data is a first-order concern.

| Persona | Description | Key needs |
|---|---|---|
| **Primary — The multi-account retail investor** | Holds equities across 2–4 broker/demat accounts; moderately-to-highly financially literate; privacy-conscious; reviews monthly. | Consolidated value & P&L, allocation, tax exposure, "am I beating NIFTY?", concentration risk. |
| **Secondary — The family-portfolio manager** | Manages portfolios for family members across different brokers; wants a per-account / per-person split alongside the combined picture. | Combine all accounts into one view, per-account drill-down, per-person breakdown. |
| **Tertiary — The shared-link recipient** | A friend/relative the primary user shares the hosted app with; non-technical, often on Windows. | Zero install, upload own file, see own dashboard privately — never seeing anyone else's data. |
| **Quaternary — The account holder (hosted)** | A public sign-up on the hosted deployment who wants their portfolio to persist across devices and reboots, with account security. | Email login, cloud persistence of session/snapshots/watchlist/overrides, optional 2FA, isolation from other users. |

**Explicitly not the audience:** day-traders and tick-watchers (the product is
deliberately not real-time), and anyone wanting it to place orders or move money.

---

## 4. Goals & non-goals

### 4.1 Goals

- **G1 — Universal ingestion.** Accept exports from any major Indian broker in CSV,
  Excel, or PDF, auto-detecting the format with no user configuration.
- **G2 — Reliable identity resolution.** Resolve every holding to its correct live
  NSE/BSE ticker, even from company names or ISINs, **without mis-assigning**.
- **G3 — One consolidated view.** Merge the same stock held across accounts into a
  single position, while preserving the per-account breakdown.
- **G4 — Layered analytics.** Deliver valuation, allocation, technical, fundamental,
  analyst, tax, risk, and dividend analysis in one place — depth on demand.
- **G5 — Privacy by default.** No holdings data leaves the user's machine in local
  mode; isolated per-session in hosted mode; per-user RLS-isolated in accounts mode.
- **G6 — Zero-friction operation.** One command (or one double-click) locally; one URL
  when hosted. No accounts, no API keys required to use the analytics.
- **G7 — Trust through honesty.** Surface un-priced tickers, missing dates, stale
  data, and assumptions plainly; never imply precision or success that isn't there.

### 4.2 Success metrics

- ≥ 95% of holdings in a typical multi-broker upload resolve to a live ticker.
- Consolidated totals reconcile to within rounding of each broker's own stated totals.
- Zero unhandled exceptions across all sections for any supported file.
- A non-technical user goes from file → dashboard in under 2 minutes.
- A user returns regularly because the picture is clearer here than anywhere else.

### 4.3 Non-goals (explicitly out of scope)

- **No order execution / money movement.** The app never trades, transfers, or places
  orders. Rebalancing only *suggests* quantities to buy/sell.
- **No financial advice.** Tax figures, targets, and signals are **estimates and
  information, not advice.**
- **No broker API / credential linking.** Input is files only (a deliberate privacy
  choice).
- **No real-time tick streaming.** Prices are close/last-traded snapshots, cached.
- **No multi-currency / non-Indian markets** (NSE/BSE focus; figures in ₹).
- **No mutual-fund NAV engine / SIP tracking** (MFs are detected and shown at file
  value, not deeply analysed).
- **No multi-user collaboration / sharing.** Accounts, when enabled, are private and
  single-owner — no shared portfolios, teams, or social features.
- **No mandatory accounts.** Accounts and a cloud database are an **optional, opt-in**
  backend (§9); the app fully functions with no account and no backend.

---

## 5. User stories

1. *As an investor,* I upload my Zerodha and HDFC exports together and see one
   consolidated portfolio with combined value and gain/loss.
2. *As an investor,* when a stock is held in two accounts, I click its row and see how
   many shares and how much value sit in each account.
3. *As an investor,* I upload an HDFC file that lists company names instead of tickers,
   and the app still prices everything live.
4. *As an investor,* I upload an IIFL PDF statement and it extracts all my holdings.
5. *As an investor,* I see my LTCG vs STCG split and an estimate of tax if I sold today.
6. *As an investor,* I check whether my basket has beaten the NIFTY 50 over the past year.
7. *As an investor,* I see which positions are over-concentrated and which sectors dominate.
8. *As a privacy-conscious user,* I run the whole thing on my laptop and confirm no
   holdings data is uploaded anywhere.
9. *As a sharer,* I send a friend a link; they open it on Windows, upload their own
   file, and never see my data nor I theirs.
10. *As a hosted account holder,* I sign up with my email, turn on two-factor login,
    and find my portfolio waiting for me on a different device after a reboot.

---

## 6. Functional requirements

### 6.1 Data ingestion & normalisation
- **FR-1.1** Accept multiple files at once via drag-and-drop; each file = one account,
  with a user-editable account label.
- **FR-1.2** Support file types: **CSV, XLSX, XLS, PDF**.
- **FR-1.3** Auto-detect known broker formats by their column signatures: Zerodha
  Kite, Zerodha Console (incl. detailed Excel with Sector + Long-Term Qty), HDFC
  Securities, Reliance/IndusInd (depository style), Groww, Upstox, Angel One, IIFL
  Portfolio+ (PDF).
- **FR-1.4** For unknown formats, **fuzzy-match column headers** to a canonical schema
  (ticker, shares, avg_cost, ltp, current_value, pnl, isin, sector, qty_long_term,
  purchase_date) using an alias dictionary; normalise `UPPER_SNAKE_CASE`
  (`NSE_SYMBOL`, `COST_PRICE`, `ISIN_CODE`) by treating underscores as spaces.
- **FR-1.5** **Excel:** auto-detect the correct sheet and the header row even when
  buried under metadata rows; handle multi-sheet workbooks.
- **FR-1.6** **CSV:** auto-detect the header line under preamble/metadata rows.
- **FR-1.7** **PDF:** extract holdings page-by-page from text-based portfolio
  statements (e.g. IIFL Portfolio+), detecting ALL-CAPS ticker rows, skipping sector
  headings / column headers / footers, parsing Indian-comma numbers and parenthesised
  negatives. Reject scanned/image PDFs with a clear message.
- **FR-1.8** Parse Indian-formatted numbers: lakh/crore commas (`1,09,912.73`),
  parenthesised negatives (`(-7,400.64)`), `₹`, `%`, and `--`/blank tokens.
- **FR-1.9** Drop junk rows: totals, blank rows, footer/disclaimer paragraphs
  (length-capped).
- **FR-1.10** Strip NSE series suffixes from tickers (`-BE`, `-BZ`, `-SM`, `-EQ`…)
  without harming legitimately hyphenated symbols (`BAJAJ-AUTO`).
- **FR-1.11** Surface per-file parse errors without failing the whole upload.

### 6.2 Ticker identity resolution (the core differentiator)
A holding may arrive as a clean ticker, a full company name, or only an ISIN. The app
resolves each to a bare NSE/BSE symbol through a **3-pass chain**, and **never
mis-assigns** — an unresolved holding is kept at its file value rather than guessed.

| Pass | Source | Role |
|---|---|---|
| **Pass 1** | **Yahoo Finance search** (`query2.finance.yahoo.com/v1/finance/search`) | Resolve cleaned company names; disambiguate look-alikes by matching the candidate's live price to the file's own LTP. |
| **Pass 2** | **NSE official equity master** (`archives.nseindia.com/.../EQUITY_L.csv`) | Authoritative for ISINs and for names Yahoo misses (knows current names, e.g. Adani Wilmar → `AWL`). |
| **Pass 3** | **Broader web search (DuckDuckGo HTML)** | Last resort for renamed companies; accepts a symbol **only if its live price matches the file's price**, so it cannot assign a popular ticker to an obscure/suspended holding. |

- **FR-2.1** **Clean tickers** pass through unchanged.
- **FR-2.2** **Company names** are cleaned (strip `LIMITED`, `EQ`, face-value junk) and
  resolved via Pass 1, price-disambiguated (so "ABB India" → ABB not Abbott India;
  "SAIL EQUITY SHARES" → SAIL not Sai Life Sciences).
- **FR-2.3** **ISINs** are resolved authoritatively via the NSE master (Pass 2),
  falling back to Yahoo.
- **FR-2.4** Resolution is **cached 24 h**. The UI reports how many names/ISINs were
  auto-matched and how many could not be (shown at file value, flagged).
- **FR-2.5** Detect non-equity instruments — **mutual funds** and **bonds/NCDs** — and
  value them from the file (no live equity data), with an **"Equity only"** toggle to
  exclude them entirely.
- **FR-2.6** Allow **manual price override** for any holding Yahoo can't price.

### 6.3 Consolidation
- **FR-3.1** Merge identical tickers across accounts into one position with total
  shares, weighted average cost, combined value, and aggregate gain/loss.
- **FR-3.2** Preserve the list of contributing accounts per position.
- **FR-3.3** Compute live current value = total shares × live price, falling back to
  the broker-reported value when no live price is available.

### 6.4 Market data (Yahoo Finance via yfinance)
- **FR-4.1** **Live quotes** — last price + previous close (for day change), fetched in
  **one bulk request per exchange** to avoid rate limits; per-ticker fallback for
  stragglers; numeric fields coerced to finite floats. Cached ~5 min.
- **FR-4.2** **Metadata** (cached 1 h, with retries) — sector, company name, analyst
  targets, fundamentals (P/E, P/B, market cap, beta, ROE, 52-week range), all from a
  single `.info` call per stock; numeric fields coerced at the source.
- **FR-4.3** **Technical history** — 200 days of closes, bulk-downloaded.
- **FR-4.4** **Dividends** — trailing-12-month dividends + yield, per stock.
- **FR-4.5** **Benchmark indices** — NIFTY 50, SENSEX, Bank Nifty, Midcap.
- **FR-4.6** **Per-stock detail** — 1-year OHLC history and recent news, on demand.
- **FR-4.7** A **"Refresh data"** action clears all caches and re-fetches.

### 6.5 Dashboard — the thirteen sections
Navigation is a left sidebar list (not horizontal tabs); the constant
`SECTIONS = ["🧠 Intelligence", "📊 Overview", "📋 Holdings", "📈 Performance",
"🔬 Technical", "🔎 Screener", "🎯 Analysts", "🧮 Tax", "⚠️ Risk", "💰 Dividends",
"🔍 Stock Detail", "👁️ Watchlist", "⚖️ Rebalance"]` defines the order.

| # | Section | Requirements |
|---|---|---|
| 1 | **🧠 Intelligence** | AI Portfolio Intelligence Engine (§6.10): ranked, evidence-backed insights + an explainable 0–100 Portfolio Health Score; today's-move card; per-insight evidence and a link to the proving section. Generated deterministically from the other sections' analytics — never invented. |
| 2 | **📊 Overview** | Condensed top-3 intelligence brief; treemap heatmap (size = value, colour = P&L, grouped by sector); allocation donuts by stock and by sector; per-account totals table + stacked bar (when >1 account). |
| 3 | **📋 Holdings** | Sortable/searchable table; toggle fundamentals columns; **export to Excel**; **manual price override**; **click a row → per-account split** of that stock (shares, cost, value, P&L per account + TOTAL) for stocks held in 2+ accounts. **Filters (combinable):** sector, asset type (Equity/Fund/Bond), technical trend signal, account, and a **"held in all accounts only"** toggle — each narrows the table to matching holdings. |
| 4 | **📈 Performance** | Auto-saved daily **snapshots** → portfolio value timeline; **XIRR** (when purchase dates exist); **benchmark backtest** of the current basket vs a chosen index, with alpha. |
| 5 | **🔬 Technical** | SMA 20/50/200 + RSI 14 → trend signal per stock (Strong Bull → Strong Bear); signal-count cards; vs-50MA and RSI bar charts. |
| 6 | **🔎 Screener** | Find *new* stocks: scans the Nifty 500 / Nifty 50 (or an uploaded watchlist, or held stocks) for a momentum setup — SMA10 crossing SMA50 with RSI in a healthy 50–65 band — showing why each passed/failed, with CSV/Excel export. |
| 7 | **🎯 Analysts** | 12-month consensus price targets (low/mean/high) with upside %, Buy/Hold/Sell consensus, # analysts; target-range chart; coverage count. |
| 8 | **🧮 Tax** | **LTCG/STCG split** (uses long-term-qty or purchase dates); estimated tax (India rates); tax-loss-harvesting candidates. Headed with an explicit "Estimate only — not tax advice" caption. |
| 9 | **⚠️ Risk** | Largest position %, top-5 weight, effective # holdings (1/HHI), portfolio beta, sector concentration; concentration warnings. |
| 10 | **💰 Dividends** | TTM dividend income per stock, portfolio yield, income chart (requires dividend-data toggle). |
| 11 | **🔍 Stock Detail** | Per-stock candlestick (1y) with SMA + avg-cost line, 52-week gauge, fundamentals, analyst consensus, dividend history, recent news (live-priced equities only). Reachable by clicking through from other sections. |
| 12 | **👁️ Watchlist** | Track non-owned tickers (live price, day change, analyst target); persisted. |
| 13 | **⚖️ Rebalance** | Editable target weights → drift and ₹ to buy/sell per holding; **never executes**. |

### 6.6 Summary cards (always visible)
Total value, total gain/loss (₹ + %), today's change, # holdings, # accounts, live
price coverage (X/Y). Gain/loss shows "—" when the file has no cost basis.

### 6.7 Persistence
- **FR-7.1** Auto-save a **daily snapshot** of total value + per-stock values.
- **FR-7.2** Remember the **last session** so the user can reload without re-uploading;
  the loaded session survives reruns (filtering/interaction does not drop it).
- **FR-7.3** Persist **watchlist** and **manual price overrides**.
- **FR-7.4** **Local / per-session storage (default):** all persistence under a local
  `data/` folder; in hosted multi-user mode, an isolated per-session temp folder.
- **FR-7.5** **Cloud storage (optional, Supabase):** the same four artifacts (last
  session, snapshots, watchlist, overrides) stored **per user in Supabase Postgres**
  instead of local files, keyed to the authenticated user and protected by row-level
  security. The cloud layer is interface-compatible with the local one (`db.py`
  mirrors `storage.py`), so call sites are identical:
  `store = db if db.is_enabled() else storage`.

### 6.8 Accounts & authentication (optional backend)
*Active only when `SUPABASE_URL` + `SUPABASE_ANON_KEY` secrets are present; otherwise
the app runs with no login, exactly as the local-first product.*

- **FR-8.1** **Email login / sign-up gate** (Supabase Auth). When enabled, an
  unauthenticated visitor sees a branded login / sign-up screen; the dashboard is
  withheld until they authenticate.
- **FR-8.2** **Per-user data isolation via row-level security** — each user can read
  and write only their own rows (`auth.uid() = user_id`); enforced in Postgres, not
  just the client.
- **FR-8.3** **Optional email-OTP two-factor authentication.** A user can turn on
  email 2FA (stored in their own Supabase user metadata, `twofa_email`, no schema
  change). When on, a correct password returns a `"2fa"` state and a 6-digit one-time
  code is emailed; the dashboard unlocks only after `verify_email_otp()` succeeds. A
  "resend code" path is provided, and send failures surface the **real underlying
  reason** (e.g. email-OTP not enabled for the project) rather than a generic error.
- **FR-8.4** **Stay logged in across a browser refresh** — the Supabase refresh token
  is held in a browser cookie and used to re-authenticate on load, so a hard refresh
  (which clears Streamlit session state) restores the session. Tokens rotate on
  refresh; logout deletes the cookie and clears all per-user session state
  (`sb`, `sb_session`, `sb_user`, `sb_2fa`, `_2fa_email`) so the next user on a shared
  browser starts clean.
- **FR-8.5** **Sidebar account controls** — the logged-in user's email, a 2FA toggle,
  and a **Log out** button; the privacy caption reflects the active storage mode.
- **FR-8.6** **Graceful, additive design** — the anon key is safe client-side (RLS is
  the protection); if the backend is unconfigured or unreachable, the app falls back
  to local behaviour rather than failing.

### 6.9 Interface & feedback polish
- **FR-9.1** **Skeleton loaders** — a dashboard-shaped placeholder (eyebrow + hero +
  four KPI cards + chart block) renders during the first cold data load, replaced once
  holdings are built; skipped on warm reruns to avoid flicker. Honors
  `prefers-reduced-motion`.
- **FR-9.2** **Click-spark effect** — a lightweight gold canvas animation emits sparks
  from each click (ported from a React component to a Streamlit-injected canvas overlay
  that persists across reruns). Purely decorative; non-blocking; respects
  `prefers-reduced-motion`.

### 6.10 AI Portfolio Intelligence Engine
A premium intelligence layer that reviews the portfolio every time the dashboard opens
and answers **"what are the most important things I should know about my portfolio
today?"** It detects, ranks, and explains the findings an institutional portfolio
manager would flag. Its defining constraint: **the engine never invents conclusions.**
Every insight is produced by a deterministic detector over the analytics the app
already computes; the (optional) natural-language layer only summarises evidence that
already exists. The full design lives in
[`EDS-ai-portfolio-intelligence.md`](EDS-ai-portfolio-intelligence.md).

- **FR-10.1** **Deterministic detection.** Insights are generated by pure detectors
  (`intelligence.py`, no I/O, like `analytics.py`) over holdings, risk metrics, TA
  signals, tax, metadata, and quotes. A detector that lacks sufficient/fresh data
  returns nothing rather than guessing.
- **FR-10.2** **Insight catalogue (v1).** Portfolio Risk (single-position / top-5 /
  sector concentration, thin effective-N, off-band beta), Technical Extremes (overbought
  RSI, escalated near a 52-week high), Overvaluation (above analyst mean target and/or
  rich P/E vs sector median), Tax-Loss Opportunity (harvestable losses, flagged when
  gains exist to offset), Today's Move, and Data-Quality (un-priced holdings). Each
  carries a category, severity, confidence, evidence object, and a link to the section
  that proves it.
- **FR-10.3** **Priority ranking.** Insights are ranked by a deterministic score
  (severity × magnitude × confidence × freshness), de-duplicated, and the top N surfaced
  (top 5 in the section, top 3 in the Overview brief).
- **FR-10.4** **Portfolio Health Score.** A 0–100, fully explainable score from five
  named, weighted sub-scores — Diversification (0.30), Sector balance (0.20), Valuation
  (0.20), Volatility (0.15), Data quality (0.15) — with a band (Resilient / Balanced /
  Watchful / Fragile) and a per-component breakdown. No opaque number; every point
  traces to a metric.
- **FR-10.5** **Evidence & traceability.** Every insight exposes the exact metric values
  and thresholds that fired it, and links to the proving section. The product's honesty
  posture, made into a feature.
- **FR-10.6** **Optional, gracefully-degrading AI narration.** A natural-language layer
  may paraphrase each insight's deterministic body, but only under a closed-world prompt
  constrained to that insight's evidence, with post-generation validation; if no AI is
  configured or it is unreachable, the deterministic templates render with no functional
  difference. AI is opt-in and never a dependency.
- **FR-10.7** **Not advice.** The engine is not an automated trading system, not
  financial advice, and not predictive — it describes the present state and known facts,
  carrying the same "information, not advice" caption as the Tax section (§4.3).

---

## 7. Non-functional requirements

- **NFR-1 Privacy.** In local mode, holdings never leave the machine; only anonymous
  market-data lookups (Yahoo / NSE / DuckDuckGo) go out. In hosted per-session mode
  (`PORTFOLIO_MULTIUSER=1`), each browser session gets an isolated temp directory. In
  accounts mode (Supabase), holdings are stored in the user's own database rows,
  isolated by Postgres RLS; secrets live only in Streamlit secrets and are never
  committed (the anon key is safe to expose — RLS is the control).
- **NFR-2 Resilience to rate limits.** Bulk-download quotes/history; retry `.info`
  with backoff; gracefully degrade (fall back to Yahoo-only, or file value) if a data
  source is unreachable; never crash on a missing/odd field (numeric coercion +
  defensive formatters).
- **NFR-3 Performance.** First (cold) load of a ~150-stock multi-broker portfolio
  completes in tens of seconds; subsequent interactions are instant via caching
  (~5 min quotes, 1 h metadata/TA, 24 h resolution & NSE master).
- **NFR-4 Robustness.** Zero unhandled exceptions across sections for any supported
  file; per-file parse errors are surfaced, not fatal.
- **NFR-5 Usability.** No configuration, accounts, or API keys required for the
  analytics; Indian number formatting (₹, lakh/crore); clear messaging for
  unresolved / un-priced / file-only rows.
- **NFR-6 Portability.** Runs on macOS, Windows, Linux (Python 3.9–3.14) locally, and
  on Streamlit Community Cloud.

### 7.1 Accessibility (WCAG 2.1 AA)
- **NFR-A1** Target **WCAG 2.1 AA**: body text ≥ 4.5:1 and large text ≥ 3:1 against the
  near-black canvas. The grey ramp bottoms out at `#808080` (5.0:1) for any *text*
  role; `#555555` and darker are reserved for disabled glyphs and hairlines only.
- **NFR-A2** **P&L is never communicated by colour alone.** Mint (gain) / coral (loss)
  is always paired with the sign (`+`/`−`), the formatted figure, or a label, so
  colour-blind users read the position correctly (DESIGN.md "The P&L Is Not Just Color
  Rule"). This is non-negotiable for a finance tool.
- **NFR-A3** Controls are **keyboard-reachable** with **visible focus states** (focus
  ring shifts toward gold but stays visible).
- **NFR-A4** **`prefers-reduced-motion`** is honored for both the click-spark and the
  skeleton-shimmer (hold the mid-tone steady instead of animating the sweep).

---

## 8. Technical architecture

**Pattern:** a single Streamlit application composed of focused, independently-testable
Python modules, plus a **separate standalone GitHub Pages landing site**. Default state
is the uploaded file plus a local `data/` folder and Streamlit's per-session cache; an
**optional Supabase backend** can swap in cloud accounts + per-user storage without
changing call sites.

### 8.1 Two pages, cross-linked

| Page | What it is | Hosting |
|---|---|---|
| **Landing site** (`index.html`) | A standalone, marketing/explainer page — hero, privacy section, supported-brokers, features, a preview of the desk, and a closing CTA. Pure HTML/CSS/Inter, design-matched to the app (champagne-gold-on-near-black). Two config placeholders (`#APP_URL`, `#REPO_URL`) are written into every matching link by a tiny inline script. | **GitHub Pages** (capraaghav.github.io/portfolio-dashboard/). |
| **App** (`app.py` + modules) | The actual Streamlit dashboard. | **Streamlit Community Cloud.** |

The landing page's "Launch dashboard" / "Open app" links point at the Streamlit app;
the app and landing cross-link. They are deliberately **two separate deployments** —
the landing is a static page that loads instantly and carries no data, while the app
carries the analytics.

### 8.2 Modules

| Module | Responsibility |
|---|---|
| `app.py` | UI orchestration: sidebar, data-loading pipeline, summary cards, the 13 sections, hosting/multi-user gating, the backend selector (`store = db if db.is_enabled() else storage`), and the auth gate (incl. the 2FA step). |
| `parsers.py` | File reading + broker detection + normalisation to the canonical schema; CSV/Excel/PDF; company-name cleaning; ISIN/series-suffix handling. |
| `market_data.py` | All Yahoo Finance fetching (quotes, metadata, TA history, dividends, benchmarks, per-stock detail), the 3-pass resolution chain, and the NSE master fetch. Cached. |
| `analytics.py` | Pure (no-I/O) computation: holdings consolidation, totals, per-account breakdown, technical indicators, risk metrics, LTCG/STCG tax, XIRR, synthetic backtest curve, rebalancing. |
| `intelligence.py` | **AI Portfolio Intelligence Engine** (§6.10) — pure (no-I/O) detection over `analytics` output: `Insight`/`HealthScore` models, a detector registry, priority ranking, and the explainable health score. `analyze()` is the entry point; detectors never invent — they return nothing on missing data. |
| `screener.py` | Momentum screener helpers (watchlist-upload parsing) for the 🔎 Screener section; scans an equity universe for SMA10/50 crossovers with a healthy RSI band. |
| `charts.py` | Reusable Plotly figure builders (treemap, donuts, candlestick, benchmark overlay, etc.). |
| `storage.py` | Local persistence (snapshots, last session, watchlist, overrides); configurable data directory for per-session isolation. |
| `db.py` | **Optional Supabase backend** — email auth (sign-in/up/out, cookie-based session restore, **email-OTP 2FA**) + per-user cloud storage, mirroring `storage.py`'s signatures as a drop-in alternative; per-session client; activates only when secrets are present. |
| `click_spark.py` | Decorative click-spark canvas overlay (JS injected via a Streamlit component, persists across reruns). |
| `formatting.py` | Indian ₹/%/number formatters (defensive: coerce-or-"—") + shared colour/label constants. |
| `index.html` | The standalone GitHub Pages landing page (no Python; design-matched). |

### 8.3 Data flow
`upload → parsers.parse_all → market_data.resolve_symbols (3-pass) → rename to clean
tickers → market_data.fetch_quotes (+ optional metadata/TA/dividends) →
analytics.build_holdings → intelligence.analyze (deterministic insights + health score)
→ sections render via charts + formatting.`

### 8.4 Storage / hosting modes

| Mode | Trigger | Persistence | Isolation |
|---|---|---|---|
| **Local-first (default)** | No secrets set | Local `data/` folder | Single user (your machine) |
| **Hosted, per-session** | `PORTFOLIO_MULTIUSER=1` | Isolated per-session temp folder | Per browser session |
| **Hosted, accounts** | `SUPABASE_URL` + `SUPABASE_ANON_KEY` set | Supabase Postgres, per user | Postgres RLS (`auth.uid() = user_id`) + optional email-OTP 2FA |

At startup `db.is_enabled()` checks for Supabase secrets + the `supabase` package; if
present the app gates on login and routes all persistence through `db.py`, otherwise it
uses `storage.py`. The Supabase client is created **per session** (in
`st.session_state`, never `cache_resource`, which would be shared across users); auth
tokens are kept in session state plus a refresh-token cookie.

### 8.5 External services
*(read-only, anonymous, always)* Yahoo Finance (`yfinance` + the finance search
endpoint), NSE archives (`EQUITY_L.csv`), DuckDuckGo HTML search. *(authenticated,
per-user, only when accounts are enabled)* Supabase Auth + Postgres REST (incl.
transactional email for OTP codes).

### 8.6 Key dependencies
streamlit ≥ 1.35, pandas, numpy, yfinance, plotly, openpyxl, pyarrow, curl_cffi,
pdfplumber; *(optional accounts)* supabase ≥ 2.0, extra-streamlit-components ≥ 0.1.71.

---

## 9. Data dictionary (canonical schema)

| Field | Meaning | Source |
|---|---|---|
| `ticker` | NSE/BSE symbol (post-resolution) | broker file → resolution |
| `shares` | Quantity held | broker file |
| `avg_cost` | Purchase/average price per share | broker file (may be absent) |
| `ltp` | Last traded price from the file | broker file |
| `current_value` | Broker-reported market value | broker file (fallback) |
| `pnl` | Broker-reported P&L | broker file (optional) |
| `isin` | ISIN code | broker file (optional) |
| `sector` | Sector/industry | broker file or Yahoo |
| `qty_long_term` | Shares held > 12 months | broker file (for tax) |
| `purchase_date` | Buy date | broker file (for XIRR) |
| `account` | Account label (= file) | user |

---

## 10. Deployment & operations

- **Local:** `pip install -r requirements.txt` then `streamlit run app.py`, or
  double-click `run.command` (macOS) / `run.bat` (Windows). Opens at `localhost:8501`.
  Persistent `data/` folder.
- **Hosted app (shared link, no accounts):** push to GitHub → deploy on Streamlit
  Community Cloud, with secret `PORTFOLIO_MULTIUSER = "1"` to enable per-session
  isolation. Auto-rebuilds on each push.
- **Hosted app with accounts (optional):** create a Supabase project, run the schema
  (`user_state` + `snapshots` tables, each with RLS policies `auth.uid() = user_id`),
  enable email-OTP in Supabase Auth settings (for 2FA), and add `SUPABASE_URL` +
  `SUPABASE_ANON_KEY` to Streamlit secrets (and a gitignored local
  `.streamlit/secrets.toml` for dev). Once present, the app requires login for all
  visitors and stores data per user. Secrets are never committed.
- **Landing page:** the standalone `index.html` is published via **GitHub Pages**
  (capraaghav.github.io/portfolio-dashboard/). Before deploying, set the `#APP_URL`
  (live Streamlit app) and `#REPO_URL` (public repo) placeholders. It is independent
  of the app deployment and carries no user data.
- **Distribution:** a clean zip (`run.command`/`run.bat` + code, `data/` excluded) for
  recipients who prefer to run locally.

---

## 11. Limitations & known constraints

- **Market-data accuracy depends on Yahoo Finance** — prices are close/last-traded,
  not real-time ticks; coverage is best for large/mid-cap NSE stocks.
- **Analyst targets are 12-month** consensus (no free 6-month source for India).
- **Performance history** builds over time from daily snapshots; the benchmark
  backtest replays *today's* quantities (ignores when shares were actually bought —
  treat it as "what if I'd held this basket the whole period").
- **XIRR requires purchase dates**, which most holdings exports omit (a tradebook is
  needed).
- **Tax figures are estimates, not advice** (India listed-equity, post-Jul 2024:
  **LTCG 12.5%** above the **₹1.25 L/yr** exemption; **STCG 20%**).
- **PDF support is text-based only** — scanned/image statements need OCR (not built).
- **Renamed-with-no-price / suspended / delisted** holdings may stay unresolved (by
  design — shown at file value, never mis-assigned).
- **Hosted mode** depends on Streamlit Cloud's shared IPs, which NSE/DuckDuckGo may
  occasionally block; the app degrades gracefully to Yahoo-only.

---

## 12. Future roadmap (candidate enhancements)

- OCR for scanned PDF statements.
- Tradebook ingestion for accurate XIRR + realised-gains history.
- Mutual-fund NAV resolution (AMFI) and deeper MF analytics.
- Alerts (price / target / rebalance-drift) and goal tracking.
- A small curated rename/alias map for well-known corporate renames.
- Correlation matrix / drawdown analytics on the Risk section.
- Auth enhancements for accounts mode: password reset, email-verification flow, OAuth
  providers, TOTP authenticator-app 2FA, and an optional "continue as guest"
  (no-account) path on the login screen.

---

## 13. Glossary

- **LTP** — Last Traded Price. **ISIN** — International Securities Identification
  Number. **LTCG/STCG** — Long/Short-Term Capital Gains. **XIRR** — money-weighted
  annualised return. **HHI** — Herfindahl-Hirschman concentration index. **NSE/BSE** —
  National / Bombay Stock Exchange. **NCD** — Non-Convertible Debenture. **SMA/RSI** —
  Simple Moving Average / Relative Strength Index. **RLS** — Row-Level Security
  (Postgres per-row access control). **OTP / 2FA** — One-Time Password / Two-Factor
  Authentication. **Anon key** — Supabase's public client key, safe to expose because
  RLS enforces access.
