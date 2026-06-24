# Reference — Modules

Factual reference for every Python module in the project. One section per module:
its responsibility, the public functions worth knowing, and what goes in and comes
out. Signatures and defaults are taken verbatim from the source.

The app is a single-page Streamlit dashboard. `app.py` is the entry point and
orchestrates the others; everything else is a library it imports.

---

## `app.py`

**Responsibility.** Streamlit entry point and UI orchestration. Builds the page,
the sidebar (brand, navigation, upload/data toggles), and every section. It wires
the data layer (`parsers` → `market_data` → `analytics`) to the render layer
(`charts`, `formatting`) and the persistence layer (`storage` or `db`). Run with
`streamlit run app.py`.

Top-level constants and switches:

- `LANDING_URL = "https://capraaghav.github.io/portfolio-dashboard/"` — link to the
  standalone marketing page. Must stay in sync with `APP_URL` in `index.html`. See
  [reference-config.md](reference-config.md).
- `USE_DB = db.is_enabled()` — true when Supabase secrets are present; selects the
  cloud backend.
- `store = db if USE_DB else storage` — the active persistence module. Both expose
  the same function names, so the rest of the app calls `store.<fn>(...)` uniformly.
- `MULTIUSER = (not USE_DB) and _is_multiuser()` — local per-session isolation mode.
- `SECTIONS` — the 11 navigation entries: Overview, Holdings, Performance, Technical,
  Analysts, Tax, Risk, Dividends, Stock Detail, Watchlist, Rebalance.

Selected helpers:

- `_is_multiuser() -> bool` — true if `PORTFOLIO_MULTIUSER` is `"1"` in the env or in
  `st.secrets`.
- `render_landing(subline: str) -> None` — compact in-app hero shown above the login
  form / upload prompt.
- `_wk52_pct(ticker, prices_map, fund_map)` — position of the live price within the
  52-week band, as a percent (or `NaN`).
- `_pnl_styler(disp_df, num_df, cols)` — tints gain/loss columns mint/coral by numeric
  sign while keeping the `+/-` in the text, so meaning never relies on colour alone
  (WCAG-safe).
- `to_excel_bytes(holdings_df, totals) -> bytes` — builds the two-sheet (Summary +
  Holdings) Excel export.
- `_go_to_detail(ticker, guard) -> None` / `_plotly_clicked_ticker(ev) -> str | None`
  — click-through navigation from charts/tables into the Stock Detail section.

---

## `parsers.py`

**Responsibility.** Read a broker's CSV / Excel / PDF export and normalise it into one
canonical schema — one row per holding-per-account. No network, no Streamlit. The
output columns are documented in [reference-broker-formats.md](reference-broker-formats.md).

Key public functions:

- `parse_all(uploaded, account_names: dict) -> tuple[pd.DataFrame | None, list]` — the
  top-level entry. Parses a list of uploaded files; returns
  `(combined_df_or_None, errors)` where `errors` is a list of `(filename, message)`.
- `parse_uploaded_file(f, account_name: str) -> pd.DataFrame` — parse a single
  file-like object into the normalised schema. Detects PDF/Excel/CSV by extension,
  finds the header row, maps columns, coerces numerics, tags the `account`.
- `detect_broker(df) -> str` — returns the matching key in `BROKER_FORMATS`, else
  `"generic"`.
- `normalize_generic(df) -> pd.DataFrame` — rename columns of an unknown export using
  `GENERIC_ALIASES`.
- `parse_pdf(raw_bytes: bytes) -> pd.DataFrame` — extract holdings from a
  portfolio-statement PDF (needs `pdfplumber`); raises `ValueError` on a scanned or
  unrecognised layout.
- `find_excel_header(raw_bytes) -> tuple` — `(sheet_name, header_row_index)` for the
  best data header across all sheets.
- `find_csv_header_row(lines) -> int` — line index of the most header-like CSV row.

Classification / cleaning helpers (used here and in `market_data`):

- `is_isin(s: str) -> bool` — true for an Indian ISIN (`INE002A01018`-style: 12 chars,
  starts with `IN`).
