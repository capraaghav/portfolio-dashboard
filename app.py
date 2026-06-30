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
import db
import earnings
import intelligence
import market_data as md
import parsers
import screener as scr
import storage
from click_spark import click_spark
from formatting import (
    fmt_inr, fmt_pct, fmt_num, fmt_mcap,
    REC_LABEL, SIGNAL_ORDER, GAIN, LOSS,
    GOLD, BG, SURFACE, BORDER, TEXT, MUTED, GRID,
    SIDEBAR, PANEL, HOVER, SELECTED, SHIMMER,
    BORDER_HAIRLINE, BORDER_PANEL, BORDER_CONTROL,
    INK_SOFT, MUTED_DEEP, DISABLED, SEVERITY,
)
from parsers import parse_all

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Portfolio Dashboard", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

# Palette → CSS custom properties, sourced from formatting.py (single source of
# truth). The rules below reference var(--token) so colours are never re-typed here.
st.markdown(f"""
<style>
:root {{
  --bg: {BG}; --sidebar: {SIDEBAR}; --panel: {PANEL}; --surface: {SURFACE};
  --hover: {HOVER}; --selected: {SELECTED}; --shimmer: {SHIMMER};
  --border-hair: {BORDER_HAIRLINE}; --border-panel: {BORDER_PANEL};
  --border-card: {BORDER}; --border-control: {BORDER_CONTROL};
  --ink: {TEXT}; --ink-soft: {INK_SOFT}; --muted: {MUTED};
  --muted-deep: {MUTED_DEEP}; --disabled: {DISABLED};
  --gold: {GOLD}; --gain: {GAIN}; --loss: {LOSS};
}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"], [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.stApp { background: var(--bg); }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }
/* hide menu/footer/deploy chrome — but NOT the whole toolbar (it holds the sidebar
   re-open button when the sidebar is collapsed) */
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stAppDeployButton"] { display: none; }
/* always keep the sidebar collapse/expand control visible & on-brand */
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"] {
  display: flex !important; visibility: visible !important; opacity: 1 !important; }
[data-testid="stSidebarCollapsedControl"] svg, [data-testid="stSidebarCollapseButton"] svg { color: var(--gold); }
h1, h2, h3, h4 { font-weight: 700; letter-spacing: -0.01em; color: var(--ink); }
hr { border-color: var(--border-hair); }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: var(--sidebar); border-right: 1px solid var(--border-hair); }
.brand-title { font-size: 1.3rem; font-weight: 800; letter-spacing: 0.18em; color: var(--gold); padding-top: 0.3rem; }
.brand-sub { font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted-deep); margin-bottom: 0.5rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 2px; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  display: flex; align-items: center; width: 100%; padding: 0.5rem 0.7rem; margin: 0;
  border-radius: 10px; cursor: pointer; transition: background .15s; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: var(--hover); }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 0.95rem; color: var(--ink-soft); font-weight: 500; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: var(--selected); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: var(--gold); font-weight: 600; }

/* ── Metric → card ── */
[data-testid="stMetric"] {
  background: var(--surface); border: 1px solid var(--border-card); border-radius: 14px;
  padding: 1rem 1.1rem; }
[data-testid="stMetricLabel"] p { text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.72rem; color: var(--muted); }
[data-testid="stMetricValue"] { font-size: 1.65rem; font-weight: 700; color: var(--ink); }
[data-testid="stMetricDelta"] { font-size: 0.9rem; }

/* ── Bordered containers → cards ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--panel); border: 1px solid var(--border-panel) !important; border-radius: 16px; }

/* ── Hero ── */
.hero { text-align: center; padding: 1.4rem 0 0.6rem; }
.hero-label { text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.8rem; color: var(--muted); }
.hero-value { font-size: 3.4rem; font-weight: 800; color: var(--gold); line-height: 1.05; margin: 0.2rem 0; letter-spacing: -0.02em; }
.hero-pnl { font-size: 1.15rem; font-weight: 600; }
.hero-pnl-muted { color: var(--muted-deep); font-weight: 500; }
.hero-sub { color: var(--muted); font-size: 0.9rem; margin-top: 0.2rem; }
.section-title { font-size: 1.5rem; font-weight: 700; color: var(--ink); margin-bottom: 0.2rem; }

/* tabs / buttons / dataframe */
.stTabs [data-baseweb="tab-list"] { gap: 2px; flex-wrap: wrap; border-bottom: 1px solid var(--border-hair); }
.stTabs [data-baseweb="tab"] { padding: 6px 14px; border-radius: 8px 8px 0 0; }
.stTabs [aria-selected="true"] { color: var(--gold); }
.stButton button, .stDownloadButton button {
  border-radius: 10px; border: 1px solid var(--border-control); background: var(--hover); color: var(--ink); font-weight: 500; }
.stButton button:hover, .stDownloadButton button:hover { border-color: var(--gold); color: var(--gold); }
.stButton button:focus-visible, .stDownloadButton button:focus-visible {
  outline: none; border-color: var(--gold); color: var(--gold);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--gold) 35%, transparent); }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* ── Touch targets on coarse pointers (mobile/tablet) ── */
@media (pointer: coarse) {
  .stTabs [data-baseweb="tab"] { padding: 12px 16px; }
  [data-testid="stSidebar"] [role="radiogroup"] label { padding: 0.75rem 0.8rem; }
}

/* ── Skeleton loaders ── */
.sk { background: linear-gradient(90deg, var(--surface) 25%, var(--shimmer) 37%, var(--surface) 63%);
  background-size: 400% 100%; animation: sksh 1.4s ease infinite; border-radius: 8px; }
@keyframes sksh { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
.sk-card { background: var(--panel); border: 1px solid var(--border-panel); border-radius: 14px; padding: 1.1rem; }
.sk-row { display: flex; gap: 14px; margin: 1rem 0; }
@media (prefers-reduced-motion: reduce) { .sk { animation: none; } }
</style>
""", unsafe_allow_html=True)

# Dashboard-shaped skeleton shown while the first (cold) data load runs
_sk_cards = "".join(
    '<div class="sk-card" style="flex:1;">'
    '<div class="sk" style="height:12px;width:55%;margin-bottom:14px;"></div>'
    '<div class="sk" style="height:26px;width:78%;"></div></div>' for _ in range(4))
_SKELETON = f"""
<div style="max-width:1400px;margin:0 auto;">
  <div style="text-align:center;padding:1.6rem 0 0.4rem;">
    <div class="sk" style="height:14px;width:150px;margin:0 auto 14px;"></div>
    <div class="sk" style="height:50px;width:320px;margin:0 auto 12px;"></div>
    <div class="sk" style="height:16px;width:220px;margin:0 auto;"></div>
  </div>
  <div class="sk-row">{_sk_cards}</div>
  <div class="sk-card" style="margin-top:0.6rem;"><div class="sk" style="height:360px;width:100%;"></div></div>
</div>
"""

# Global click-spark effect (gold sparks radiate from every click)
click_spark(spark_color=GOLD, spark_size=13, spark_radius=30, spark_count=9, duration=400)

# ─── Backend: Supabase accounts (if configured) else local files ─────────────
# When SUPABASE_URL + SUPABASE_ANON_KEY are in secrets, the app requires login and
# stores each user's portfolio/snapshots/watchlist privately in Supabase. Otherwise
# it behaves exactly as before (local files, with optional per-session isolation).

LANDING_URL = "https://capraaghav.github.io/portfolio-dashboard/"  # standalone marketing page (GitHub Pages)
USE_DB = db.is_enabled()
store = db if USE_DB else storage

