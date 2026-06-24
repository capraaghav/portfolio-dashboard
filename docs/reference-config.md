# Reference — Configuration

Runtime configuration: the secrets/env that switch backends, the sidebar data
toggles, cache lifetimes, and the two cross-linked page URLs. Every value here
traces to source (`app.py`, `db.py`, `market_data.py`, `index.html`).

---

## Backend selection

The app has three persistence modes. They are selected at startup, in this order.

### Supabase cloud backend — `SUPABASE_URL` + `SUPABASE_ANON_KEY`

When **both** secrets are present in `st.secrets` and the `supabase` package is
importable, `db.is_enabled()` returns true and the app uses the Supabase backend
(`db.py`): email login is required, and each user's portfolio, snapshots, watchlist,
and overrides are stored privately in Postgres under row-level security.

```python
USE_DB = db.is_enabled()
store = db if USE_DB else storage
```

`store` is the active persistence module; the rest of `app.py` calls `store.<fn>(...)`
without caring which backend is live. When `USE_DB` is true, `app.py` also calls
`db.init_cookies()`, `db.restore_session()`, and (per logged-in run)
`db.persist_cookie()` so a browser refresh keeps you signed in. Logged-out visitors
see the landing hero plus `db.render_auth()`.

Optional, per-user (not config): email 2FA, stored in Supabase user metadata and
toggled in the sidebar Security expander.

### Multi-user local isolation — `PORTFOLIO_MULTIUSER=1`

When the Supabase backend is **not** active, setting `PORTFOLIO_MULTIUSER` to `"1"`
(in the environment **or** in `st.secrets`) turns on per-session isolation:

```python
MULTIUSER = (not USE_DB) and _is_multiuser()
```

Each browser session gets a random 12-char id and its own data directory under the OS
temp dir, via `storage.configure(...)`:

```
<tempdir>/portfolio_sessions/<session-id>/
```

So separate visitors of a single hosted instance don't see each other's local files.

### Default single-user local — neither set

With no Supabase secrets and `PORTFOLIO_MULTIUSER` unset, the app runs fully local:
`storage.py` writes everything under `./data/` next to `app.py`. Nothing leaves the
machine. This is the original local-only mode.

---

## Sidebar data toggles

Found in the sidebar "⚙️ Upload / Data" expander. Each controls how much Yahoo data is
fetched and which assets are included. Defaults are taken verbatim from `app.py`.

| Toggle (label) | Variable | Default | Effect |
| --- | --- | --- | --- |
| Equity only (remove funds & bonds) | `exclude_nonequity` | `False` | Drops mutual funds and bonds/NCDs from the entire dashboard (uses `classify_asset`). |
| Sectors, targets & fundamentals | `load_meta` | `True` | One Yahoo `.info` call per stock (sector, name, analyst targets, fundamentals). Slower on first load, cached 1 hour. |
| Technical analysis (SMA / RSI) | `load_ta` | `False` | Bulk-downloads 200d price history for SMA/RSI signals. ~10s first load, cached 1 hour. |
| Dividend data | `load_div` | `False` | Fetches dividend history per stock for the Dividends section. |

The "🔄 Refresh data (clear cache)" button clears the caches of `fetch_quotes`,
`fetch_metadata`, `fetch_ta_signals`, `fetch_dividends`, and `fetch_closes`, then
reruns.

Other sidebar / in-section controls that gate rendering rather than fetching: a Sector
filter and a "Show fundamentals (P/E, P/B, Mkt Cap, Beta, 52w)" checkbox (default
`False`, only shown when `load_meta` is on) and a "Held in all accounts only" filter on
the Holdings section.

---

## Cache TTLs (`market_data.py`)

Yahoo Finance calls are cached with `st.cache_data(ttl=…)`. Lifetimes (from the module
docstring and the decorators):

| Data | Function | TTL |
| --- | --- | --- |
| Live quotes (price + day change) | `fetch_quotes` | 300 s (5 min) |
| Metadata (sector, name, targets, fundamentals) | `fetch_metadata` | 3600 s (1 hr) |
| Technical signals (SMA / RSI) | `fetch_ta_signals` | 3600 s (1 hr) |
| Dividends | `fetch_dividends` | 21600 s (6 hr) |
| Benchmark index series | `fetch_benchmark` | 3600 s (1 hr) |
| Basket-backtest closes | `fetch_closes` | 3600 s (1 hr) |
| Single-stock history | `fetch_history_single` | 1800 s (30 min) |
| Single-stock news | `fetch_news_single` | 1800 s (30 min) |
| Symbol resolution | `resolve_symbols` | 86400 s (24 hr) |
| NSE official equity list | `fetch_nse_master` | 86400 s (24 hr) |

Note: parameters whose names begin with `_` (`_suffix_map`, `_query_map`, `_ltp_map`,
`_price_map`) are excluded from each function's cache key, so dicts can be passed
without breaking caching.

---

## Cross-linked page URLs

The product is two pages that point at each other and **must stay in sync**:

- **The app** (live Streamlit dashboard): `https://portfolio-dashboard-1.streamlit.app/`
- **The marketing landing page** (standalone, GitHub Pages):
  `https://capraaghav.github.io/portfolio-dashboard/`

### `APP_URL` — defined in `index.html`

```javascript
const APP_URL = "https://portfolio-dashboard-1.streamlit.app/";
```

Every "Launch dashboard" / "Open app" link on the landing page uses the placeholder
`href="#APP_URL"` with a `data-app-url` attribute; a small script rewrites those hrefs
to `APP_URL` at load. If the deployed Streamlit URL ever changes, update this constant
in `index.html`.

### `LANDING_URL` — defined in `app.py`

```python
LANDING_URL = "https://capraaghav.github.io/portfolio-dashboard/"  # standalone marketing page (GitHub Pages)
```

Used by `render_landing(...)` for the in-app "New here? See what it does →" link back
to the marketing page.

**Keep them consistent.** `APP_URL` points landing → app; `LANDING_URL` points app →
landing. If either deployment URL changes, update both constants so the round trip
keeps working.

---

## Related

- [reference-modules.md](reference-modules.md) — per-module reference (`app.py`,
  `db.py`, `storage.py`, `market_data.py`).
- [reference-broker-formats.md](reference-broker-formats.md) — supported exports and
  the canonical parsed schema.
- [explanation-architecture.md](explanation-architecture.md) — why the backends and
  modules are arranged this way.
- [howto-add-a-broker.md](howto-add-a-broker.md) — add support for a new broker export.
