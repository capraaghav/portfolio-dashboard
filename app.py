"""
Portfolio Dashboard — Local-only, Indian Markets (NSE/BSE)
Run:  streamlit run app.py

Everything runs on your machine. The only outbound calls are to Yahoo Finance
for prices/fundamentals. No portfolio data is ever uploaded anywhere.
"""

from __future__ import annotations
import io
import os
import tempfile
import uuid
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

import analytics
import charts
import market_data as md
import parsers
import storage
from formatting import (
    fmt_inr, fmt_pct, fmt_num, fmt_int, fmt_mcap,
    REC_LABEL, SIGNAL_ORDER, GAIN, LOSS,
)
from parsers import parse_all

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Portfolio Dashboard", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.5rem; }
[data-testid="stMetricDelta"] { font-size: 0.95rem; }
.block-container { padding-top: 1.2rem; }
.stTabs [data-baseweb="tab-list"] { gap: 2px; flex-wrap: wrap; }
.stTabs [data-baseweb="tab"] { padding: 6px 12px; }
</style>
""", unsafe_allow_html=True)

# ─── Multi-user / hosting isolation ──────────────────────────────────────────
# When hosted for several people (set PORTFOLIO_MULTIUSER=1 as an env var or in
# Streamlit Cloud secrets), give each browser session its own private temp folder
# so no visitor can see another's saved holdings, snapshots, watchlist or overrides.
# Locally (default) it uses the persistent ./data folder as before.

def _is_multiuser() -> bool:
    if os.getenv("PORTFOLIO_MULTIUSER") == "1":
        return True
    try:
        return str(st.secrets.get("PORTFOLIO_MULTIUSER", "")).strip() == "1"
    except Exception:
        return False

MULTIUSER = _is_multiuser()
if MULTIUSER:
    if "_sid" not in st.session_state:
        st.session_state["_sid"] = uuid.uuid4().hex[:12]
    storage.configure(Path(tempfile.gettempdir()) / "portfolio_sessions" / st.session_state["_sid"])

# ─── Session state ────────────────────────────────────────────────────────────

if "overrides" not in st.session_state:
    st.session_state.overrides = storage.load_overrides()
if "watchlist" not in st.session_state:
    st.session_state.watchlist = storage.load_watchlist()


def _wk52_pct(ticker, prices_map, fund_map):
    f = fund_map.get(ticker) or {}
    low, high, price = f.get("wk52_low"), f.get("wk52_high"), prices_map.get(ticker)
    if all([low, high, price]) and high > low:
        return (price - low) / (high - low) * 100
    return np.nan


def to_excel_bytes(holdings_df: pd.DataFrame, totals: dict) -> bytes:
    buf = io.BytesIO()
    summary = pd.DataFrame([{
        "Total Value (₹)": totals.get("value"),
        "Total Cost (₹)": totals.get("cost"),
        "Total Gain/Loss (₹)": totals.get("pnl"),
        "Gain/Loss %": totals.get("pnl_pct"),
        "Holdings": totals.get("n_holdings"),
        "Exported": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    }])
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        holdings_df.drop(columns=[c for c in holdings_df.columns if c.startswith("_")],
                         errors="ignore").to_excel(writer, sheet_name="Holdings", index=False)
    return buf.getvalue()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Portfolio Dashboard")
    st.caption("Local-only · Indian Markets · NSE / BSE")
    st.divider()

    st.subheader("Upload Holdings")
    st.caption("CSV or Excel exports from any broker. Each file = one account.")
    uploaded = st.file_uploader("Drop files here", type=["csv", "xlsx", "xls", "pdf"],
                                accept_multiple_files=True, label_visibility="collapsed",
                                key="uploader")

    account_names: dict[str, str] = {}
    if uploaded:
        st.subheader("Account Labels")
        for f in uploaded:
            default = f.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
            account_names[f.name] = st.text_input(f"`{f.name}`", value=default, key=f"acct_{f.name}")

    # Offer to reload the last saved session if nothing is uploaded
    use_saved = False
    if not uploaded:
        meta_info = storage.session_meta()
        if meta_info:
            st.info(f"Last session: **{meta_info.get('rows', '?')} rows** "
                    f"saved {meta_info.get('saved_at', '')[:16].replace('T', ' ')}")
            use_saved = st.button("↩️ Load last session", width='stretch')

    st.divider()
    st.subheader("Filters")
    exclude_nonequity = st.toggle("Equity only (remove mutual funds & bonds)", value=False,
                                  help="Drops mutual funds and bonds/NCDs from the entire dashboard.")

    st.divider()
    st.subheader("Data options")
    load_meta = st.toggle("Sector, names, analyst targets & fundamentals", value=True,
                          help="One Yahoo Finance .info call per stock. Slower on first load, cached 1 hour.")
    load_ta = st.toggle("Technical analysis (SMA / RSI)", value=False,
                        help="Bulk-downloads price history. ~10s first load, cached 1 hour.")
    load_div = st.toggle("Dividend data", value=False,
                         help="Fetches dividend history per stock for the Dividends tab.")

    st.divider()
    if st.button("🔄 Refresh data (clear cache & retry)", width='stretch'):
        for fn in (md.fetch_quotes, md.fetch_metadata, md.fetch_ta_signals,
                   md.fetch_dividends, md.fetch_closes):
            fn.clear()
        st.rerun()
    st.caption("Use if prices, signals, or targets look stale or empty (Yahoo rate-limits large portfolios).")

    with st.expander("Supported formats"):
        st.markdown("""
| Broker | How to export |
|--------|--------------|
| **Zerodha Kite** | Holdings → ⋮ → Download |
| **Zerodha Console** | Portfolio → Holdings → Export |
| **HDFC Securities** | Portfolio → Holdings → Download |
| **Reliance / IndusInd** | Holdings → Download |
| **IIFL Portfolio+ (PDF)** | Portfolio report PDF |
| **Groww** | Stocks → ↓ Download Report |
| **Upstox** | Holdings → Export |
| **Angel One** | Holdings → Download |
| **Any broker** | CSV / Excel / **PDF** with Symbol/ISIN + Qty + Price |