if USE_DB:
    db.init_cookies()     # construct the CookieManager once for this run (before any get/set)
    db.restore_session()  # re-auth from cookie after a browser refresh wipes session_state
    # NOTE: the auth gate is deferred to just after render_landing() is defined, so a
    # logged-out visitor sees the landing page first and the login form below it.

def _is_multiuser() -> bool:
    if os.getenv("PORTFOLIO_MULTIUSER") == "1":
        return True
    try:
        return str(st.secrets.get("PORTFOLIO_MULTIUSER", "")).strip() == "1"
    except Exception:
        return False

MULTIUSER = (not USE_DB) and _is_multiuser()
if MULTIUSER:
    if "_sid" not in st.session_state:
        st.session_state["_sid"] = uuid.uuid4().hex[:12]
    storage.configure(Path(tempfile.gettempdir()) / "portfolio_sessions" / st.session_state["_sid"])


def render_landing(subline: str) -> None:
    """Compact in-app hero. The full marketing landing is the standalone index.html
    page (hosted separately) — embedding it here nested the app inside itself, so the
    app just shows this hero above the login form / upload prompt."""
    st.markdown(f"""
<div style="max-width:920px;margin:0 auto;text-align:center;padding:1rem 0 0.3rem;">
  <div style="text-transform:uppercase;letter-spacing:0.16em;font-size:0.78rem;color:var(--muted);">
    Portfolio · Indian Markets · NSE / BSE</div>
  <div style="font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;line-height:1.08;
    letter-spacing:-0.02em;color:var(--ink);margin:0.4rem 0 0.3rem;">
    Everything you own, <span style="color:var(--gold);">in one honest view.</span></div>
  <div style="color:var(--ink-soft);font-size:1rem;">{subline}</div>
  <div style="margin-top:0.7rem;"><a href="{LANDING_URL}" target="_blank" style="color:var(--gold);font-weight:600;font-size:0.92rem;text-decoration:none;">New here? See what it does →</a></div>
</div>
""", unsafe_allow_html=True)


# Bundled onboarding sample — two demo accounts fed through the real parser so a
# new visitor sees a populated, insight-rich dashboard without owning a broker file.
_DEMO_FILES = [("demo_long_term.csv", "Demo — Long Term"),
               ("demo_trading.csv", "Demo — Trading")]


@st.cache_data(show_spinner=False)
def load_demo() -> "pd.DataFrame | None":
    """Parse the bundled sample CSVs into the canonical raw schema (no I/O on disk
    beyond reading the shipped files; routed through parsers.parse_all like a real
    upload). Cached — the files never change."""
    sample_dir = Path(__file__).parent / "data" / "sample"
    uploads, names = [], {}
    for fname, label in _DEMO_FILES:
        path = sample_dir / fname
        if not path.exists():
            return None
        buf = io.BytesIO(path.read_bytes())
        buf.name = fname
        uploads.append(buf)
        names[fname] = label
    raw_df, _ = parse_all(uploads, names)
    return raw_df


# Auth gate. Logged-out visitors get a compact hero + the login form. The full
# marketing page lives separately at index.html (its CTA opens this app).
if USE_DB:
    if not db.current_user():
        render_landing("Sign in below to get started.")
        db.render_auth()
        st.stop()
    db.persist_cookie()   # (re)write the refresh-token cookie each logged-in run

# ─── Session state ────────────────────────────────────────────────────────────

if "overrides" not in st.session_state:
    st.session_state.overrides = store.load_overrides()
if "watchlist" not in st.session_state:
    st.session_state.watchlist = store.load_watchlist()


def _wk52_pct(ticker, prices_map, fund_map):
    f = fund_map.get(ticker) or {}
    low, high, price = f.get("wk52_low"), f.get("wk52_high"), prices_map.get(ticker)
    if all([low, high, price]) and high > low:
        return (price - low) / (high - low) * 100
    return np.nan


def _pnl_styler(disp_df: pd.DataFrame, num_df: pd.DataFrame, cols):
    """Tint directional value columns mint (gain) / coral (loss) by their numeric
    sign, while the formatted strings keep their +/- so the meaning never relies on
    colour alone (WCAG-safe). `disp_df` holds the formatted strings; `num_df` is the
    aligned numeric source the sign is read from (same row order)."""
    present = [c for c in cols if c in disp_df.columns and c in num_df.columns]

    def _col(series):
        out = []
        for v in num_df[series.name].to_numpy():
            if pd.notna(v) and v > 0:
                out.append(f"color: {GAIN}")
            elif pd.notna(v) and v < 0:
                out.append(f"color: {LOSS}")
            else:
                out.append("")
        return out

    sty = disp_df.style
    if present:
        sty = sty.apply(_col, axis=0, subset=present)
    return sty


# Directional value columns that earn the mint/coral signal in tables
_PNL_COLS = ["Gain/Loss (₹)", "Gain/Loss (%)", "Upside (%)"]


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


# ─── Click-through navigation (Technical chart/table → Stock Detail) ──────────

def _go_to_detail(ticker: str | None, guard: str) -> None:
    """Jump to the Stock Detail section for `ticker` (a click-through from another
    surface). `guard` is a per-source session-state key holding the last ticker that
    triggered navigation: a stale selection still sitting in a widget's state must not
    bounce the user straight back out when they return to this tab, so we navigate only
    on a *new* selection. No-op when there's no ticker or it's unchanged."""
    if not ticker or st.session_state.get(guard) == ticker:
        return
    st.session_state[guard] = ticker
    st.session_state["_goto_section"] = "🔍 Stock Detail"
    st.session_state["_goto_ticker"] = ticker
    st.rerun()


def _plotly_clicked_ticker(ev) -> str | None:
    """Pull the clicked bar's ticker (its x category) from a plotly selection event."""
    try:
        pts = ev.selection["points"] if (ev and ev.selection) else []
    except Exception:
        pts = []
    return pts[0].get("x") if pts else None


# ─── Sidebar: brand + navigation + upload/data ───────────────────────────────

SECTIONS = ["🧠 Intelligence", "📊 Overview", "📋 Holdings", "📈 Performance", "🔬 Technical", "🔎 Screener",
            "🎯 Analysts", "🧮 Tax", "⚠️ Risk", "💰 Dividends", "📅 Earnings Calendar",
            "🔍 Stock Detail", "👁️ Watchlist", "⚖️ Rebalance"]

