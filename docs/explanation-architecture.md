# Explanation — End-to-end architecture

> Diátaxis: **Explanation.** Why the app is shaped this way, and the reasoning
> behind the one-way data flow. For *what each function does*, see
> [reference-modules.md](reference-modules.md).

## The problem

A retail investor in Indian markets holds equities across several brokers —
Zerodha, Groww, Upstox, HDFC Securities, and more. Each broker shows only its own
slice, in its own column names, with its own idea of a "symbol" (some give a clean
ticker, some a full company name, some only an ISIN). No one screen tells the truth
about the whole portfolio: total value, allocation, tax exposure, concentration.

So the app's whole job is a **funnel**: take messy, heterogeneous broker exports at
the wide end and produce one trustworthy, analysis-rich view at the narrow end. The
architecture is that funnel, made literal. It runs top-to-bottom on every Streamlit
rerun, and each stage only depends on the stage above it.

## The data flow

```
  broker files (CSV / XLSX / PDF, one per account)
        │
        ▼
  parsers.parse_all(uploaded, account_names)
        │   one normalised DataFrame: ticker, shares, avg_cost, account, ltp, …
        │   (rows are still per-account, symbols still messy)
        ▼
  symbol triage  (app.py)
        │   classify each symbol: clean ticker / ISIN / company name
        │   only the messy ones go to resolution
        ▼
  market_data.resolve_symbols(names, query_map, ltp_map)        [cached 24h]
        │   3-pass resolution, per name, in a thread pool:
        │     1. Yahoo Finance search   (CSV LTP disambiguates look-alikes)
        │     2. NSE official EQUITY_L master list (authoritative for ISIN)
        │     3. broader web fallback (DuckDuckGo), price-validated
        │   → {original_name: bare_ticker_or_None}
        ▼
  rename to resolved tickers; build asset-type + display-name maps (app.py)
        │
        ▼
  market_data fetchers  (all @st.cache_data, keyed on the ticker tuple)
        │   fetch_quotes        5 min   live price + day change (bulk download)
        │   fetch_metadata      1 hour  sector, name, analyst targets, fundamentals
        │   fetch_ta_signals    1 hour  200d history → SMA/RSI signal
        │   fetch_dividends     6 hour  trailing-12-month dividends + yield
        │   (metadata/TA/dividends only if their sidebar toggle is on)
        ▼
  analytics.build_holdings(raw, prices, meta)
        │   consolidate per-account rows → ONE row per ticker
        │   (sum shares, weighted avg cost, value, P&L, sector, account list)
        ▼
  analytics.portfolio_totals(holdings)   +   store.auto_snapshot_if_new(...)
        │   portfolio value / cost / P&L  ·  one silent daily snapshot
        ▼
  intelligence.analyze(holdings, raw, prices, meta, totals, ta_signals, quotes)
        │   pure detection → ranked, evidence-backed insights + health score
        │   (deterministic; detectors return [] on missing data, never invent)
        ▼
  render ONE of 13 sidebar sections
        Intelligence · Overview · Holdings · Performance · Technical · Screener ·
        Analysts · Tax · Risk · Dividends · Stock Detail · Watchlist · Rebalance
```

## Why it is shaped this way

### One linear pass, recomputed every rerun

Streamlit re-runs the entire script on every interaction. The app leans into that
rather than fighting it: `app.py` reads top to bottom as the pipeline above. There is
no event graph, no observer wiring, no "controller" — the script *is* the controller.

- **Trade-off accepted:** recomputing on every click is wasteful in the abstract.
- **Why it's fine:** every expensive stage (`resolve_symbols`, the four fetchers) is
  wrapped in `@st.cache_data`. After the first cold load the reruns hit warm caches
  and the "recompute" is cheap DataFrame math. The cost we paid is a few hundred lines
  of cache decorators; the cost we avoided is an entire reactive-state framework.