- `looks_like_symbol(s: str) -> bool` — true if the value is already a clean ticker
  (no spaces, 1–15 chars, `[A-Z0-9&.\-]`), not a verbose company name.
- `classify_asset(name: str) -> str` — `"Equity"`, `"Mutual Fund"`, or `"Bond/NCD"`.
- `clean_company_name(name: str) -> str` — strip broker instrument suffixes
  (`-EQ`, `LIMITED`, face values, NSE series codes) to a searchable name.

**Output schema:** `ticker, shares, avg_cost, ltp, current_value, pnl, account, isin,
sector, qty_long_term, purchase_date`. Numeric columns are coerced (₹, commas, `%`
stripped); `purchase_date` is parsed `dayfirst=True`.

---

## `market_data.py`

**Responsibility.** All Yahoo Finance data fetching for Indian NSE/BSE tickers,
cached via `st.cache_data`. Resolves company names → tickers, fetches live quotes,
metadata (sector / name / analyst targets / fundamentals), technical signals,
dividends, per-stock history/news, and benchmark indices.

Cache TTLs (from the module docstring and decorators):

| Function | TTL | What it caches |
| --- | --- | --- |
| `fetch_quotes` | 300 s (5 min) | live prices + day change |
| `fetch_metadata` | 3600 s (1 hr) | sector, name, analyst targets, fundamentals |
| `fetch_ta_signals` | 3600 s (1 hr) | 200d history → SMA/RSI signals |
| `fetch_dividends` | 21600 s (6 hr) | TTM dividend, yield, last payout |
| `fetch_benchmark` | 3600 s (1 hr) | index close series |
| `fetch_closes` | 3600 s (1 hr) | close series for the basket backtest |
| `fetch_history_single` | 1800 s (30 min) | one stock's OHLC history |
| `fetch_news_single` | 1800 s (30 min) | one stock's headlines |
| `resolve_symbols` | 86400 s (24 hr) | name/ISIN → ticker resolution |
| `fetch_nse_master` | 86400 s (24 hr) | NSE official equity list |

Note: arguments whose names start with `_` (e.g. `_suffix_map`, `_query_map`,
`_ltp_map`, `_price_map`) are excluded from the cache key — they pass dicts without
breaking caching.

Key public functions:

- `fetch_quotes(tickers: tuple) -> dict` — `{ticker: {price, prev_close, day_chg,
  day_chg_pct, suffix}}`. Bulk-downloads 5d closes per exchange (`.NS` then `.BO`),
  computes close-over-close day change, falls back to `fast_info` for stragglers, and
  guarantees an entry for every ticker.
- `prices_from_quotes(quotes) -> dict` / `suffix_map_from_quotes(quotes) -> dict` —
  pull `{ticker: price}` and `{ticker: suffix}` out of a quotes dict.
- `resolve_symbols(names: tuple, _query_map: dict, _ltp_map: dict) -> dict` —
  `{original_name: bare_ticker_or_None}`. Resolution chain: Yahoo search (with
  CSV-price disambiguation) → NSE official symbol master → DuckDuckGo (price-validated).
- `fetch_nse_master() -> dict` — NSE's official equity list as
  `{"isin": {...}, "names": [(norm_name, symbol)], "symbols": set}`.
- `fetch_metadata(tickers: tuple, _suffix_map: dict) -> dict` — returns
  `{"sectors", "names", "analyst", "fundamentals"}`, each keyed by ticker. `analyst`
  carries target low/high/mean/median, analyst count and recommendation; `fundamentals`
  carries P/E, P/B, market cap, beta, ROE, margins, debt/equity, div yield, 52-week
  high/low, industry.
- `fetch_ta_signals(tickers: tuple, _suffix_map: dict) -> dict` — `{ticker: signal}`,
  each signal computed by `analytics.compute_signal` over 200d closes.
- `fetch_dividends(tickers, _suffix_map, _price_map) -> dict` — `{ticker: {ttm,
  yield_pct, last_amount, last_date, history}}`.
- `fetch_history_single(ticker, suffix, period="1y") -> pd.DataFrame` — OHLC for one
  stock.
- `fetch_news_single(ticker, suffix, limit=6) -> list` — `[{title, link, publisher}]`.
- `fetch_closes(tickers, _suffix_map, period="1y") -> dict` — `{ticker: close_series}`
  for the basket backtest.