Files that store a full **company name** or only an **ISIN** instead of a ticker
are auto-matched to NSE/BSE symbols (the file's own LTP disambiguates look-alikes;
unknown names fall back to the NSE official list, then a web search).
        """)
    if MULTIUSER:
        st.caption("🔒 Your upload is processed in a private session and is **not stored** after you "
                   "leave. Other visitors can't see your data.")
    else:
        st.caption("🔒 Runs entirely on your machine. No portfolio data leaves your computer.")

# ─── Acquire raw data (upload or saved session) ──────────────────────────────

raw: pd.DataFrame | None = None
if uploaded:
    raw, parse_errors = parse_all(uploaded, account_names)
    for fname, err in parse_errors:
        st.error(f"**`{fname}`** — {err}")
    if raw is not None:
        storage.save_session(raw)
elif use_saved:
    raw = storage.load_session()

if raw is None or raw.empty:
    st.markdown("## Welcome to your Portfolio Dashboard")
    st.markdown("""
Upload one or more brokerage CSV/Excel exports from the **sidebar** to begin.

**You'll get:** live valuation · gain/loss · allocation & sector charts · treemap
heatmap · technical signals · analyst price targets · LTCG/STCG tax view ·
risk metrics · dividends · per-stock drill-down · benchmark vs NIFTY · rebalancing.