- **The lever:** the *cold* first load is the slow path. That is why there is a
  dashboard-shaped skeleton (`_SKELETON`) shown until `st.session_state["_data_ready"]`
  is set, and why the sidebar toggles for metadata / TA / dividends default the
  expensive ones **off** — you don't pay for analysis you didn't ask for.

### Resolution is separated from fetching, and both are cached differently

Symbol resolution ("ABB INDIA" → `ABB`, an ISIN → a ticker) is slow, network-heavy,
and almost never changes — so it is cached **24 hours**. Live prices change all day —
so quotes are cached **5 minutes**. Splitting these into separate cached functions
lets each pick its own freshness without dragging the other along.

```
  resolve_symbols   24h   ← rarely changes, expensive
  fetch_metadata     1h   ← changes slowly
  fetch_ta_signals   1h
  fetch_dividends    6h
  fetch_quotes       5m   ← changes constantly, must stay fresh
```

- **Trade-off:** a renamed/relisted company can stay mis-resolved for up to 24h.
- **Mitigation:** the sidebar **Refresh data (clear cache)** button calls `.clear()`
  on every fetcher, the manual-fix escape hatch (price overrides) covers anything the
  resolver still can't price, and price-validation in the resolver means a wrong guess
  is usually *no* guess rather than a confidently-wrong one.

### The `_`-prefixed argument trick

The fetchers take `_suffix_map` / `_price_map` / `_query_map` arguments. Streamlit
**excludes** any argument whose name starts with `_` from the cache key. This lets the
app pass large, unhashable, per-run dicts (the resolved suffix map, the LTP map)
*through* a cached function without those dicts busting the cache. The cache key stays
the tuple of tickers — which is exactly the thing that should determine freshness.

### Rate-limit defence: bulk download, then fall back per-ticker

Yahoo Finance rate-limits aggressive per-ticker fetching. So `fetch_quotes`,
`fetch_ta_signals`, and `fetch_closes` all do **one** `yf.download` for the whole
basket (per exchange suffix), and only drop to per-ticker `ThreadPoolExecutor` fetches
for the stragglers the batch missed. One request for fifty stocks beats fifty
requests; the per-ticker path is the safety net, not the default.

### Consolidation is the product's whole point

`build_holdings` is where "messy multi-broker" becomes "one honest view": it groups
`raw` by ticker and collapses every per-account row into a single row — summed shares,
share-weighted average cost, current value, P&L, the merged list of accounts that hold
it. Everything downstream (totals, allocation, tax, risk, rebalance) reads this one
consolidated frame. It is deliberately **pure** (no I/O, no Streamlit) so it is trivial
to reason about and test, and so the per-account drill-down can reuse it by calling
`build_holdings` on a one-ticker slice.

### Graceful degradation, not hard requirements

The pipeline never hard-fails on missing data; each stage falls back:

- no cost basis in the file → value/allocation/technicals still render, P&L/tax/XIRR
  are skipped with an explainer
- Yahoo can't price a ticker → fall back to the CSV's reported value / LTP, and offer
  a manual price override in Holdings
- mutual funds & bonds have no Yahoo equity data → valued from the CSV, flagged as
  `CSV` rather than `Live`

This is why the funnel has so many `if`/`setdefault` guards: the input is broker
exports in the wild, and the app's promise is "drop in whatever you have and still get
a usable view."

## Related explanations

- [explanation-two-page-architecture.md](explanation-two-page-architecture.md) — why
  login + dashboard and the marketing landing are two separate pages.
- [explanation-storage-backends.md](explanation-storage-backends.md) — how the
  `store` indirection at the top of the pipeline chooses local files vs Supabase.
- [explanation-indian-market-specifics.md](explanation-indian-market-specifics.md) —
  the 3-pass resolution and NSE/BSE/tax detail in depth.
- [reference-modules.md](reference-modules.md) — per-module, per-function reference.