- `fetch_benchmark(symbol, period="1y") -> pd.Series` — index close series.

Constants: `SUFFIXES = [".NS", ".BO"]`; `BENCHMARKS = {"NIFTY 50": "^NSEI", "SENSEX":
"^BSESN", "NIFTY Bank": "^NSEBANK", "NIFTY Midcap 100": "^NSEMDCP50"}`.

---

## `analytics.py`

**Responsibility.** Pure portfolio math — no I/O, no Streamlit, easily unit-tested.
Holdings consolidation, technical-indicator math, risk/concentration metrics, Indian
LTCG/STCG tax estimation, tax-loss harvesting, XIRR/CAGR, and rebalancing drift.

Tax constants (post-23 Jul 2024 Budget; estimates only):
`LTCG_RATE = 0.125`, `LTCG_EXEMPTION = 125_000`, `STCG_RATE = 0.20`,
`LT_HOLDING_DAYS = 365`.

Key public functions:

- `build_holdings(raw: pd.DataFrame, prices: dict, meta: dict) -> pd.DataFrame` —
  consolidate raw per-account rows into one row per ticker. Output columns include
  `Ticker, Company, Shares, Avg Cost (₹), Live Price (₹), Current Value (₹),
  Cost Basis (₹), Gain/Loss (₹), Gain/Loss (%), Sector, Accounts`, plus hidden
  `_lt_shares` and `_first_buy`. Sorted by current value descending.
- `portfolio_totals(holdings) -> dict` — `{value, cost, pnl, pnl_pct, n_holdings}`.
- `per_account_breakdown(sub, prices, meta) -> pd.DataFrame` — one row per account for
  a single ticker's slice (reuses `build_holdings` so figures reconcile).
- `rsi(series, period=14) -> float` and `compute_signal(closes) -> dict` — RSI-14 and
  a trend signal `{signal, label, rsi, vs_50ma}` from SMA20/50/200 crossovers.
- `risk_metrics(holdings, fundamentals=None) -> dict` — `{hhi, effective_n, top1_pct,
  top1_ticker, top5_pct, top_sector, top_sector_pct, portfolio_beta, n_positions}`.
  HHI is the Herfindahl concentration index; `effective_n = 1/hhi`.
- `tax_breakdown(raw, prices, meta) -> dict` — splits unrealised gains into long-term
  vs short-term (using the broker's `qty_long_term` column, else `purchase_date`, else
  "unknown") and estimates LTCG/STCG tax. Returns gains, exemption used, taxable
  amounts, per-tax totals, and a per-ticker breakdown.
- `harvest_candidates(holdings) -> pd.DataFrame` — positions at an unrealised loss,
  sorted worst-first, for tax-loss harvesting.
- `xirr(cashflows: list[tuple], guess=0.1) -> float | None` — Newton-Raphson XIRR over
  `(date, amount)` flows (investments negative, value positive); annualised rate as a
  fraction.
- `portfolio_xirr(raw, holdings) -> float | None` — XIRR using purchase dates as buy
  flows + today's mark-to-market value. Returns `None` without `purchase_date`.
- `synthetic_curve(closes, shares_map) -> pd.Series` — value of today's share
  quantities over history (a "what if I'd held this exact basket" backtest).
- `normalize_to_100(series) -> pd.Series` — rebase a series to 100 at its start.
- `rebalance_plan(holdings, targets: dict) -> pd.DataFrame` — drift and ₹-to-trade per
  holding given `{ticker: target_pct}`.

---

## `charts.py`