**Privacy:** everything runs locally. Only price lookups hit Yahoo Finance.
    """)
    st.stop()

# ─── Resolve symbols (some brokers store the full company name or only an ISIN) ─

orig_syms = tuple(sorted(raw["ticker"].unique()))
asset_types, clean_map, need_search = {}, {}, {}
for t in orig_syms:
    asset_types[t] = parsers.classify_asset(t)
    if parsers.is_isin(t):                            # depository export → resolve ISIN
        clean_map[t] = t
        if asset_types[t] == "Equity":
            need_search[t] = t
    elif parsers.looks_like_symbol(t):               # already a clean ticker
        clean_map[t] = t
    else:                                            # full company name → resolve
        clean_map[t] = parsers.clean_company_name(t)
        if asset_types[t] == "Equity":
            need_search[t] = clean_map[t]

ltp_map = raw.groupby("ticker")["ltp"].first().to_dict() if "ltp" in raw.columns else {}

resolved: dict = {}
if need_search:
    with st.spinner(f"Resolving {len(need_search)} names/ISINs to NSE/BSE tickers…"):
        resolved = md.resolve_symbols(tuple(sorted(need_search)), need_search, ltp_map)

# Build final ticker rename + display-name + asset-type maps
rename, display, asset_of = {}, {}, {}
unresolved_equities = []
for t in orig_syms:
    is_clean = parsers.looks_like_symbol(t) and not parsers.is_isin(t)
    if is_clean:
        new = t
    elif asset_types[t] == "Equity" and resolved.get(t):
        new = resolved[t]
    elif asset_types[t] == "Equity":
        new = clean_map[t][:28] or t                 # unresolved equity → cleaned name / ISIN
        unresolved_equities.append(clean_map[t].title())
    else:
        # Mutual fund / bond — keep distinguishing detail (e.g. NCD series), don't merge
        new = str(t).replace("''", "").replace('"', "").strip()[:46]
    rename[t] = new
    asset_of[new] = asset_types[t]
    display[new] = t if is_clean else new.title()

raw = raw.copy()
raw["ticker"] = raw["ticker"].map(rename)

# Optional: drop mutual funds & bonds from the whole dashboard
n_excluded = 0
if exclude_nonequity:
    before = raw["ticker"].nunique()
    raw = raw[raw["ticker"].map(lambda t: asset_of.get(t, "Equity") == "Equity")].copy()
    n_excluded = before - raw["ticker"].nunique()

yahoo_eligible = {
    rename[t] for t in orig_syms
    if asset_types[t] == "Equity"
    and ((parsers.looks_like_symbol(t) and not parsers.is_isin(t)) or resolved.get(t))
}
name_resolved = bool(need_search)

# ─── Fetch market data ───────────────────────────────────────────────────────

tickers_tuple = tuple(sorted(raw["ticker"].unique()))
yahoo_eligible &= set(tickers_tuple)                     # prune anything filtered out
yahoo_tickers = tuple(sorted(yahoo_eligible))

with st.spinner(f"Fetching live prices for {len(yahoo_tickers)} stocks…"):
    quotes = md.fetch_quotes(yahoo_tickers)

prices = md.prices_from_quotes(quotes)
suffix_map = md.suffix_map_from_quotes(quotes)
# Apply any manual overrides (for tickers Yahoo can't price)
for t, p in st.session_state.overrides.items():
    if p:
        prices[t] = p

meta: dict = {"sectors": {}, "names": {}, "analyst": {}, "fundamentals": {}}
if load_meta:
    with st.spinner("Loading names, sectors, analyst targets & fundamentals…"):
        meta = md.fetch_metadata(yahoo_tickers, suffix_map)

ta_signals: dict = {}
if load_ta:
    with st.spinner("Downloading price history for technical analysis…"):
        ta_signals = md.fetch_ta_signals(yahoo_tickers, suffix_map)

dividends: dict = {}
if load_div:
    with st.spinner("Fetching dividend history…"):
        dividends = md.fetch_dividends(yahoo_tickers, suffix_map, prices)

# Fill names/sectors for everything (Yahoo where available; cleaned name / asset type otherwise)
meta.setdefault("names", {})
meta.setdefault("sectors", {})
for t in tickers_tuple:
    if not meta["names"].get(t):
        meta["names"][t] = display.get(t, t)
    if asset_of.get(t) in ("Mutual Fund", "Bond/NCD"):
        meta["sectors"][t] = asset_of[t]
    elif not meta["sectors"].get(t):
        meta["sectors"][t] = "Unknown"

analyst_data = meta.get("analyst", {})
fundamentals = meta.get("fundamentals", {})
has_targets = load_meta and any(v.get("target_mean") for v in analyst_data.values())

# ─── Build holdings + totals ─────────────────────────────────────────────────

holdings = analytics.build_holdings(raw, prices, meta)
totals = analytics.portfolio_totals(holdings)
n_accounts = raw["account"].nunique()

# Portfolio day change (from quotes × shares)
shares_map = dict(zip(holdings["Ticker"], holdings["Shares"]))
day_chg_total, prev_val_total = 0.0, 0.0
for t, q in quotes.items():
    if q.get("day_chg") is not None and q.get("prev_close"):
        sh = shares_map.get(t, 0) or 0
        day_chg_total += sh * q["day_chg"]
        prev_val_total += sh * q["prev_close"]
day_chg_pct = (day_chg_total / prev_val_total * 100) if prev_val_total > 0 else None

# Auto-save a daily snapshot (silently, once per day)
try:
    storage.auto_snapshot_if_new(totals, holdings)
except Exception:
    pass

# Genuine failures = Yahoo-eligible equities we still couldn't price (not MF/NCD/unresolved)
failed_tickers = [t for t in yahoo_tickers if prices.get(t) is None]
non_yahoo = [t for t in tickers_tuple if t not in yahoo_eligible]
has_cost_basis = "avg_cost" in raw.columns and raw["avg_cost"].notna().any()

# ─── Summary cards (always visible) ──────────────────────────────────────────

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Value", fmt_inr(totals["value"], short=True))
c2.metric("Total Gain/Loss",
          fmt_inr(totals["pnl"], short=True) if has_cost_basis else "—",
          fmt_pct(totals["pnl_pct"]) if has_cost_basis else None)
c3.metric("Today's Change",
          fmt_inr(day_chg_total, short=True) if day_chg_total else "—",
          fmt_pct(day_chg_pct) if day_chg_pct is not None else None)
c4.metric("Holdings", totals["n_holdings"])
c5.metric("Accounts", n_accounts)
c6.metric("Live prices", f"{len(yahoo_eligible) - len(failed_tickers)}/{len(tickers_tuple)}")

if not has_cost_basis:
    st.info("ℹ️ This file has **no cost basis** (it omits buy price), so Gain/Loss, tax, and XIRR can't be "
            "computed. Live value, allocation, technicals, analyst targets, and risk all still work. "
            "Upload a Console/tradebook export with average cost to unlock P&L.")

if n_excluded:
    st.caption(f"🧹 Equity-only filter is on — removed **{n_excluded}** mutual fund / bond holding(s) from the dashboard.")

if name_resolved:
    n_matched = sum(1 for v in resolved.values() if v)
    msg = f"🔎 Auto-matched **{n_matched}** company name(s)/ISIN(s) to NSE/BSE tickers via Yahoo search."
    if unresolved_equities:
        msg += (f" **{len(unresolved_equities)}** couldn't be matched (likely newly-listed, suspended, or "
                "demerged) — shown with their CSV value but no live analysis.")
    st.info(msg)

if non_yahoo and (asset_breakdown := {a: sum(1 for t in non_yahoo if asset_of.get(t) == a)
                                      for a in ("Mutual Fund", "Bond/NCD")}):
    bits = [f"{n} {a.lower()}" for a, n in asset_breakdown.items() if n]
    if bits:
        st.caption(f"Non-equity instruments valued from the CSV: {', '.join(bits)}.")

if failed_tickers:
    with st.expander(f"⚠️ {len(failed_tickers)} ticker(s) not priced by Yahoo — set a manual price in Holdings"):
        st.write(", ".join(failed_tickers))

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_names = ["📊 Overview", "📋 Holdings", "📈 Performance", "🔬 Technical", "🎯 Analysts",
             "🧮 Tax", "⚠️ Risk", "💰 Dividends", "🔍 Stock Detail", "👁️ Watchlist", "⚖️ Rebalance"]
tabs = st.tabs(tab_names)

# Shared filtered view (account filter lives in Holdings, but Overview shows all)
chart_data = holdings.dropna(subset=["Current Value (₹)"])
chart_data = chart_data[chart_data["Current Value (₹)"] > 0]


# ═══ OVERVIEW ═════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Portfolio Heatmap")
    st.caption("Box size = position value · colour = gain/loss %. Grouped by sector.")
    fig = charts.treemap(holdings)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No priced holdings to display yet.")

    st.divider()
    st.subheader("Allocation")
    a1, a2 = st.columns(2)
    with a1:
        f = charts.pie_by_stock(chart_data)
        if f:
            st.plotly_chart(f, use_container_width=True)
    with a2:
        if load_meta:
            f = charts.pie_by_sector(chart_data)
            if f:
                st.plotly_chart(f, use_container_width=True)
        else:
            st.info("Enable **Sector & fundamentals** in the sidebar for the sector chart.")

    if n_accounts > 1:
        st.divider()
        st.subheader("Per-Account Breakdown")
        acct_rows, bar_rows = [], []
        for acct, grp in raw.groupby("account"):
            ah = analytics.build_holdings(grp, prices, meta)
            at = analytics.portfolio_totals(ah)
            acct_rows.append({
                "Account": acct, "Holdings": len(ah),
                "Current Value": fmt_inr(at["value"], short=True),
                "Cost Basis": fmt_inr(at["cost"], short=True),
                "Gain/Loss": fmt_inr(at["pnl"], short=True),
                "Gain/Loss %": fmt_pct(at["pnl_pct"]),
                "% of Portfolio": f"{at['value']/totals['value']*100:.1f}%" if totals["value"] > 0 else "—",
            })
            for _, r in ah.nlargest(8, "Current Value (₹)").iterrows():
                bar_rows.append({"Account": acct, "Ticker": r["Ticker"], "Value": r["Current Value (₹)"]})
        st.dataframe(pd.DataFrame(acct_rows), width='stretch', hide_index=True)
        f = charts.account_stacked(pd.DataFrame(bar_rows))
        if f:
            st.plotly_chart(f, use_container_width=True)


# ═══ HOLDINGS ═════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Holdings")

    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        all_accounts = sorted(raw["account"].unique())
        sel_accounts = st.multiselect("Filter by account", all_accounts, default=all_accounts)
    with fc2:
        search = st.text_input("Search ticker / company", placeholder="e.g. RELIANCE")
    with fc3:
        ta_opts = ["Trend", "RSI"] if ta_signals else []
        tgt_opts = ["Upside (%)"] if has_targets else []
        sort_col = st.selectbox("Sort by", ["Current Value (₹)", "Gain/Loss (₹)", "Gain/Loss (%)",
                                            "Shares", "Live Price (₹)", "Ticker"] + ta_opts + tgt_opts)

    show_fund = st.checkbox("Show fundamentals (P/E, P/B, Mkt Cap, Beta, 52w)", value=False) if load_meta else False

    fr = raw[raw["account"].isin(sel_accounts)] if sel_accounts else raw
    fh = analytics.build_holdings(fr, prices, meta)

    if ta_signals:
        fh["Trend"] = fh["Ticker"].map(lambda t: ta_signals.get(t, {}).get("label", "—"))
        fh["RSI"] = fh["Ticker"].map(lambda t: ta_signals.get(t, {}).get("rsi", np.nan))
        fh["vs 50MA"] = fh["Ticker"].map(lambda t: ta_signals.get(t, {}).get("vs_50ma", None))
        fh["_sig"] = fh["Ticker"].map(lambda t: SIGNAL_ORDER.index(ta_signals.get(t, {}).get("signal", "N/A")))
    if has_targets:
        fh["Target (₹)"] = fh["Ticker"].map(lambda t: analyst_data.get(t, {}).get("target_mean"))
        fh["Upside (%)"] = fh.apply(lambda r: (analyst_data.get(r["Ticker"], {}).get("target_mean") / r["Live Price (₹)"] - 1) * 100
                                    if (analyst_data.get(r["Ticker"], {}).get("target_mean") and r["Live Price (₹)"]) else np.nan, axis=1)
        fh["Consensus"] = fh["Ticker"].map(lambda t: REC_LABEL.get(analyst_data.get(t, {}).get("rec_key", ""), "—"))
    if show_fund:
        fh["P/E"] = fh["Ticker"].map(lambda t: (fundamentals.get(t) or {}).get("pe"))
        fh["P/B"] = fh["Ticker"].map(lambda t: (fundamentals.get(t) or {}).get("pb"))
        fh["Mkt Cap"] = fh["Ticker"].map(lambda t: (fundamentals.get(t) or {}).get("market_cap"))
        fh["Beta"] = fh["Ticker"].map(lambda t: (fundamentals.get(t) or {}).get("beta"))
        fh["52w %"] = fh["Ticker"].map(lambda t: _wk52_pct(t, prices, fundamentals))
    if non_yahoo:  # mixed portfolio — show asset type + which rows are live
        fh["Type"] = fh["Ticker"].map(lambda t: asset_of.get(t, "Equity"))
        fh["Data"] = fh["Ticker"].map(lambda t: "Live" if (t in yahoo_eligible and prices.get(t) is not None) else "CSV")

    if search:
        s = search.strip().upper()
        fh = fh[fh["Ticker"].str.contains(s) | fh["Company"].str.upper().str.contains(s)]

    if sort_col == "Trend" and "_sig" in fh.columns:
        fh = fh.sort_values("_sig", na_position="last")
    else:
        fh = fh.sort_values(sort_col, ascending=(sort_col == "Ticker"), na_position="last")

    disp = fh.drop(columns=[c for c in fh.columns if c.startswith("_")], errors="ignore").copy()
    for col in ["Avg Cost (₹)", "Live Price (₹)", "Current Value (₹)", "Cost Basis (₹)", "Gain/Loss (₹)"]:
        disp[col] = disp[col].apply(fmt_inr)
    disp["Gain/Loss (%)"] = disp["Gain/Loss (%)"].apply(fmt_pct)
    disp["Shares"] = disp["Shares"].apply(lambda x: f"{x:,.2f}" if not pd.isna(x) else "—")
    if "RSI" in disp.columns:
        disp["RSI"] = disp["RSI"].apply(lambda x: f"{x:.0f}" if not pd.isna(x) else "—")
    if "vs 50MA" in disp.columns:
        disp["vs 50MA"] = disp["vs 50MA"].apply(lambda x: x if (x and str(x) != "None") else "—")
    if "Trend" in disp.columns:
        disp["Trend"] = disp["Trend"].replace({"— N/A": "—"})
    if "Target (₹)" in disp.columns:
        disp["Target (₹)"] = disp["Target (₹)"].apply(fmt_inr)
        disp["Upside (%)"] = disp["Upside (%)"].apply(fmt_pct)
    if show_fund:
        disp["P/E"] = disp["P/E"].apply(lambda x: fmt_num(x, 1))
        disp["P/B"] = disp["P/B"].apply(lambda x: fmt_num(x, 1))
        disp["Mkt Cap"] = disp["Mkt Cap"].apply(fmt_mcap)
        disp["Beta"] = disp["Beta"].apply(lambda x: fmt_num(x, 2))
        disp["52w %"] = disp["52w %"].apply(lambda x: f"{x:.0f}%" if not pd.isna(x) else "—")

    event = st.dataframe(disp, width='stretch', hide_index=True,
                         height=min(45 + 36 * len(disp), 600),
                         on_select="rerun", selection_mode="single-row",
                         key="holdings_table")
    st.caption(f"Showing {len(disp)} of {len(holdings)} holdings.  "
               "💡 Click a row to see its per-account split.")

    # ── Per-account breakdown for the selected stock (when held in 2+ accounts) ──
    sel = list(event.selection.rows) if (event and event.selection) else []
    if sel and sel[0] < len(fh):
        srow = fh.iloc[sel[0]]
        t, company = srow["Ticker"], srow["Company"]
        sub = fr[fr["ticker"] == t]
        accts = sorted(sub["account"].unique())
        st.markdown(f"#### Per-account split — {t} · {company}")
        if len(accts) <= 1:
            st.caption(f"Held only in **{accts[0] if accts else '—'}** — no multi-account split.")
        else:
            bd = analytics.per_account_breakdown(sub, prices, meta)
            tot_sh = bd["Shares"].sum()
            tot_cost = bd["Cost Basis (₹)"].sum()
            tot_val = bd["Current Value (₹)"].sum()
            tot_pnl = bd["Gain/Loss (₹)"].sum()
            total = {
                "Account": "TOTAL", "Shares": tot_sh,
                "Avg Cost (₹)": (tot_cost / tot_sh) if tot_sh else np.nan,
                "Live Price (₹)": srow["Live Price (₹)"],
                "Current Value (₹)": tot_val, "Cost Basis (₹)": tot_cost,
                "Gain/Loss (₹)": tot_pnl,
                "Gain/Loss (%)": (tot_pnl / tot_cost * 100) if tot_cost > 0 else np.nan,
            }
            bd = pd.concat([bd, pd.DataFrame([total])], ignore_index=True)
            bdisp = bd.copy()
            for col in ["Avg Cost (₹)", "Live Price (₹)", "Current Value (₹)", "Cost Basis (₹)", "Gain/Loss (₹)"]:
                bdisp[col] = bdisp[col].apply(fmt_inr)
            bdisp["Gain/Loss (%)"] = bdisp["Gain/Loss (%)"].apply(fmt_pct)
            bdisp["Shares"] = bdisp["Shares"].apply(lambda x: f"{x:,.2f}" if not pd.isna(x) else "—")
            st.dataframe(bdisp, width='stretch', hide_index=True)

    ec1, ec2 = st.columns([1, 4])
    with ec1:
        st.download_button("⬇️ Export to Excel", to_excel_bytes(fh, totals),
                           file_name=f"portfolio_{pd.Timestamp.now():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           width='stretch')

    # Manual price overrides for un-priced tickers
    if failed_tickers:
        with st.expander(f"✏️ Set manual prices for {len(failed_tickers)} un-priced ticker(s)"):
            edit_df = pd.DataFrame({
                "Ticker": failed_tickers,
                "Your Price (₹)": [st.session_state.overrides.get(t, 0.0) for t in failed_tickers],
            })
            edited = st.data_editor(edit_df, hide_index=True, width='stretch',
                                    disabled=["Ticker"], key="override_editor")
            if st.button("Save manual prices"):
                for _, r in edited.iterrows():
                    if r["Your Price (₹)"] and r["Your Price (₹)"] > 0:
                        st.session_state.overrides[r["Ticker"]] = float(r["Your Price (₹)"])
                storage.save_overrides(st.session_state.overrides)
                st.success("Saved. Refreshing…")
                st.rerun()


# ═══ PERFORMANCE ══════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Performance Over Time")

    snap_df = storage.snapshots_df()
    sc1, sc2 = st.columns([3, 1])
    with sc2:
        if st.button("📸 Save snapshot now", width='stretch'):
            storage.save_snapshot(totals, holdings)
            st.success("Snapshot saved!")
            st.rerun()
        st.caption(f"{len(snap_df)} snapshot(s) saved.")

    if len(snap_df) >= 2:
        f = charts.snapshot_line(snap_df)
        if f:
            st.plotly_chart(f, use_container_width=True)
        first, last = snap_df.iloc[0], snap_df.iloc[-1]
        days = (last["date"] - first["date"]).days or 1
        if first["Total Value"] and last["Total Value"]:
            chg = last["Total Value"] / first["Total Value"] - 1
            ann = (1 + chg) ** (365 / days) - 1
            m1, m2, m3 = st.columns(3)
            m1.metric("Tracked period", f"{days} days")
            m2.metric("Value change", fmt_pct(chg * 100))
            m3.metric("Annualised (from snapshots)", fmt_pct(ann * 100))
    else:
        st.info("**A snapshot is auto-saved once per day.** Come back over time, or click "
                "**Save snapshot now** — once you have 2+ snapshots, your value timeline appears here. "
                "Snapshots are stored locally in `data/snapshots.json`.")

    st.divider()
    st.subheader("Annualised Return (XIRR)")
    xirr = analytics.portfolio_xirr(raw, holdings)
    if xirr is not None:
        st.metric("Portfolio XIRR", fmt_pct(xirr * 100),
                  help="Money-weighted annualised return using your purchase dates.")
    else:
        st.info("XIRR needs **purchase dates**, which the holdings export doesn't include. "
                "Upload your broker **tradebook** (Zerodha Console → Reports → Tradebook) — it has trade "
                "dates — and XIRR will compute automatically. Meanwhile the snapshot timeline above gives "
                "time-weighted return over the tracked period.")

    st.divider()
    st.subheader("Benchmark — Current Basket vs Index")
    st.caption("Backtests *today's* share quantities over the period (ignores when you actually bought). "
               "A fair 'has my basket beaten the index?' check.")
    bc1, bc2, bc3 = st.columns([2, 2, 2])
    with bc1:
        bench_name = st.selectbox("Benchmark", list(md.BENCHMARKS.keys()))
    with bc2:
        period = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=1)
    with bc3:
        st.write("")
        run_bt = st.button("▶️ Run backtest", width='stretch')

    if run_bt:
        with st.spinner("Downloading history for your basket + benchmark…"):
            closes = md.fetch_closes(tickers_tuple, suffix_map, period)
            port_curve = analytics.synthetic_curve(closes, shares_map)
            bench_series = md.fetch_benchmark(md.BENCHMARKS[bench_name], period)
        if port_curve.empty:
            st.warning("Couldn't build the portfolio curve (no history returned).")
        else:
            pn = analytics.normalize_to_100(port_curve)
            bn = analytics.normalize_to_100(bench_series)
            f = charts.benchmark_overlay(pn, bn, bench_name)
            if f:
                st.plotly_chart(f, use_container_width=True)
            p_ret = pn.iloc[-1] - 100 if not pn.empty else np.nan
            b_ret = bn.iloc[-1] - 100 if not bn.empty else np.nan
            r1, r2, r3 = st.columns(3)
            r1.metric(f"Your basket ({period})", fmt_pct(p_ret))
            r2.metric(f"{bench_name} ({period})", fmt_pct(b_ret))
            r3.metric("Alpha (out/under-performance)", fmt_pct(p_ret - b_ret),
                      delta=fmt_pct(p_ret - b_ret))


# ═══ TECHNICAL ════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Technical Analysis")
    if not load_ta:
        st.info("Enable **Technical analysis** in the sidebar to load SMA/RSI signals.")
    elif not ta_signals:
        st.info("No technical data loaded yet.")
    else:
        real = sum(1 for v in ta_signals.values() if v.get("signal") != "N/A")
        if real == 0:
            st.warning("⚠️ No signals came back — Yahoo Finance likely rate-limited the history download. "
                       "Click **🔄 Refresh data** in the sidebar to retry (it bulk-downloads in one request).")
        st.caption("Price vs SMA50 sets Bullish/Bearish. Strong = SMA50 also above/below SMA200 "
                   "(golden/death cross). RSI 14: >70 overbought, <30 oversold.")
        counts = {s: 0 for s in SIGNAL_ORDER}
        for t in ta_signals:
            counts[ta_signals[t].get("signal", "N/A")] = counts.get(ta_signals[t].get("signal", "N/A"), 0) + 1
        cc = st.columns(5)
        for col, key, lbl in zip(cc, ["Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish"],
                                 ["↑↑ Strong Bull", "↑ Bullish", "→ Neutral", "↓ Bearish", "↓↓ Strong Bear"]):
            col.metric(lbl, counts.get(key, 0))
        t1, t2 = st.columns([3, 2])
        with t1:
            f = charts.vs_50ma_bar(ta_signals)
            if f:
                st.plotly_chart(f, use_container_width=True)
        with t2:
            f = charts.rsi_bar(ta_signals)
            if f:
                st.plotly_chart(f, use_container_width=True)


# ═══ ANALYSTS ═════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("Analyst Price Targets")
    if not load_meta:
        st.info("Enable **Analyst targets & fundamentals** in the sidebar.")
    elif not has_targets:
        any_named = any(meta.get("names", {}).get(t) and meta["names"][t] != t for t in yahoo_tickers)
        if yahoo_tickers and not any_named:
            st.warning("⚠️ No company data came back — Yahoo Finance likely rate-limited the requests. "
                       "Click **🔄 Refresh data** in the sidebar to retry.")
        else:
            st.info("No analyst targets found. Large/mid-cap NSE stocks usually have coverage; small-caps often don't.")
    else:
        st.caption("**Source:** Yahoo Finance consensus (aggregates institutional brokers — Goldman Sachs, "
                   "Morgan Stanley, Motilal Oswal, ICICI Securities, Kotak, etc.). Targets are **12-month** "
                   "projections — the closest free proxy to a 6-month view.")
        rows = []
        for _, r in holdings.iterrows():
            a = analyst_data.get(r["Ticker"], {})
            if a.get("target_mean") is None:
                continue
            live = r["Live Price (₹)"]
            rows.append({"Ticker": r["Ticker"], "Company": r["Company"], "Live (₹)": live,
                         "Target Low": a.get("target_low"), "Target Mean": a.get("target_mean"),
                         "Target High": a.get("target_high"),
                         "Upside (%)": (a["target_mean"] / live - 1) * 100 if live else np.nan,
                         "Consensus": REC_LABEL.get(a.get("rec_key", ""), "—"),
                         "# Analysts": a.get("n_analysts")})
        if not rows:
            st.info("No analyst targets for the current holdings.")
        else:
            tgt_df = pd.DataFrame(rows).sort_values("Upside (%)", ascending=False)
            rng_rows = []
            for _, r in tgt_df.iterrows():
                live = r["Live (₹)"]
                if not live:
                    continue
                rng_rows.append({"Ticker": r["Ticker"],
                                 "Low %": (r["Target Low"] / live - 1) * 100 if r["Target Low"] else np.nan,
                                 "Mean %": r["Upside (%)"],
                                 "High %": (r["Target High"] / live - 1) * 100 if r["Target High"] else np.nan,
                                 "Consensus": r["Consensus"]})
            f = charts.analyst_range(pd.DataFrame(rng_rows))
            if f:
                st.plotly_chart(f, use_container_width=True)
            with st.expander("Full analyst target table"):
                td = tgt_df.copy()
                for col in ["Live (₹)", "Target Low", "Target Mean", "Target High"]:
                    td[col] = td[col].apply(fmt_inr)
                td["Upside (%)"] = td["Upside (%)"].apply(fmt_pct)
                td["# Analysts"] = td["# Analysts"].apply(lambda x: str(int(x)) if x and not pd.isna(x) else "—")
                st.dataframe(td, width='stretch', hide_index=True)
            st.caption(f"Analyst coverage: **{len(rows)}/{len(holdings)}** holdings.")


# ═══ TAX ══════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Capital Gains Tax (if sold today)")
    st.caption("⚠️ **Estimate only — not tax advice.** Indian listed-equity rates (post-Jul 2024): "
               "LTCG 12.5% above ₹1.25 L/yr exemption · STCG 20%. Long-term = held >12 months. "
               "Verify with your CA / current law.")
    tax = analytics.tax_breakdown(raw, prices, meta)
    if not tax:
        st.info("Not enough data to compute the tax split.")
    elif tax["all_unknown"]:
        st.warning("Your file has no **Quantity Long Term** column or **purchase dates**, so long-term vs "
                   "short-term can't be determined. Use a **Zerodha Console** export (it has the long-term "
                   "column) for the LTCG/STCG split. Total unrealised gain shown below.")
        st.metric("Total unrealised gain", fmt_inr(tax["unknown_gain"], short=True))
    else:
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Long-term gain", fmt_inr(tax["lt_gain"], short=True),
                  help="Unrealised gain on shares held >12 months.")
        x2.metric("Short-term gain", fmt_inr(tax["st_gain"], short=True),
                  help="Unrealised gain on shares held <12 months.")
        x3.metric("Est. LTCG tax", fmt_inr(tax["ltcg_tax"], short=True),
                  help=f"12.5% on long-term gains above ₹1.25 L. Exemption used: {fmt_inr(tax['ltcg_exemption_used'])}.")
        x4.metric("Est. STCG tax", fmt_inr(tax["stcg_tax"], short=True), help="20% on short-term gains.")
        st.metric("**Total estimated tax if you sold everything today**", fmt_inr(tax["total_tax"], short=True))
        if tax["unknown_gain"]:
            st.caption(f"Plus {fmt_inr(tax['unknown_gain'], short=True)} of gain with undetermined holding term (excluded above).")

    st.divider()
    st.subheader("Tax-Loss Harvesting Candidates")
    st.caption("Positions at an unrealised loss. Booking losses can offset taxable gains "
               "(STCL offsets STCG/LTCG; LTCL offsets LTCG). Mind the 30-day wash-sale-style repurchase considerations.")
    losers = analytics.harvest_candidates(holdings)
    if losers.empty:
        st.success("No positions currently at a loss. 🎉")
    else:
        ld = losers.copy()
        for col in ["Avg Cost (₹)", "Live Price (₹)", "Current Value (₹)", "Gain/Loss (₹)"]:
            ld[col] = ld[col].apply(fmt_inr)
        ld["Gain/Loss (%)"] = ld["Gain/Loss (%)"].apply(fmt_pct)
        ld["Shares"] = ld["Shares"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(ld, width='stretch', hide_index=True)
        total_loss = losers["Gain/Loss (₹)"].sum()
        st.metric("Total harvestable loss", fmt_inr(total_loss, short=True))


# ═══ RISK ═════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("Risk & Concentration")
    rm = analytics.risk_metrics(holdings, fundamentals if load_meta else None)
    if not rm:
        st.info("No priced holdings to analyse.")
    else:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Largest position", f"{rm['top1_pct']:.1f}%", help=f"{rm['top1_ticker']}")
        r2.metric("Top-5 weight", f"{rm['top5_pct']:.1f}%")
        r3.metric("Effective # holdings", f"{rm['effective_n']:.1f}",
                  help="1/HHI — diversification-adjusted count. Lower than actual count means concentration.")
        r4.metric("Portfolio beta", fmt_num(rm["portfolio_beta"], 2) if not pd.isna(rm.get("portfolio_beta", np.nan)) else "—",
                  help="Value-weighted beta vs market. >1 = more volatile than the index.")

        # Concentration warnings
        warns = []
        if rm["top1_pct"] > 15:
            warns.append(f"**{rm['top1_ticker']}** is {rm['top1_pct']:.0f}% of your portfolio — high single-stock concentration.")
        if rm["top_sector_pct"] > 35:
            warns.append(f"**{rm['top_sector']}** sector is {rm['top_sector_pct']:.0f}% of your portfolio — high sector concentration.")
        if rm["effective_n"] < 8:
            warns.append(f"Effective holdings ≈ {rm['effective_n']:.0f}: despite {rm['n_positions']} stocks, value is concentrated in a few.")
        for w in warns:
            st.warning(w)
        if not warns:
            st.success("No major concentration flags. Portfolio looks reasonably diversified.")

        st.divider()
        if load_meta:
            st.markdown("**Sector concentration**")
            sec = (holdings.dropna(subset=["Current Value (₹)"]).groupby("Sector")["Current Value (₹)"]
                   .sum().sort_values(ascending=False).reset_index())
            sec["% of Portfolio"] = sec["Current Value (₹)"] / totals["value"] * 100
            import plotly.express as px
            figs = px.bar(sec, x="% of Portfolio", y="Sector", orientation="h",
                          color="% of Portfolio", color_continuous_scale="Blues",
                          height=max(300, len(sec) * 28))
            figs.update_layout(margin=dict(t=20, b=20, l=10, r=10), yaxis=dict(autorange="reversed"),
                               coloraxis_showscale=False)
            st.plotly_chart(figs, use_container_width=True)


# ═══ DIVIDENDS ════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("Dividend Income")
    if not load_div:
        st.info("Enable **Dividend data** in the sidebar to load dividend history.")
    elif not dividends:
        st.info("No dividend data loaded.")
    else:
        rows = []
        for _, r in holdings.iterrows():
            d = dividends.get(r["Ticker"], {})
            ttm = d.get("ttm") or 0
            if ttm <= 0:
                continue
            shares = r["Shares"]
            rows.append({"Ticker": r["Ticker"], "Company": r["Company"],
                         "Div/Share (TTM)": ttm, "Shares": shares,
                         "Annual Income (₹)": ttm * shares,
                         "Yield on Price": d.get("yield_pct"),
                         "Last Paid": d.get("last_date")})
        if not rows:
            st.info("None of your holdings paid dividends in the last 12 months (per Yahoo Finance).")
        else:
            dd = pd.DataFrame(rows).sort_values("Annual Income (₹)", ascending=False)
            total_income = dd["Annual Income (₹)"].sum()
            port_yield = (total_income / totals["value"] * 100) if totals["value"] > 0 else np.nan
            d1, d2, d3 = st.columns(3)
            d1.metric("Est. annual dividend income", fmt_inr(total_income, short=True))
            d2.metric("Portfolio dividend yield", fmt_pct(port_yield) if not pd.isna(port_yield) else "—")
            d3.metric("Dividend-paying holdings", len(dd))

            import plotly.express as px
            fig_div = px.bar(dd.head(20), x="Annual Income (₹)", y="Ticker", orientation="h",
                             title="Annual dividend income by stock (top 20)", color_discrete_sequence=[GAIN],
                             height=max(300, len(dd.head(20)) * 24))
            fig_div.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, b=20, l=10, r=10))
            st.plotly_chart(fig_div, use_container_width=True)

            ddd = dd.copy()
            ddd["Div/Share (TTM)"] = ddd["Div/Share (TTM)"].apply(fmt_inr)
            ddd["Annual Income (₹)"] = ddd["Annual Income (₹)"].apply(fmt_inr)
            ddd["Yield on Price"] = ddd["Yield on Price"].apply(lambda x: f"{x:.2f}%" if x else "—")
            ddd["Shares"] = ddd["Shares"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(ddd, width='stretch', hide_index=True)


# ═══ STOCK DETAIL ═════════════════════════════════════════════════════════════
with tabs[8]:
    st.subheader("Stock Detail")
    # Only stocks with live Yahoo data have charts/news/fundamentals
    detail_options = [t for t in holdings["Ticker"].tolist() if t in yahoo_eligible]
    if not detail_options:
        st.info("No live-priced equities to show detail for (mutual funds, bonds, and unresolved "
                "tickers don't have Yahoo market data).")
        pick = None
    else:
        pick = st.selectbox("Select a holding", detail_options)
    if pick:
        row = holdings[holdings["Ticker"] == pick].iloc[0]
        suffix = suffix_map.get(pick, ".NS")
        a = analyst_data.get(pick, {})
        fnd = fundamentals.get(pick, {})

        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Live Price", fmt_inr(row["Live Price (₹)"]))
        h2.metric("Your Avg Cost", fmt_inr(row["Avg Cost (₹)"]))
        h3.metric("Current Value", fmt_inr(row["Current Value (₹)"], short=True))
        h4.metric("Gain/Loss", fmt_inr(row["Gain/Loss (₹)"], short=True), fmt_pct(row["Gain/Loss (%)"]))

        with st.spinner(f"Loading {pick} chart…"):
            hist = md.fetch_history_single(pick, suffix, period="1y")
        f = charts.candlestick(hist, pick, row["Avg Cost (₹)"])
        if f:
            st.plotly_chart(f, use_container_width=True)
        else:
            st.info("No price history available for this ticker.")

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if fnd.get("wk52_low") and fnd.get("wk52_high"):
                fg = charts.wk52_gauge(row["Live Price (₹)"], fnd["wk52_low"], fnd["wk52_high"])
                if fg:
                    st.plotly_chart(fg, use_container_width=True)
            if load_div:
                dv = dividends.get(pick, {})
                if dv.get("history") is not None:
                    fd = charts.dividend_history(dv["history"])
                    if fd:
                        st.plotly_chart(fd, use_container_width=True)
        with dcol2:
            st.markdown("**Fundamentals**")
            st.markdown(f"""
