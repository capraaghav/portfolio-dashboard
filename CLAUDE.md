# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
pip3 install -r requirements.txt   # first time only
streamlit run app.py               # opens http://localhost:8501
```

If `streamlit` isn't on PATH after install:
```bash
~/Library/Python/3.9/bin/streamlit run app.py
```

Clear all caches (prices, metadata, TA) via the in-app **🔄 Refresh data** button, or call `.clear()` on any `@st.cache_data` function in `market_data.py`.

## Module responsibilities

| File | Role |
|---|---|
| `app.py` | Streamlit entrypoint. All UI sections, sidebar, CSS, data-flow orchestration. Single long file — each tab/section is a top-level `if section == "…":` block. |
| `market_data.py` | All Yahoo Finance I/O (`yfinance`). `@st.cache_data`-decorated functions for quotes, metadata, TA signals, dividends, history. Also handles symbol resolution (company name / ISIN → NSE/BSE ticker). |
| `analytics.py` | Pure computation: holdings consolidation, RSI/SMA signals, tax (LTCG/STCG), XIRR, risk metrics, rebalance drift. No I/O, no Streamlit. |
| `charts.py` | Plotly figure builders, one function per chart. Returns `go.Figure` or `None`. |
| `parsers.py` | Broker CSV/Excel/PDF parsing. Auto-detects Zerodha, Groww, Upstox, Angel One, HDFC, Reliance, IndusInd, IIFL. Normalises to a canonical DataFrame with columns `ticker, qty, avg_cost, ltp, account`. |
| `formatting.py` | All theme tokens (`GOLD`, `GAIN`, `LOSS`, `BG`, etc.) and `fmt_inr`, `fmt_pct`, `fmt_num`, `fmt_mcap` helpers. Single source of truth — `app.py` imports the palette directly into its CSS `:root {}` block. |
| `storage.py` | Local file persistence under `./data/`: snapshots, last session (parquet), watchlist, price overrides. Also handles multi-user mode (path isolation per visitor session). |
| `db.py` | Supabase backend — mirrors `storage.py`'s function signatures. Activated when `SUPABASE_URL` + `SUPABASE_ANON_KEY` are in `st.secrets`. Handles email login, refresh-token cookie, optional 2FA. |
| `click_spark.py` | Self-contained custom Streamlit component that adds click-spark particle effects. |

## Data flow

```
User uploads CSV/Excel/PDF
  → parsers.parse_all()            # returns raw DataFrame
  → md.resolve_symbols()           # company name / ISIN → ticker (Yahoo search)
  → md.fetch_quotes()              # live prices, cached 5 min
  → md.fetch_metadata()            # sectors, names, analyst targets, fundamentals, cached 1 h
  → analytics.build_holdings()     # consolidates multi-account rows, applies prices
  → per-section rendering in app.py
```

## Backend / storage modes

`app.py` selects `store = db if db.is_enabled() else storage` at startup and calls `store.<fn>` uniformly throughout. Three runtime modes:

1. **Local** (default): `storage.py`, data under `./data/`.
2. **Multi-user hosted** (`PORTFOLIO_MULTIUSER=1` secret): `storage.py` with a per-visitor temp directory — no persistence across visits.
3. **Supabase** (`SUPABASE_URL` + `SUPABASE_ANON_KEY` secrets): `db.py`, full auth + per-user cloud persistence.

The Supabase client is per-session (`st.session_state["sb"]`), never `@st.cache_resource` — that would share auth state across users.

## Key conventions

- **Colour tokens are defined once in `formatting.py`** and injected into CSS via f-string in `app.py`. Don't hardcode hex colours anywhere else.
- **`@st.cache_data` parameters prefixed with `_`** are excluded from the cache key (used to pass suffix maps and other non-serialisable args without breaking caching).
- **Tickers stored as plain NSE symbols** (e.g. `RELIANCE`, not `RELIANCE.NS`). The `.NS`/`.BO` suffix is resolved at fetch time via `suffix_map` and never persisted.
- **`parsers.py` must produce columns**: `ticker, qty, avg_cost, ltp, account`. Optional: `qty_lt` (Zerodha long-term quantity for tax).
- **`analytics.build_holdings()`** is idempotent and stateless — call it again anytime the filter state changes rather than mutating the result.

## Deployment

See `DEPLOY.md` for Streamlit Community Cloud steps. The `data/` directory is gitignored; snapshots and session data never go to the repo.