with st.sidebar:
    st.markdown('<div class="brand-title">PORTFOLIO</div>'
                '<div class="brand-sub">Indian Markets · NSE / BSE</div>', unsafe_allow_html=True)
    if USE_DB:
        _u = db.current_user()
        c_acc, c_out = st.columns([3, 1])
        c_acc.caption(f"👤 {_u['email']}" if _u else "")
        if c_out.button("Log out", key="logout"):
            db.sign_out()
            # Wipe all per-user state (watchlist, overrides, uploaded file, cached
            # holdings) so the next person to log in on this browser starts clean.
            st.session_state.clear()
            st.rerun()
        with st.expander("🔐 Security"):
            _2fa_on = db.twofa_enabled()
            _want = st.toggle("Require email code at login (2FA)", value=_2fa_on,
                              key="twofa_toggle",
                              help="Adds a one-time code, emailed each time you log in, "
                                   "on top of your password.")
            if _want != _2fa_on:
                ok, err = db.set_twofa(_want)
                if ok:
                    st.success(("Two-factor enabled." if _want else "Two-factor disabled."))
                    st.rerun()
                else:
                    st.error(err)
    # A click-through from another tab (e.g. Technical) parks the target section
    # here; apply it before the radio instantiates so it lands selected.
    # Initialise the data-toggle defaults once (so the toggles can be widget-keyed
    # and still programmatically set — e.g. by the sample-data demo — without the
    # value=/key= conflict).
    for _k, _d in (("load_meta", True), ("load_ta", False), ("load_div", False)):
        st.session_state.setdefault(_k, _d)
    # Freshly-loaded sample demo: turn on depth toggles and land on Intelligence,
    # all BEFORE the toggle/radio widgets instantiate (same pre-widget pattern).
    if st.session_state.get("_demo") and not st.session_state.get("_demo_seeded"):
        st.session_state["load_meta"] = True
        st.session_state["load_ta"] = True
        st.session_state["load_div"] = True
        st.session_state["_goto_section"] = "🧠 Intelligence"
        st.session_state["_demo_seeded"] = True
    if "_goto_section" in st.session_state:
        st.session_state["nav"] = st.session_state.pop("_goto_section")
    section = st.radio("Navigation", SECTIONS, label_visibility="collapsed", key="nav")
    st.divider()

    with st.expander("⚙️  Upload / Data", expanded=not bool(st.session_state.get("uploader"))):
        st.caption("CSV / Excel / PDF from any broker. Each file = one account.")
        uploaded = st.file_uploader("Drop files here", type=["csv", "xlsx", "xls", "pdf"],
                                    accept_multiple_files=True, label_visibility="collapsed",
                                    key="uploader")

        account_names: dict[str, str] = {}
        if uploaded:
            st.caption("Account labels")
            for f in uploaded:
                default = f.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
                account_names[f.name] = st.text_input(f"`{f.name}`", value=default, key=f"acct_{f.name}")

        # Offer to reload the last saved session if nothing is uploaded
        use_saved = False
        if not uploaded:
            meta_info = store.session_meta()
            if meta_info:
                st.info(f"Last session: **{meta_info.get('rows', '?')} rows** "
                        f"saved {meta_info.get('saved_at', '')[:16].replace('T', ' ')}")
                use_saved = st.button("↩️ Load last session", width='stretch')
            if st.button("✨ Load sample portfolio", width='stretch',
                         help="Explore the dashboard with a demo portfolio — no file needed."):
                st.session_state["_demo"] = True
                st.session_state["_demo_seeded"] = False
                st.session_state["_use_saved"] = False
                st.rerun()

        st.divider()
        exclude_nonequity = st.toggle("Equity only (remove funds & bonds)", value=False,
                                      help="Drops mutual funds and bonds/NCDs from the entire dashboard.")
        load_meta = st.toggle("Sectors, targets & fundamentals", key="load_meta",
                              help="One Yahoo Finance .info call per stock. Slower on first load, cached 1 hour.")
        load_ta = st.toggle("Technical analysis (SMA / RSI)", key="load_ta",
                            help="Bulk-downloads price history. ~10s first load, cached 1 hour.")
        load_div = st.toggle("Dividend data", key="load_div",
                             help="Fetches dividend history per stock for the Dividends section.")

        if st.button("🔄 Refresh data (clear cache)", width='stretch'):
            for fn in (md.fetch_quotes, md.fetch_metadata, md.fetch_ta_signals,
                       md.fetch_dividends, md.fetch_closes):
                fn.clear()
            st.rerun()

    with st.expander("📁 Supported formats"):
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
    if USE_DB:
        st.caption("🔒 Saved privately to your account (Supabase). Only you can see your data.")
    elif MULTIUSER:
        st.caption("🔒 Your upload is processed in a private session and is **not stored** after you "
                   "leave. Other visitors can't see your data.")
    else:
        st.caption("🔒 Runs entirely on your machine. No portfolio data leaves your computer.")

# ─── Acquire raw data (upload or saved session) ──────────────────────────────

raw: pd.DataFrame | None = None
if uploaded:
    st.session_state["_demo"] = False     # a real upload always wins over the demo
    raw, parse_errors = parse_all(uploaded, account_names)
    for fname, err in parse_errors:
        st.error(f"**`{fname}`** — {err}")
    if raw is not None:
        store.save_session(raw)
    st.session_state["_use_saved"] = False
elif st.session_state.get("_demo"):
    # Sample portfolio — parsed from the bundled CSVs; never persisted, so it can't
    # overwrite a real saved session.
    raw = load_demo()
    st.session_state["_use_saved"] = False
elif use_saved or st.session_state.get("_use_saved"):
    # Keep the loaded session across reruns (the button is one-shot) so filters/
    # interactions don't drop the data.
    st.session_state["_use_saved"] = True
    raw = store.load_session()