| Metric | Value |
|---|---|
| Sector | {row['Sector']} |
| Industry | {fnd.get('industry') or '—'} |
| Market Cap | {fmt_mcap(fnd.get('market_cap'))} |
| P/E (trailing) | {fmt_num(fnd.get('pe'), 1)} |
| P/E (forward) | {fmt_num(fnd.get('forward_pe'), 1)} |
| P/B | {fmt_num(fnd.get('pb'), 1)} |
| Beta | {fmt_num(fnd.get('beta'), 2)} |
| ROE | {fmt_pct(fnd['roe']*100) if fnd.get('roe') is not None else '—'} |
| 52-wk High | {fmt_inr(fnd.get('wk52_high'))} |
| 52-wk Low | {fmt_inr(fnd.get('wk52_low'))} |
""")
            if a.get("target_mean"):
                st.markdown("**Analyst Consensus**")
                st.markdown(f"""
| Metric | Value |
|---|---|
| Consensus | {REC_LABEL.get(a.get('rec_key',''), '—')} |
| Target (mean) | {fmt_inr(a.get('target_mean'))} |
| Target range | {fmt_inr(a.get('target_low'))} – {fmt_inr(a.get('target_high'))} |
| Upside to mean | {fmt_pct((a['target_mean']/row['Live Price (₹)']-1)*100) if row['Live Price (₹)'] else '—'} |
| # Analysts | {int(a['n_analysts']) if a.get('n_analysts') else '—'} |
""")

        st.markdown("**Recent News**")
        with st.spinner("Loading news…"):
            news = md.fetch_news_single(pick, suffix)
        if news:
            for item in news:
                pub = f" · *{item['publisher']}*" if item.get("publisher") else ""
                if item.get("link"):
                    st.markdown(f"- [{item['title']}]({item['link']}){pub}")
                else:
                    st.markdown(f"- {item['title']}{pub}")
        else:
            st.caption("No recent news found for this ticker.")


# ═══ WATCHLIST ════════════════════════════════════════════════════════════════
with tabs[9]:
    st.subheader("Watchlist")
    st.caption("Track stocks you don't own yet. Saved locally in `data/watchlist.json`.")
    wc1, wc2 = st.columns([3, 1])
    with wc1:
        new_w = st.text_input("Add tickers (comma or space separated)", placeholder="TATAMOTORS, INFY, HDFCBANK")
    with wc2:
        st.write("")
        if st.button("➕ Add", width='stretch') and new_w:
            for t in new_w.replace(",", " ").split():
                tt = t.strip().upper()
                if tt and tt not in st.session_state.watchlist:
                    st.session_state.watchlist.append(tt)
            storage.save_watchlist(st.session_state.watchlist)
            st.rerun()

    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Add a few tickers above.")
    else:
        wl = tuple(sorted(st.session_state.watchlist))
        with st.spinner("Fetching watchlist quotes…"):
            wquotes = md.fetch_quotes(wl)
            wsuffix = md.suffix_map_from_quotes(wquotes)
            wmeta = md.fetch_metadata(wl, wsuffix) if load_meta else {"analyst": {}, "names": {}}
        wrows = []
        for t in wl:
            q = wquotes.get(t, {})
            a = wmeta.get("analyst", {}).get(t, {})
            price = q.get("price")
            tgt = a.get("target_mean")
            wrows.append({"Ticker": t, "Company": wmeta.get("names", {}).get(t, t),
                          "Price (₹)": fmt_inr(price), "Day %": fmt_pct(q.get("day_chg_pct")) if q.get("day_chg_pct") is not None else "—",
                          "Target (₹)": fmt_inr(tgt), "Upside": fmt_pct((tgt/price-1)*100) if (tgt and price) else "—",
                          "Consensus": REC_LABEL.get(a.get("rec_key", ""), "—")})
        st.dataframe(pd.DataFrame(wrows), width='stretch', hide_index=True)
        rm_t = st.selectbox("Remove ticker", ["—"] + list(wl))
        if rm_t != "—" and st.button("Remove"):
            st.session_state.watchlist.remove(rm_t)
            storage.save_watchlist(st.session_state.watchlist)
            st.rerun()


# ═══ REBALANCE ════════════════════════════════════════════════════════════════
with tabs[10]:
    st.subheader("Rebalancing")
    st.caption("Set target weights for your holdings; see the drift and the ₹ to buy/sell to hit them. "
               "Defaults to your current weights — edit the **Target %** column.")
    rb = holdings.dropna(subset=["Current Value (₹)"]).copy()
    rb = rb[rb["Current Value (₹)"] > 0]
    if rb.empty:
        st.info("No priced holdings to rebalance.")
    else:
        rb["Current %"] = rb["Current Value (₹)"] / totals["value"] * 100
        editor_df = rb[["Ticker", "Current %"]].copy()
        editor_df["Target %"] = editor_df["Current %"].round(2)
        edited = st.data_editor(editor_df, hide_index=True, width='stretch',
                                disabled=["Ticker", "Current %"], key="rebal_editor",
                                column_config={"Current %": st.column_config.NumberColumn(format="%.2f%%"),
                                               "Target %": st.column_config.NumberColumn(format="%.2f%%")})
        tgt_total = edited["Target %"].sum()
        st.caption(f"Target weights sum to **{tgt_total:.1f}%** (should be ~100%).")
        targets = dict(zip(edited["Ticker"], edited["Target %"]))
        plan = analytics.rebalance_plan(rb, targets)
        plan = plan[plan["Action (₹)"].abs() > 1].sort_values("Action (₹)")
        if plan.empty:
            st.success("Already at target — nothing to trade.")
        else:
            pd_disp = plan.copy()
            pd_disp["Action"] = pd_disp["Action (₹)"].apply(lambda x: ("🟢 Buy " if x > 0 else "🔴 Sell ") + fmt_inr(abs(x), short=True))
            pd_disp["Current %"] = pd_disp["Current %"].apply(lambda x: f"{x:.2f}%")
            pd_disp["Target %"] = pd_disp["Target %"].apply(lambda x: f"{x:.2f}%")
            pd_disp["Drift %"] = pd_disp["Drift %"].apply(lambda x: f"{x:+.2f}%")
            pd_disp["Current Value (₹)"] = pd_disp["Current Value (₹)"].apply(fmt_inr)
            pd_disp["Target Value (₹)"] = pd_disp["Target Value (₹)"].apply(fmt_inr)
            st.dataframe(pd_disp[["Ticker", "Current %", "Target %", "Drift %",
                                  "Current Value (₹)", "Target Value (₹)", "Action"]],
                         width='stretch', hide_index=True)
            st.caption("⚠️ Suggestions only — not investment advice. Review before trading; the app never places orders.")


st.caption("Portfolio Dashboard · runs entirely on your local machine · only price lookups use Yahoo Finance")