**Responsibility.** Reusable Plotly figure builders. Each returns a `go.Figure` (or
`None` when there's no data); `app.py` renders it. Imports the theme palette from
`formatting.py` and installs a global dark Plotly template (`portfolio`,
transparent background, Inter font, muted grid) as the default.

Each function takes a prepared DataFrame/Series/dict and returns `go.Figure | None`:

- `pie_by_stock(chart_data, top_n=12)` — donut of top-N holdings by value, rest folded
  into "Others".
- `pie_by_sector(chart_data)` — donut by sector.
- `treemap(holdings)` — value-sized, P&L-coloured treemap (Portfolio → Sector →
  Ticker), red→green diverging at 0.
- `account_stacked(bar_data)` — holdings stacked by account.
- `vs_50ma_bar(ta_signals, order=None)` — each holding's price vs its 50-day MA;
  `order` locks row order to match the RSI chart.
- `rsi_bar(ta_signals, order=None)` — RSI bars with shaded overbought (>70) / oversold
  (<30) zones.
- `signal_distribution_bar(counts)` — single stacked bar of the bull→bear trend mix.
- `analyst_range(rng_df)` — target low→high ranges with mean diamonds, vs current
  price.
- `snapshot_line(snap_df)` — portfolio value over time, with the invested-cost line.
- `benchmark_overlay(port_norm, bench_norm, bench_name)` — portfolio vs index, rebased
  to 100.
- `candlestick(hist, ticker, avg_cost=None)` — OHLC with SMA50/200 and an avg-cost
  line.
- `wk52_gauge(price, low, high)` — 52-week range gauge.
- `dividend_history(divs)` — per-share dividend bars (last 5 years).

---

## `formatting.py`

**Responsibility.** Number formatting (Indian lakh/crore conventions) and the shared
colour/label constants — the single source of truth for the dark, champagne-gold
theme. `app.py` projects these into CSS custom properties; `charts.py` reads them for
figure styling.

Theme tokens (hex):

| Token | Value | Use |
| --- | --- | --- |
| `GOLD` | `#C9A87A` | primary accent — brand, hero value, chart lines |
| `GAIN` | `#3DDC97` | positive (mint green) |
| `LOSS` | `#F0564A` | negative (coral red) |
| `BG` | `#0A0A0A` | app background |
| `SURFACE` | `#141414` | cards / panels |
| `BORDER` | `#262626` | card borders / dividers |
| `TEXT` | `#EDEDED` | primary text |
| `MUTED` | `#8B8B8B` | secondary / labels |
| `GRID` | `#1F1F1F` | chart gridlines |
| `SIDEBAR` | `#0C0C0C` | sidebar surface |
| `PANEL` | `#121212` | container cards |
| `HOVER` | `#161616` | control / nav hover |
| `SELECTED` | `#18170F` | gold-tinted black — active nav row |
| `SHIMMER` | `#1F1F1F` | skeleton-loader sweep |
| `BORDER_HAIRLINE` | `#1C1C1C` | dividers, sidebar edge |
| `BORDER_PANEL` | `#232323` | container-card border |
| `BORDER_CONTROL` | `#2A2A2A` | button / control border |
| `INK_SOFT` | `#B9B9B9` | nav label default |
| `MUTED_DEEP` | `#808080` | tertiary text floor (AA-safe, 5.0:1 on `BG`) |
| `DISABLED` | `#555555` | disabled glyphs / N-A |

Also: `SIGNAL_ORDER` and `SIGNAL_COLOR` (trend signal labels/colours),
`REC_LABEL` and `REC_COLOR` (analyst recommendation labels/colours).

Formatting functions:

- `fmt_inr(val, short=False) -> str` — `₹1,234.56`, or short form `₹1.23 Cr` / `₹1.23 L`
  / `₹1.2 K`. Missing → `—`.
- `fmt_pct(val) -> str` — `+12.34%`; missing → `—`.
- `fmt_num(val, decimals=2) -> str` — thousands-grouped number; missing → `—`.
- `fmt_mcap(val) -> str` — market cap in crore (`₹1,234 Cr` or `₹1.23 L Cr`).

All four tolerate strings, `NaN`, `inf`, and the odd non-numeric value Yahoo returns
(via the internal `_num` coercion).

---

## `storage.py`

**Responsibility.** Local persistence — portfolio snapshots (performance history) and
the last parsed session (so the user need not re-upload), plus watchlist and manual
price overrides. Everything is written under `./data/` next to the app; nothing leaves
the machine.

Files: `snapshots.json`, `last_session.parquet` (+ `.json` meta; CSV fallback if
`pyarrow` is missing), `watchlist.json`, `price_overrides.json`.

Key public functions:

- `configure(data_dir) -> None` — point all persistence at a different directory. Used
  in multi-user mode to give each visitor an isolated folder.
- `save_snapshot(totals, holdings, when=None) -> bool` / `load_snapshots() -> list[dict]`
  / `snapshots_df() -> pd.DataFrame` — one snapshot per calendar date (re-saving
  overwrites today).
- `auto_snapshot_if_new(totals, holdings) -> bool` — save at most once per calendar
  day; returns `True` if it wrote.
- `save_session(raw) -> None` / `load_session() -> pd.DataFrame | None` /
  `session_meta() -> dict` — persist and reload the parsed portfolio.
- `load_watchlist() -> list[str]` / `save_watchlist(tickers) -> None`.
- `load_overrides() -> dict` / `save_overrides(overrides) -> None`.

`db.py` mirrors these signatures exactly, so `app.py` swaps backends with one variable
(`store = db if USE_DB else storage`).

---

## `db.py`

**Responsibility.** Supabase backend — email-login accounts and per-user cloud
persistence. Activated only when `SUPABASE_URL` + `SUPABASE_ANON_KEY` are present in
`st.secrets` and the `supabase` package is installed; otherwise the app falls back to
`storage.py`. Mirrors `storage.py`'s persistence signatures and adds auth. Postgres
row-level security keeps each user's rows private.

Config / client:

- `is_enabled() -> bool` — true when Supabase secrets are present and importable.
- `_client()` — a per-session client (intentionally not `cache_resource`, which would
  share auth across users).

Cookie / session restore (keeps you logged in across a full browser refresh):

- `init_cookies() -> None` — construct the `CookieManager` once per run, before any
  get/set.
- `persist_cookie() -> None` — (re)write the refresh-token cookie on each logged-in
  run.
- `restore_session() -> None` — re-authenticate from the cookie after a refresh wipes
  `session_state`.

Auth:

- `current_user() -> dict | None` — `{'id', 'email'}` or `None`.
- `sign_in(email, password) -> tuple[str, str | None]` — status is `'ok'`, `'2fa'`
  (password ok, code emailed), or `'error'`.
- `sign_up(email, password) -> tuple[bool, str | None]`.
- `sign_out() -> None` — signs out and wipes session keys.
- `verify_email_otp(email, token) -> tuple[bool, str | None]` and
  `resend_email_otp(email) -> tuple[bool, str | None]` — email 2FA flow.
- `twofa_enabled() -> bool` / `set_twofa(enabled) -> tuple[bool, str | None]` — read /
  toggle the per-user email-2FA preference (stored in Supabase user metadata).
- `render_auth() -> None` — the branded login / sign-up gate.

Per-user storage (same names as `storage.py`): `save_session`, `load_session`,
`session_meta`, `load_watchlist`, `save_watchlist`, `load_overrides`, `save_overrides`,
`load_snapshots`, `save_snapshot`, `snapshots_df`, `auto_snapshot_if_new`. Backed by
the `user_state` table (single row per user, keyed `user_id`) and the `snapshots`
table (PK `(user_id, snap_date)`).

---

## `click_spark.py`

**Responsibility.** A click-burst spark animation ported from React Bits to Streamlit.
Draws a transparent, full-window `<canvas>` over the whole app and sparks wherever you
click. The script is injected into the document that owns the app UI so it survives
Streamlit reruns (a guard prevents double-init; each rerun refreshes the live config).

Single public function:

- `click_spark(spark_color="#C9A87A", spark_size=13, spark_radius=30, spark_count=9,
  duration=400, easing="ease-out", extra_scale=1.0) -> None` — enable the global
  click-spark effect. Call once per run (e.g. right after the page CSS). Props mirror
  the React component.

---

## Related

- [reference-broker-formats.md](reference-broker-formats.md) — supported broker exports
  and the canonical parsed schema.
- [reference-config.md](reference-config.md) — runtime config, backend switches,
  sidebar toggles, cache TTLs, and the cross-linked URLs.
- [explanation-architecture.md](explanation-architecture.md) — why the modules are
  split this way and how data flows through them.
- [howto-add-a-broker.md](howto-add-a-broker.md) — add support for a new broker export.