if section == "🔎 Screener":
    st.markdown('<p class="section-title">🔎 Screener</p>', unsafe_allow_html=True)

    # ── Mode selector ──────────────────────────────────────────────────────
    scr_mode = st.radio(
        "Source",
        ["🌐 NSE Universe", "📂 Upload Watchlist", "💼 My Accounts"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # Holdings from a previously uploaded/saved portfolio, for the "My Accounts" mode.
    scr_raw = store.load_session()
    scr_accts = sorted(scr_raw["account"].dropna().unique()) if (
        scr_raw is not None and not scr_raw.empty and "account" in scr_raw.columns) else []

    col_src, col_run = st.columns([3, 1])
    scr_symbols: list = []
    scr_source_label = ""

    if scr_mode == "🌐 NSE Universe":
        with col_src:
            universe_name = st.selectbox(
                "Universe",
                ["Nifty 500", "Nifty 50"],
                label_visibility="collapsed",
            )
        scr_source_label = universe_name
    elif scr_mode == "📂 Upload Watchlist":
        with col_src:
            wl_file = st.file_uploader(
                "Upload watchlist (CSV / XLS / XLSX)",
                type=["csv", "xls", "xlsx"],
                label_visibility="collapsed",
            )
    else:  # 💼 My Accounts
        with col_src:
            if not scr_accts:
                st.info("No uploaded portfolio found. Add files in **⚙️ Upload / Data** first.")
                scr_sel_accts = []
            else:
                scr_sel_accts = st.multiselect(
                    "Accounts", scr_accts, default=scr_accts,
                    label_visibility="collapsed",
                    help="Screen the stocks you hold in the chosen accounts.")

    # ── Filters ────────────────────────────────────────────────────────────
    with st.expander("⚙️ Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        tolerance = fc1.slider("SMA Tolerance (%)", 0.1, 5.0, 1.0, 0.1,
                               help="Max % distance between SMA10 and SMA50")
        bullish_only = fc2.checkbox("Bullish Only (SMA10 ≥ SMA50)", value=True)
        sort_by = fc3.selectbox(
            "Sort by",
            ["Closest Match", "Highest RSI", "Lowest RSI", "Highest Price", "Lowest Price", "Alphabetical"],
        )
        fp1, fp2, fp3, fp4 = st.columns(4)
        rsi_min = fp1.number_input("RSI Min", 0, 100, 50, step=1)
        rsi_max = fp2.number_input("RSI Max", 0, 100, 65, step=1)
        price_min = fp3.number_input("Min Price (₹)", 0, value=0, step=10)
        price_max_raw = fp4.number_input("Max Price (₹)", 0, value=0, step=100,
                                          help="0 = no limit")
        price_max = float(price_max_raw) if price_max_raw > 0 else None

    run_btn = col_run.button("▶ Run Screener", type="primary", use_container_width=True)

    if run_btn:
        # ── Resolve symbol list ────────────────────────────────────────────
        if scr_mode == "🌐 NSE Universe":
            with st.spinner(f"Loading {universe_name}…"):
                scr_symbols = md.get_universe(universe_name)
            scr_source_label = universe_name
        elif scr_mode == "📂 Upload Watchlist":
            if "wl_file" not in dir() or wl_file is None:
                st.warning("Upload a watchlist file first.")
                st.stop()
            syms, err = scr.parse_watchlist_upload(wl_file.read(), wl_file.name)
            if err:
                st.error(err)
                st.stop()
            scr_symbols = syms
            scr_source_label = f"Uploaded ({len(syms)} symbols)"
        else:  # 💼 My Accounts
            if not scr_sel_accts:
                st.warning("Pick at least one account to screen.")
                st.stop()
            held = scr_raw[scr_raw["account"].isin(scr_sel_accts)]
            scr_symbols = sorted(t for t in held["ticker"].dropna().unique()
                                 if parsers.looks_like_symbol(str(t)) and not parsers.is_isin(str(t)))
            scr_source_label = f"My Accounts ({len(scr_symbols)} stocks)"

        if not scr_symbols:
            st.warning("No symbols to screen.")
        else:
            # ── Fetch history ──────────────────────────────────────────────
            suffix_map_scr = {t: ".NS" for t in scr_symbols}
            tickers_tuple_scr = tuple(scr_symbols)
            with st.spinner(f"Fetching 200-day history for {len(scr_symbols)} stocks…"):
                closes_dict = md.fetch_screener_history(tickers_tuple_scr, suffix_map_scr, "200d")

            # ── Compute metrics ────────────────────────────────────────────
            with st.spinner("Computing indicators…"):
                metrics_df, skipped = analytics.calculate_screening_metrics(closes_dict)

            # ── Run engine ─────────────────────────────────────────────────
            engine = scr.ScreeningEngine()
            rule = scr.SMAProximityRule(tolerance_pct=tolerance, bullish_only=bullish_only)
            results, rejected_sma, rejected_rsi = engine.run(
                metrics_df,
                rules=[rule],
                price_min=float(price_min),
                price_max=price_max,
                rsi_min=float(rsi_min),
                rsi_max=float(rsi_max),
            )

            # ── Apply sort ─────────────────────────────────────────────────
            sort_map = {
                "Closest Match":  ("distance_pct", True),
                "Highest RSI":    ("rsi", False),
                "Lowest RSI":     ("rsi", True),
                "Highest Price":  ("price", False),
                "Lowest Price":   ("price", True),
                "Alphabetical":   ("ticker", True),
            }
            scol, sasc = sort_map.get(sort_by, ("distance_pct", True))
            if not results.empty:
                results = results.sort_values(scol, ascending=sasc).reset_index(drop=True)

            screened = len(closes_dict)
            matched = len(results)
            avg_rsi = round(results["rsi"].mean(), 1) if not results.empty else 0

            # ── KPI cards ─────────────────────────────────────────────────
            k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
            k1.metric("Universe", len(scr_symbols))
            k2.metric("Screened", screened)
            k3.metric("Rejected (SMA)", rejected_sma)
            k4.metric("Rejected (RSI)", rejected_rsi)
            k5.metric("Matched", matched)
            k6.metric("Skipped", len(skipped))
            k7.metric("Avg RSI (matched)", avg_rsi if matched else "—")

            filters_lines = [
                f"✓ SMA10 within {tolerance}% of SMA50",
                f"✓ RSI between {rsi_min} and {rsi_max}",
            ]
            if bullish_only:
                filters_lines.append("✓ Bullish Only")
            if price_min > 0:
                filters_lines.append(f"✓ Price ≥ ₹{int(price_min):,}")
            if price_max:
                filters_lines.append(f"✓ Price ≤ ₹{int(price_max):,}")
            st.info("**Active Filters** — " + " · ".join(filters_lines))

            if results.empty:
                st.info(f"No stocks matched within {tolerance}% SMA tolerance. Try widening the filter.")
            else:
                # ── Results table ──────────────────────────────────────────
                disp_df = results[["ticker", "price", "rsi", "sma10", "sma50", "distance_pct", "signal"]].copy()
                disp_df.columns = ["Symbol", "Price (₹)", "RSI", "SMA10", "SMA50", "Diff %", "Signal"]
                disp_df["Price (₹)"] = disp_df["Price (₹)"].apply(lambda v: fmt_inr(v))
                disp_df["RSI"] = disp_df["RSI"].apply(lambda v: fmt_num(v, 1))
                disp_df["SMA10"] = disp_df["SMA10"].apply(lambda v: fmt_num(v, 2))
                disp_df["SMA50"] = disp_df["SMA50"].apply(lambda v: fmt_num(v, 2))
                disp_df["Diff %"] = disp_df["Diff %"].apply(lambda v: f"{v:.2f}%")

                SIGNAL_COLORS = {
                    "Perfect Touch": GOLD,
                    "Bullish Cross": GAIN,
                    "Bullish Touch": "#5ba85f",
                }

                def _sig_color(val):
                    c = SIGNAL_COLORS.get(val, MUTED)
                    return f"color: {c}; font-weight: 600"

                styled = disp_df.style.map(_sig_color, subset=["Signal"])
                st.dataframe(styled, use_container_width=True, hide_index=True)

                # ── Advanced metrics ───────────────────────────────────────
                with st.expander("📐 Advanced Metrics"):
                    adv = results[["ticker", "sma10_above", "wk52_high", "wk52_low", "price"]].copy()
                    adv["Above SMA50"] = adv["sma10_above"].map({True: "✓ Yes", False: "✗ No"})
                    adv["Dist 52W High"] = adv.apply(
                        lambda r: f"{(r['price']/r['wk52_high']-1)*100:.1f}%" if r['wk52_high'] > 0 else "—", axis=1
                    )
                    adv["Dist 52W Low"] = adv.apply(
                        lambda r: f"{(r['price']/r['wk52_low']-1)*100:.1f}%" if r['wk52_low'] > 0 else "—", axis=1
                    )
                    st.dataframe(
                        adv[["ticker", "Above SMA50", "Dist 52W High", "Dist 52W Low"]].rename(columns={"ticker": "Symbol"}),
                        use_container_width=True, hide_index=True
                    )

                # ── Export ─────────────────────────────────────────────────
                export_df = results[["ticker", "price", "rsi", "sma10", "sma50", "distance_pct", "signal"]].copy()
                export_df.columns = ["symbol", "price", "rsi", "sma10", "sma50", "distance_pct", "signal"]
                ce1, ce2 = st.columns(2)
                ce1.download_button(
                    "⬇️ Export CSV",
                    export_df.to_csv(index=False).encode(),
                    file_name=f"screener_{pd.Timestamp.now():%Y%m%d_%H%M}.csv",
                    mime="text/csv",
                )
                ce2.download_button(
                    "⬇️ Export Excel",
                    to_excel_bytes(export_df, {}),
                    file_name=f"screener_{pd.Timestamp.now():%Y%m%d_%H%M}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            # ── Skipped diagnostics ────────────────────────────────────────
            if skipped:
                with st.expander(f"⚠️ Skipped symbols ({len(skipped)})"):
                    st.caption("Skipped due to insufficient price history (< 60 trading days):")
                    st.write(", ".join(sorted(skipped)))

    st.stop()

if raw is None or raw.empty:
    render_landing("⚙️ Open <b>Upload / Data</b> in the sidebar and drop your broker file to begin.")
    _, cmid, _ = st.columns([1, 1.4, 1])
    with cmid:
        st.write("")
        if st.button("✨ Try it with sample data →", width='stretch', type="primary"):
            st.session_state["_demo"] = True
            st.session_state["_demo_seeded"] = False
            st.session_state["_use_saved"] = False
            st.rerun()
        st.caption("Loads a demo portfolio so you can explore everything — "
                   "no file, nothing saved. Your own upload replaces it anytime.")
    st.stop()

if st.session_state.get("_demo"):
    _bnl, _bnr = st.columns([6, 1])
    _bnl.info("✨ You're viewing **sample data** — explore freely. "
              "Upload your own broker file in the sidebar to replace it.")
    if _bnr.button("Clear", help="Exit the sample portfolio", width='stretch'):
        st.session_state["_demo"] = False
        st.session_state["_demo_seeded"] = False
        st.rerun()

# ─── Global account selector — scope the whole dashboard to chosen accounts ───
# Lives in the sidebar (a second `with st.sidebar` block, rendered after raw is
# known). Filters `raw` before holdings/totals/sections so every tab reflects the
# selection. Only shown when more than one account was uploaded.
if "account" in raw.columns:
    _all_accts = sorted(raw["account"].dropna().unique())
    if len(_all_accts) > 1:
        with st.sidebar:
            with st.expander("🗂️  Accounts", expanded=True):
                st.caption("Choose which uploaded accounts feed the dashboard.")
                _sel_accts = st.multiselect(
                    "Include accounts", _all_accts, default=_all_accts,
                    key="global_accounts", label_visibility="collapsed")
        if not _sel_accts:
            st.warning("No accounts selected — pick at least one in the sidebar **🗂️ Accounts**.")
            st.stop()
        if set(_sel_accts) != set(_all_accts):
            raw = raw[raw["account"].isin(_sel_accts)].copy()

# ─── Resolve symbols (some brokers store the full company name or only an ISIN) ─

# Show a dashboard-shaped skeleton while the first (cold) load runs; cleared once
# holdings are built. Skipped on later reruns (caches are warm → no flicker).
_sk = st.empty()
if not st.session_state.get("_data_ready"):
    _sk.markdown(_SKELETON, unsafe_allow_html=True)

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

# Data is ready — clear the loading skeleton
st.session_state["_data_ready"] = True
_sk.empty()

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
    store.auto_snapshot_if_new(totals, holdings)
except Exception:
    pass

# AI Portfolio Intelligence — deterministic detection over the data above.
# Pure call; never crashes the dashboard if a detector misbehaves.
try:
    intel = intelligence.analyze(holdings, raw, prices, meta, totals, ta_signals, quotes)
except Exception:
    intel = {"insights": [], "health": None, "move": {}, "empty": True}

# Genuine failures = Yahoo-eligible equities we still couldn't price (not MF/NCD/unresolved)
failed_tickers = [t for t in yahoo_tickers if prices.get(t) is None]
non_yahoo = [t for t in tickers_tuple if t not in yahoo_eligible]
has_cost_basis = "avg_cost" in raw.columns and raw["avg_cost"].notna().any()

# ─── Global notices (shown above the selected section) ───────────────────────

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

# ─── Sections (chosen from the sidebar nav; `section` is set in the sidebar) ──

# Shared filtered view (account filter lives in Holdings, but Overview shows all)
chart_data = holdings.dropna(subset=["Current Value (₹)"])
chart_data = chart_data[chart_data["Current Value (₹)"] > 0]


# ─── Intelligence rendering helpers (shared by the brief + the section) ───────

# Friendly labels + value formatting for the per-insight evidence, so a
# non-technical user reads "Largest holding: TITAN" not a raw JSON dump.
_EV_LABEL = {
    "top1_ticker": "Largest holding", "top1_pct": "Its weight",
    "top5_pct": "Top-5 weight", "top_sector": "Largest sector",
    "top_sector_pct": "Sector weight", "effective_n": "Effective holdings",
    "n_positions": "Positions", "portfolio_beta": "Portfolio beta",
    "threshold": "Flagged above", "harvestable_loss": "Harvestable loss",
    "n": "Positions at a loss", "has_gains": "Gains to offset?",
    "n_unpriced": "Unpriced holdings", "n_total": "Total holdings",
    "coverage": "Live-price coverage", "rsi_threshold": "Overbought above",
    "abs": "Value change", "pct": "% change", "top_gainer": "Top gainer",
    "top_loser": "Top loser", "ticker": "Stock", "weight_pct": "Weight",
    "price": "Price", "target_mean": "Analyst target", "upside_pct": "Upside to target",
    "pe": "P/E", "sector_pe": "Sector P/E", "rsi": "RSI",
    "near_52w_high": "At 52-wk high", "above_target": "Above target", "rich_pe": "Rich P/E",
    "flagged": "Flagged holdings", "overbought": "Overbought holdings",
}
_EV_MONEY = {"harvestable_loss", "abs", "price", "target_mean"}
_EV_PCT = {"top1_pct", "top5_pct", "top_sector_pct", "weight_pct", "upside_pct", "pct", "threshold"}
_EV_BOOL = {"has_gains", "near_52w_high", "above_target", "rich_pe"}
_EV_LIST = {"flagged", "overbought"}


def _ev_label(k):
    return _EV_LABEL.get(k, k.replace("_", " ").capitalize())


def _ev_val(k, v):
    """Format one evidence value for humans."""
    if v is None:
        return "—"
    if isinstance(v, np.generic):       # unwrap numpy scalars (np.False_, np.float64…)
        v = v.item()
    if k in _EV_BOOL or isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, (list, tuple)) and len(v) == 2 and not isinstance(v[0], dict):
        return f"{v[0]} ({fmt_pct(v[1])})"     # (ticker, pct) e.g. top gainer
    if k in _EV_MONEY:
        return fmt_inr(v)
    if k == "coverage":
        return f"{v * 100:.0f}%"
    if k in _EV_PCT:
        return f"{v:g}%"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def render_evidence(ev):
    """Render an insight's evidence as friendly label/value rows + any detail tables."""
    scalars = {k: v for k, v in ev.items() if k not in _EV_LIST}
    if scalars:
        st.dataframe(
            pd.DataFrame([{"Metric": _ev_label(k), "Value": _ev_val(k, v)}
                         for k, v in scalars.items()]),
            hide_index=True, use_container_width=True)
    for lk in _EV_LIST:
        recs = ev.get(lk)
        if recs:
            st.caption(_ev_label(lk))
            st.dataframe(
                pd.DataFrame([{_ev_label(k): _ev_val(k, v) for k, v in r.items()}
                             for r in recs]),
                hide_index=True, use_container_width=True)


def render_insight_card(ins, key_prefix=""):
    """One insight as a bordered card: severity chip + title + body + evidence + link."""
    sev = SEVERITY.get(ins.severity, SEVERITY["low"])
    cat = ins.category.replace("_", " ").title()
    with st.container(border=True):
        st.markdown(
            f'<span style="color:{sev["tint"]};font-weight:700">{sev["glyph"]} {cat}</span>'
            f'<span style="color:{MUTED};font-size:0.72rem;letter-spacing:0.06em">'
            f' · {sev["word"].upper()}</span>',
            unsafe_allow_html=True)
        st.markdown(f'**{ins.title}**')
        st.markdown(f'<span style="color:{INK_SOFT}">{ins.body}</span>', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            with st.expander("Why this fired"):
                render_evidence(ins.evidence)
        with c2:
            if st.button(f"View in {ins.section.split(' ', 1)[-1]} →",
                         key=f"goto_{key_prefix}_{ins.id}", use_container_width=True):
                st.session_state["_goto_section"] = ins.section
                st.rerun()


def render_brief(insights, limit=3):
    """Condensed top-N brief (used on Overview)."""
    for ins in insights[:limit]:
        render_insight_card(ins, key_prefix="brief")


def render_checklist():
    """Getting-started checklist — ticks off as the user explores. Session-only."""
    if st.session_state.get("_checklist_hidden"):
        return
    try:
        has_watch = len(store.load_watchlist()) > 0
    except Exception:
        has_watch = False
    items = [
        ("Load a portfolio", True),  # past the data guard → always done here
        ("Open the Intelligence brief", bool(st.session_state.get("_seen_intel"))),
        ("Turn on Technical analysis", bool(st.session_state.get("load_ta"))),
        ("Explore 3 sections", len(st.session_state.get("_seen_sections", set())) >= 3),
        ("Add a stock to your Watchlist", has_watch),
    ]
    done = sum(d for _, d in items)
    if done == len(items):          # fully complete → retire it
        st.session_state["_checklist_hidden"] = True
        return
    with st.expander(f"🚀 Getting started · {done}/{len(items)}", expanded=(done < 2)):
        for label, ok in items:
            st.markdown(f"{'✅' if ok else '⬜'} {label}")
        if st.button("Dismiss", key="checklist_dismiss"):
            st.session_state["_checklist_hidden"] = True
            st.rerun()


_TOUR_STEPS = [
    ("Welcome to your desk",
     "You're in. Pick any of the **13 sections** from the sidebar on the left — they run "
     "from the big picture down to deep analysis."),
    ("🧠 Intelligence reads it for you",
     "The Intelligence section reviews your whole portfolio and surfaces what matters "
     "today — ranked, with the evidence behind every call."),
    ("Go deeper with the toggles",
     "Flip on **Technical / Dividends / Fundamentals** in the sidebar's Upload / Data "
     "panel. The deeper sections light up and Intelligence gets sharper."),
    ("Every claim is traceable",
     "On any insight, open **Why this fired** to see the exact numbers behind it. "
     "Nothing is invented."),
    ("Private by default",
     "Your data is processed locally and never sold. Upload your own broker file in the "
     "sidebar anytime to replace the sample."),
]


def render_tour():
    """Lightweight coach-mark tour (session-only). A pinned card at the top of the
    main area; Back / Next / Skip step through it."""
    step = st.session_state.get("_tour_step", 1)
    if not (1 <= step <= len(_TOUR_STEPS)):
        return
    title, body = _TOUR_STEPS[step - 1]
    with st.container(border=True):
        st.markdown(
            f'<span style="color:{GOLD};font-weight:700;letter-spacing:0.04em">'
            f'GETTING ORIENTED · {step}/{len(_TOUR_STEPS)}</span>', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        st.markdown(f'<span style="color:{INK_SOFT}">{body}</span>', unsafe_allow_html=True)
        cback, cnext, cskip = st.columns([1, 1, 1])
        if step > 1 and cback.button("← Back", key="tour_back", use_container_width=True):
            st.session_state["_tour_step"] = step - 1
            st.rerun()
        _last = step == len(_TOUR_STEPS)
        if cnext.button("Done ✓" if _last else "Next →", key="tour_next",
                        use_container_width=True, type="primary"):
            st.session_state["_tour_step"] = 0 if _last else step + 1
            st.rerun()
        if cskip.button("Skip", key="tour_skip", use_container_width=True):
            st.session_state["_tour_step"] = 0
            st.rerun()


# Onboarding: track exploration (session-only) + show the coach tour above sections.
_seen = st.session_state.setdefault("_seen_sections", set())
_seen.add(section)
if section == "🧠 Intelligence":
    st.session_state["_seen_intel"] = True
st.session_state.setdefault("_tour_step", 1)
render_tour()


# ═══ INTELLIGENCE ═════════════════════════════════════════════════════════════
if section == "🧠 Intelligence":
    st.markdown('<div class="hero-label">INTELLIGENCE</div>', unsafe_allow_html=True)
    render_checklist()
    cse, cre = st.columns([4, 1])
    cse.subheader("What matters about your portfolio today")
    if cre.button("↻ Re-analyse", use_container_width=True):
        st.rerun()

    health = intel.get("health")
    move = intel.get("move") or {}
    hc, mc = st.columns(2)
    with hc:
        with st.container(border=True):
            st.markdown('<div class="hero-label">PORTFOLIO HEALTH</div>', unsafe_allow_html=True)
            if health:
                fig = charts.health_gauge(health.score, health.band)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                with st.expander("Breakdown"):
                    for comp in health.components:
                        st.markdown(
                            f"**{comp.name}** · {comp.subscore:.0f}/100 "
                            f"<span style='color:{MUTED}'>(weight {comp.weight:.0%}) — "
                            f"{comp.reason}</span>", unsafe_allow_html=True)
            else:
                st.caption("Not enough priced data for a health score.")
    with mc:
        with st.container(border=True):
            st.markdown('<div class="hero-label">TODAY\'S MOVE</div>', unsafe_allow_html=True)
            pct = move.get("pct")
            if pct is not None:
                col = GAIN if (move.get("abs") or 0) >= 0 else LOSS
                st.markdown(
                    f'<div style="font-size:1.65rem;font-weight:700;color:{col}">'
                    f'{fmt_inr(move["abs"])}</div>'
                    f'<div style="color:{col}">{fmt_pct(pct)} today</div>',
                    unsafe_allow_html=True)
                g = move.get("top_gainer")
                if g:
                    st.caption(f"Top mover: {g[0]} ({g[1]:+.1f}%)")
            else:
                st.caption("Day change unavailable.")

    st.divider()
    st.markdown('<div class="hero-label">INSIGHTS</div>', unsafe_allow_html=True)
    insights = intel.get("insights") or []
    if intel.get("empty"):
        st.info("Upload a portfolio to get your intelligence brief.")
    elif not insights:
        st.success("Nothing demands attention today. No concentration, valuation, or "
                   "technical flags — your book looks balanced.")
    else:
        for ins in insights:
            render_insight_card(ins, key_prefix="full")
        st.caption("Insights are generated from your own analytics — every claim links to the "
                   "section that proves it. Information, not financial advice.")


# ═══ OVERVIEW ═════════════════════════════════════════════════════════════════
if section == "📊 Overview":
    # Hero — centred portfolio value
    if has_cost_basis:
        _pc = GAIN if (totals["pnl"] or 0) >= 0 else LOSS
        _pnl_html = f'<span style="color:{_pc}">{fmt_inr(totals["pnl"])} P&L ({fmt_pct(totals["pnl_pct"])})</span>'
        _sub = f'{fmt_inr(totals["cost"])} invested · cost basis'
    else:
        _pnl_html = '<span class="hero-pnl-muted">cost basis unavailable</span>'
        _sub = f'{totals["n_holdings"]} holdings · {n_accounts} account(s)'
    st.markdown(
        '<div class="hero">'
        '<div class="hero-label">PORTFOLIO VALUE</div>'
        f'<div class="hero-value">{fmt_inr(totals["value"])}</div>'
        f'<div class="hero-pnl">{_pnl_html}</div>'
        f'<div class="hero-sub">{_sub}</div>'
        '</div>', unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Today's Change", fmt_inr(day_chg_total, short=True) if day_chg_total else "—",
              fmt_pct(day_chg_pct) if day_chg_pct is not None else None)
    k2.metric("Holdings", totals["n_holdings"])
    k3.metric("Accounts", n_accounts)
    k4.metric("Live prices", f"{len(yahoo_eligible) - len(failed_tickers)}/{len(tickers_tuple)}")
    st.divider()

    # Intelligence brief — the top few things that matter, surfaced first.
    _brief = intel.get("insights") or []
    if _brief:
        bh1, bh2 = st.columns([4, 1])
        bh1.subheader("🧠 What matters today")
        if intel.get("health"):
            bh2.metric("Health", f"{intel['health'].score}", help=intel["health"].band)
        render_brief(_brief, limit=3)
        if st.button("See full intelligence brief →", key="overview_to_intel"):
            st.session_state["_goto_section"] = "🧠 Intelligence"
            st.rerun()
        st.divider()

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
elif section == "📋 Holdings":
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

    # Secondary filters live in a popover so the data table leads the page, not the controls
    sectors_avail = sorted([s for s in holdings["Sector"].dropna().unique() if s])
    atypes_avail = sorted(set(asset_of.values()))
    with st.popover("⚙️ More filters", use_container_width=False):
        sector_sel = st.selectbox("Sector", ["All sectors"] + sectors_avail)
        type_sel = st.selectbox("Asset type", ["All types"] + atypes_avail)
        trend_sel = st.selectbox(
            "Trend", (["All trends"] + [s for s in SIGNAL_ORDER if s != "N/A"]) if ta_signals else ["All trends"],
            disabled=not ta_signals,
            help=None if ta_signals else "Turn on Technical analysis in the sidebar to filter by trend.")
        show_fund = st.checkbox("Show fundamentals (P/E, P/B, Mkt Cap, Beta, 52w)", value=False) if load_meta else False
        in_all = (st.checkbox("🔗 Held in all accounts only", value=False,
                              help="Show only stocks held in every selected account.")
                  if n_accounts > 1 else False)

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
    if sector_sel != "All sectors":
        fh = fh[fh["Sector"] == sector_sel]
    if type_sel != "All types":
        fh = fh[fh["Ticker"].map(lambda t: asset_of.get(t, "Equity")) == type_sel]
    if ta_signals and trend_sel != "All trends":
        fh = fh[fh["Ticker"].map(lambda t: ta_signals.get(t, {}).get("signal", "N/A")) == trend_sel]
    if in_all:
        n_sel = len(sel_accounts) if sel_accounts else len(all_accounts)
        fh = fh[fh["Accounts"].apply(lambda s: len(str(s).split(", ")) == n_sel)]

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

    event = st.dataframe(_pnl_styler(disp, fh, _PNL_COLS), width='stretch', hide_index=True,
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
            st.dataframe(_pnl_styler(bdisp, bd, _PNL_COLS), width='stretch', hide_index=True)

    ec1, ec2 = st.columns([1, 4])
    with ec1:
        st.download_button("⬇️ Export to Excel", to_excel_bytes(fh, totals),
                           file_name=f"portfolio_{pd.Timestamp.now():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           width='stretch')

    with st.expander("📋 Copy to TradingView"):
        st.caption("Copy, then paste into TradingView → Watchlist → ⋯ → Import list.")
        st.code(analytics.tradingview_list(fh["Ticker"], suffix_map,
                                           header=f"Portfolio {pd.Timestamp.now():%d %b %Y}"),
                language=None)

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
                store.save_overrides(st.session_state.overrides)
                st.success("Saved. Refreshing…")
                st.rerun()


# ═══ PERFORMANCE ══════════════════════════════════════════════════════════════
elif section == "📈 Performance":
    st.subheader("Performance Over Time")

    snap_df = store.snapshots_df()
    sc1, sc2 = st.columns([3, 1])
    with sc2:
        if st.button("📸 Save snapshot now", width='stretch'):
            store.save_snapshot(totals, holdings)
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
elif section == "🔬 Technical":
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

        def _vs50f(t):
            v = ta_signals.get(t, {}).get("vs_50ma")
            if not v:
                return None
            try:
                return float(v.replace("%", "").replace("+", ""))
            except ValueError:
                return None

        # vs-50MA% is stored as a display string ("+3.4%"); parse each once per rerun
        # so the sort key, headline count, and table all read a number, not re-parse.
        vs50 = {t: _vs50f(t) for t in ta_signals}

        valid = []
        counts = {s: 0 for s in SIGNAL_ORDER}
        for t, sig in ta_signals.items():
            s = sig.get("signal", "N/A")
            counts[s] = counts.get(s, 0) + 1
            if s != "N/A":
                valid.append(t)

        # ── Mood: 5 count cards + distribution bar + headline ──
        cc = st.columns(5)
        for col, key, lbl in zip(cc, ["Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish"],
                                 ["↑↑ Strong Bull", "↑ Bullish", "→ Neutral", "↓ Bearish", "↓↓ Strong Bear"]):
            col.metric(lbl, counts.get(key, 0))
        dist = charts.signal_distribution_bar(counts)
        if dist:
            st.plotly_chart(dist, use_container_width=True, config={"displayModeBar": False})
        total = len(valid)
        if total:
            n_bull = counts["Strong Bullish"] + counts["Bullish"]
            n_bear = counts["Strong Bearish"] + counts["Bearish"]
            above50 = sum(1 for t in valid if (vs50[t] or 0) > 0)
            mood = "leans bullish" if n_bull > n_bear else ("leans bearish" if n_bear > n_bull else "is mixed")
            st.markdown(f"Portfolio **{mood}** — **{above50} of {total}** holdings trade above their 50-day average.")

        st.divider()

        # ── Controls: sort + how many ──
        sc1, sc2 = st.columns([2, 1])
        sort_by = sc1.selectbox("Sort bars by",
                                ["Most extreme (vs 50MA)", "Trend strength", "RSI"])
        show_all = sc2.toggle(f"Show all ({total})", value=False,
                              help="Off shows the ~16 most extreme; on shows every holding.")

        if sort_by.startswith("Most extreme"):
            keyed = sorted(valid, key=lambda t: (vs50[t] or 0.0))
        elif sort_by == "RSI":
            keyed = sorted(valid, key=lambda t: (ta_signals[t].get("rsi")
                           if pd.notna(ta_signals[t].get("rsi")) else 0.0))
        else:  # Trend strength — Strong Bear (bottom) → Strong Bull (top)
            keyed = sorted(valid, key=lambda t: -SIGNAL_ORDER.index(ta_signals[t].get("signal", "N/A")))

        if not show_all and len(keyed) > 16:
            order = keyed[:8] + keyed[-8:]   # bottom 8 + top 8 of the active sort
        else:
            order = keyed
        sub = {t: ta_signals[t] for t in order}

        st.caption("💡 Click any bar or table row to open that stock's detailed analysis.")
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("**Price vs 50-Day MA (%)**")
            f = charts.vs_50ma_bar(sub, order)
            if f:
                ev = st.plotly_chart(f, use_container_width=True, config={"displayModeBar": False},
                                     on_select="rerun", selection_mode="points", key="ta_vs50_chart")
                _go_to_detail(_plotly_clicked_ticker(ev), "_ta_vs50_last")
        with b2:
            st.markdown("**RSI (14-day)**")
            f = charts.rsi_bar(sub, order)
            if f:
                ev = st.plotly_chart(f, use_container_width=True, config={"displayModeBar": False},
                                     on_select="rerun", selection_mode="points", key="ta_rsi_chart")
                _go_to_detail(_plotly_clicked_ticker(ev), "_ta_rsi_last")

        # ── Searchable, sortable signal table (all holdings) ──
        st.divider()
        st.markdown("**All signals**")
        ta_q = st.text_input("Search ticker", key="ta_search", placeholder="e.g. RELIANCE")
        trows = [{"Ticker": t, "Trend": ta_signals[t]["label"],
                  "RSI": ta_signals[t]["rsi"], "vs 50MA (%)": vs50[t]} for t in valid]
        tdf = pd.DataFrame(trows).sort_values("vs 50MA (%)", ascending=False, na_position="last")
        if ta_q:
            tdf = tdf[tdf["Ticker"].str.contains(ta_q.strip().upper())]
        tdisp = tdf.copy()
        tdisp["RSI"] = tdisp["RSI"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
        tdisp["vs 50MA (%)"] = tdisp["vs 50MA (%)"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")

        def _trend_color(lbl):
            if "Bull" in lbl:
                return f"color: {GAIN}"
            if "Bear" in lbl:
                return f"color: {LOSS}"
            return f"color: {MUTED}"

        # "vs 50MA (%)" is a directional value column → reuse the shared sign-tint
        # styler (mint/coral by numeric sign, read off the aligned numeric `tdf`).
        tsty = _pnl_styler(tdisp, tdf, ["vs 50MA (%)"]).map(_trend_color, subset=["Trend"])
        tev = st.dataframe(tsty, width='stretch', hide_index=True,
                           height=min(45 + 36 * len(tdisp), 520),
                           on_select="rerun", selection_mode="single-row", key="ta_signal_table")
        _trows = list(tev.selection.rows) if (tev and tev.selection) else []
        if _trows and _trows[0] < len(tdf):
            _go_to_detail(tdf.iloc[_trows[0]]["Ticker"], "_ta_row_last")


# ═══ ANALYSTS ═════════════════════════════════════════════════════════════════
elif section == "🎯 Analysts":
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
elif section == "🧮 Tax":
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
elif section == "⚠️ Risk":
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
elif section == "💰 Dividends":
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


# ═══ EARNINGS CALENDAR ════════════════════════════════════════════════════════
elif section == "📅 Earnings Calendar":
    import calendar as _cal
    from datetime import date as _date
    st.subheader("Earnings Calendar")
    st.caption("Upcoming corporate events for your portfolio. Dates from Yahoo Finance; "
               "estimated and subject to company reschedules — information, not advice.")

    # Controls: view, watchlist toggle, type filters
    cc1, cc2 = st.columns([2, 2])
    with cc1:
        view = st.radio("View", ["List", "Monthly"], horizontal=True, label_visibility="collapsed")
    with cc2:
        incl_watch = st.toggle("Include watchlist stocks", value=False,
                               disabled=not st.session_state.watchlist)
    types_on = st.multiselect("Event types", earnings.EVENT_TYPES, default=earnings.EVENT_TYPES,
                              format_func=lambda t: f"{earnings.EVENT_META[t]['emoji']} {t}")

    # Symbol universe + name/website maps (portfolio always; watchlist optional)
    syms = list(holdings["Ticker"])
    names = dict(zip(holdings["Ticker"], holdings["Company"]))
    if incl_watch:
        for w in st.session_state.watchlist:
            if w not in names:
                syms.append(w)
                names[w] = w  # ponytail: ticker as name for watchlist; no extra meta fetch
    fundamentals = meta.get("fundamentals", {}) if load_meta else {}

    with st.spinner("Fetching corporate events…"):
        edates = md.fetch_earnings_events(tuple(syms), suffix_map)
    events = [e for e in earnings.build_events(syms, names, edates, fundamentals)
              if e.type in types_on]

    # Legend
    st.markdown(" ".join(f"{earnings.EVENT_META[t]['emoji']} {t}" for t in earnings.EVENT_TYPES))

    if not events:
        st.info("No upcoming corporate events found for these stocks. Yahoo Finance only "
                "publishes quarterly-results dates; earnings-call and presentation dates "
                "are not available from a free source yet.")
    elif view == "List":
        _STATUS_DOT = {"Upcoming": "🟢", "Today": "🟡", "Completed": "⚪"}
        rows = [{
            "When": e.when.strftime("%d %b %Y"),
            "Days": ("Today" if e.days_remaining == 0
                     else f"{e.days_remaining}d" if e.days_remaining > 0
                     else f"{-e.days_remaining}d ago"),
            "Status": f"{_STATUS_DOT.get(e.status, '')} {e.status}",
            "Event": f"{e.emoji} {e.type}",
            "Company": e.company, "Symbol": e.symbol, "Quarter": e.quarter,
        } for e in events]
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

        with st.expander("Event details"):
            pick = st.selectbox("Select an event",
                                [f"{e.emoji} {e.symbol} — {e.when.strftime('%d %b %Y')}" for e in events])
            e = events[[f"{x.emoji} {x.symbol} — {x.when.strftime('%d %b %Y')}" for x in events].index(pick)]
            st.markdown(f"**{e.company}** ({e.symbol})")
            st.markdown(f"- **Event:** {e.emoji} {e.type}")
            st.markdown(f"- **Date:** {e.when.strftime('%A, %d %B %Y')}")
            st.markdown(f"- **Quarter:** {e.quarter or '—'}")
            st.markdown(f"- **Status:** {e.status} ({e.days_remaining} days)")
            st.markdown(f"- {e.description}")
            if e.ir_url:
                st.markdown(f"- **Investor Relations:** [{e.ir_url}]({e.ir_url})")
    else:  # Monthly
        by_date = {}
        for e in events:
            by_date.setdefault(e.when, []).append(e)
        months = sorted({_date(d.year, d.month, 1) for d in by_date})
        msel = st.selectbox("Month", months, format_func=lambda m: m.strftime("%B %Y"))
        st.caption(f"{_cal.day_abbr[0]}–{_cal.day_abbr[6]} · Mon-first")
        grid = "<table style='width:100%;border-collapse:collapse;table-layout:fixed'>"
        grid += "<tr>" + "".join(
            f"<th style='padding:4px;color:{MUTED};font-weight:500'>{_cal.day_abbr[i]}</th>"
            for i in range(7)) + "</tr>"
        for week in _cal.Calendar(firstweekday=0).monthdatescalendar(msel.year, msel.month):
            grid += "<tr>"
            for day in week:
                dim = day.month != msel.month
                marks = "".join(ev.emoji for ev in by_date.get(day, []))
                fg = DISABLED if dim else TEXT
                grid += (f"<td style='border:1px solid {BORDER};vertical-align:top;height:64px;"
                         f"padding:4px;color:{fg}'>"
                         f"<div style='font-size:12px'>{day.day}</div>"
                         f"<div style='font-size:16px'>{marks}</div></td>")
            grid += "</tr>"
        grid += "</table>"
        st.markdown(grid, unsafe_allow_html=True)


# ═══ STOCK DETAIL ═════════════════════════════════════════════════════════════
elif section == "🔍 Stock Detail":
    st.subheader("Stock Detail")
    # Only stocks with live Yahoo data have charts/news/fundamentals
    detail_options = [t for t in holdings["Ticker"].tolist() if t in yahoo_eligible]

    # A click-through from the Technical tab lands here. If that stock has live
    # Yahoo data, preselect it; otherwise say why there's nothing to show.
    _goto = st.session_state.pop("_goto_ticker", None)
    if _goto and _goto not in detail_options:
        st.info(f"**{_goto}** has no live Yahoo market data (mutual fund, bond, or unresolved "
                "ticker), so there's no detailed analysis to show.")
        _goto = None

    if not detail_options:
        st.info("No live-priced equities to show detail for (mutual funds, bonds, and unresolved "
                "tickers don't have Yahoo market data).")
        pick = None
    else:
        if _goto:
            st.session_state["detail_pick"] = _goto
        pick = st.selectbox("Select a holding", detail_options, key="detail_pick")
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
elif section == "👁️ Watchlist":
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
            store.save_watchlist(st.session_state.watchlist)
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
        with st.expander("📋 Copy to TradingView"):
            st.caption("Copy, then paste into TradingView → Watchlist → ⋯ → Import list.")
            st.code(analytics.tradingview_list(wl, wsuffix, header="Watchlist"), language=None)
        rm_t = st.selectbox("Remove ticker", ["—"] + list(wl))
        if rm_t != "—" and st.button("Remove"):
            st.session_state.watchlist.remove(rm_t)
            store.save_watchlist(st.session_state.watchlist)
            st.rerun()


# ═══ REBALANCE ════════════════════════════════════════════════════════════════
elif section == "⚖️ Rebalance":
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
