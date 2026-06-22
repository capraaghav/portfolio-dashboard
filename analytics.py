"""Pure portfolio analytics — no I/O, no Streamlit. Easy to unit-test.

Covers: holdings consolidation, technical-indicator math, risk/concentration
metrics, Indian LTCG/STCG tax estimation, tax-loss harvesting, XIRR/CAGR,
and rebalancing drift.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

# Indian capital-gains rates on listed equity (post-23 Jul 2024 Budget).
# These are estimates for guidance only — verify against current law / your CA.
LTCG_RATE = 0.125          # 12.5% on long-term gains
LTCG_EXEMPTION = 125_000   # ₹1.25 lakh annual exemption
STCG_RATE = 0.20           # 20% on short-term gains
LT_HOLDING_DAYS = 365      # >12 months = long-term for listed equity


# ─── Technical indicators ─────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    if len(delta) < period:
        return np.nan
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    last_loss = loss.iloc[-1]
    if last_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + gain.iloc[-1] / last_loss)), 1)


def compute_signal(closes: pd.Series) -> dict:
    n = len(closes)
    if n < 20:
        return {"signal": "N/A", "label": "— N/A", "rsi": np.nan, "vs_50ma": None}
    price = closes.iloc[-1]
    sma20 = closes.rolling(20).mean().iloc[-1]
    sma50 = closes.rolling(50).mean().iloc[-1] if n >= 50 else None
    sma200 = closes.rolling(200).mean().iloc[-1] if n >= 200 else None
    rsi_val = rsi(closes)
    vs_50ma = ((price / sma50 - 1) * 100) if sma50 is not None else None

    if sma50 is not None:
        above = price > sma50
        if sma200 is not None:
            golden = sma50 > sma200
            if above and golden:
                sig, lbl = "Strong Bullish", "↑↑ Strong Bull"
            elif above:
                sig, lbl = "Bullish", "↑ Bullish"
            elif not above and not golden:
                sig, lbl = "Strong Bearish", "↓↓ Strong Bear"
            else:
                sig, lbl = "Bearish", "↓ Bearish"
        else:
            if abs(price - sma50) / sma50 < 0.02:
                sig, lbl = "Neutral", "→ Neutral"
            elif above:
                sig, lbl = "Bullish", "↑ Bullish"
            else:
                sig, lbl = "Bearish", "↓ Bearish"
    else:
        sig, lbl = ("Bullish", "↑ Bullish") if price > sma20 else ("Bearish", "↓ Bearish")

    return {
        "signal": sig,
        "label": lbl,
        "rsi": rsi_val,
        "vs_50ma": f"{vs_50ma:+.1f}%" if vs_50ma is not None else None,
    }


# ─── Holdings consolidation ───────────────────────────────────────────────────

def build_holdings(raw: pd.DataFrame, prices: dict, meta: dict) -> pd.DataFrame:
    """Consolidate raw per-account rows into one row per ticker."""
    rows = []
    for ticker, grp in raw.groupby("ticker"):
        total_shares = grp["shares"].sum()

        has_cost = "avg_cost" in grp.columns and grp["avg_cost"].notna().any()
        cost_basis = (grp["shares"] * grp["avg_cost"]).sum() if has_cost else np.nan
        avg_cost = cost_basis / total_shares if (total_shares > 0 and not np.isnan(cost_basis)) else np.nan

        live_price = prices.get(ticker)
        if live_price is None and "ltp" in grp.columns:
            live_price = grp["ltp"].dropna().mean() or None

        cur_val = total_shares * live_price if live_price is not None else np.nan
        # Fallback to the broker-reported value when we can't price it at all
        if (cur_val is None or (isinstance(cur_val, float) and np.isnan(cur_val))) and "current_value" in grp.columns:
            cv = grp["current_value"].sum()
            cur_val = cv if cv else np.nan
        pnl = (cur_val - cost_basis) if (not np.isnan(cur_val) and not np.isnan(cost_basis)) else np.nan
        pnl_pct = (pnl / cost_basis * 100) if (not np.isnan(pnl) and cost_basis > 0) else np.nan

        csv_sector = (
            grp["sector"].dropna().iloc[0].title()
            if "sector" in grp.columns and grp["sector"].notna().any()
            else None
        )
        sector = csv_sector or meta.get("sectors", {}).get(ticker, "Unknown")

        lt_shares = grp["qty_long_term"].sum() if "qty_long_term" in grp.columns else np.nan
        first_buy = (
            grp["purchase_date"].min()
            if "purchase_date" in grp.columns and grp["purchase_date"].notna().any()
            else pd.NaT
        )

        rows.append({
            "Ticker": ticker,
            "Company": meta.get("names", {}).get(ticker, ticker),
            "Shares": total_shares,
            "Avg Cost (₹)": avg_cost,
            "Live Price (₹)": live_price,
            "Current Value (₹)": cur_val,
            "Cost Basis (₹)": cost_basis,
            "Gain/Loss (₹)": pnl,
            "Gain/Loss (%)": pnl_pct,
            "Sector": sector,
            "Accounts": ", ".join(sorted(grp["account"].unique())),
            "_lt_shares": lt_shares,
            "_first_buy": first_buy,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Current Value (₹)", ascending=False, na_position="last")
    return df.reset_index(drop=True)


def portfolio_totals(holdings: pd.DataFrame) -> dict:
    tv = holdings["Current Value (₹)"].sum()
    tc = holdings["Cost Basis (₹)"].sum()
    pnl = holdings["Gain/Loss (₹)"].sum()
    return {
        "value": tv,
        "cost": tc,
        "pnl": pnl,
        "pnl_pct": (pnl / tc * 100) if tc > 0 else np.nan,
        "n_holdings": len(holdings),
    }


def per_account_breakdown(sub: pd.DataFrame, prices: dict, meta: dict) -> pd.DataFrame:
    """One row per account for a single ticker's slice of `raw`. Reuses
    build_holdings per account so the figures reconcile with the consolidated row."""
    rows = []
    for acct, grp in sub.groupby("account"):
        ah = build_holdings(grp, prices, meta)
        if ah.empty:
            continue
        r = ah.iloc[0]
        rows.append({
            "Account": acct,
            "Shares": r["Shares"],
            "Avg Cost (₹)": r["Avg Cost (₹)"],
            "Live Price (₹)": r["Live Price (₹)"],
            "Current Value (₹)": r["Current Value (₹)"],
            "Cost Basis (₹)": r["Cost Basis (₹)"],
            "Gain/Loss (₹)": r["Gain/Loss (₹)"],
            "Gain/Loss (%)": r["Gain/Loss (%)"],
        })
    return pd.DataFrame(rows)


# ─── Risk & concentration ─────────────────────────────────────────────────────

def risk_metrics(holdings: pd.DataFrame, fundamentals: dict | None = None) -> dict:
    vals = holdings["Current Value (₹)"].dropna()
    vals = vals[vals > 0]
    total = vals.sum()
    if total <= 0 or vals.empty:
        return {}

    weights = (vals / total).sort_values(ascending=False)
    hhi = float((weights ** 2).sum())                 # Herfindahl index (0–1)
    effective_n = 1.0 / hhi if hhi > 0 else np.nan    # effective number of holdings
    top5 = float(weights.head(5).sum() * 100)
    top1 = float(weights.iloc[0] * 100)
    largest_ticker = holdings.loc[weights.index[0], "Ticker"]

    sector_grp = (
        holdings.dropna(subset=["Current Value (₹)"])
        .groupby("Sector")["Current Value (₹)"]
        .sum()
        .sort_values(ascending=False)
    )
    top_sector = sector_grp.index[0] if len(sector_grp) else "—"
    top_sector_pct = float(sector_grp.iloc[0] / total * 100) if len(sector_grp) else np.nan

    # Weighted portfolio beta (only over stocks with a beta value)
    port_beta = np.nan
    if fundamentals:
        bw, bsum = 0.0, 0.0
        for _, row in holdings.iterrows():
            beta = (fundamentals.get(row["Ticker"]) or {}).get("beta")
            v = row["Current Value (₹)"]
            if beta is not None and not pd.isna(v) and v > 0:
                bw += beta * v
                bsum += v
        port_beta = (bw / bsum) if bsum > 0 else np.nan

    return {
        "hhi": hhi,
        "effective_n": effective_n,
        "top1_pct": top1,
        "top1_ticker": largest_ticker,
        "top5_pct": top5,
        "top_sector": top_sector,
        "top_sector_pct": top_sector_pct,
        "portfolio_beta": port_beta,
        "n_positions": len(vals),
    }


# ─── Indian capital-gains tax (unrealised, if-sold-today) ─────────────────────

def tax_breakdown(raw: pd.DataFrame, prices: dict, meta: dict) -> dict:
    """Split unrealised gains into long-term vs short-term and estimate tax.

    Uses the broker's 'Quantity Long Term' column when present. Otherwise falls
    back to purchase_date (>365 days = long-term). If neither exists, everything
    is treated as 'unknown term' and excluded from the tax estimate.
    """
    rows = []
    has_lt_col = "qty_long_term" in raw.columns
    has_dates = "purchase_date" in raw.columns
    now = pd.Timestamp.now()

    for ticker, grp in raw.groupby("ticker"):
        live = prices.get(ticker)
        if live is None and "ltp" in grp.columns:
            live = grp["ltp"].dropna().mean() or None
        if live is None:
            continue

        for _, r in grp.iterrows():
            shares = r.get("shares")
            avg = r.get("avg_cost")
            if pd.isna(shares) or pd.isna(avg):
                continue
            gain_per_share = live - avg

            lt_sh = st_sh = 0.0
            term_known = True
            if has_lt_col and not pd.isna(r.get("qty_long_term")):
                lt_sh = float(r["qty_long_term"])
                st_sh = float(shares) - lt_sh
            elif has_dates and not pd.isna(r.get("purchase_date")):
                age = (now - r["purchase_date"]).days
                if age >= LT_HOLDING_DAYS:
                    lt_sh = float(shares)
                else:
                    st_sh = float(shares)
            else:
                term_known = False

            rows.append({
                "ticker": ticker,
                "lt_gain": lt_sh * gain_per_share,
                "st_gain": st_sh * gain_per_share,
                "unknown_gain": (float(shares) * gain_per_share) if not term_known else 0.0,
                "term_known": term_known,
            })

    if not rows:
        return {}

    df = pd.DataFrame(rows)
    lt_gain = df["lt_gain"].sum()
    st_gain = df["st_gain"].sum()
    unknown_gain = df["unknown_gain"].sum()

    ltcg_taxable = max(0.0, lt_gain - LTCG_EXEMPTION)
    ltcg_tax = ltcg_taxable * LTCG_RATE
    stcg_tax = max(0.0, st_gain) * STCG_RATE

    return {
        "lt_gain": lt_gain,
        "st_gain": st_gain,
        "unknown_gain": unknown_gain,
        "ltcg_exemption_used": min(max(lt_gain, 0.0), LTCG_EXEMPTION),
        "ltcg_taxable": ltcg_taxable,
        "ltcg_tax": ltcg_tax,
        "stcg_tax": stcg_tax,
        "total_tax": ltcg_tax + stcg_tax,
        "term_resolved": bool(df["term_known"].any()),
        "all_unknown": not bool(df["term_known"].any()),
        "per_ticker": df.groupby("ticker")[["lt_gain", "st_gain", "unknown_gain"]].sum().reset_index(),
    }


def harvest_candidates(holdings: pd.DataFrame) -> pd.DataFrame:
    """Positions sitting at an unrealised loss — candidates for tax-loss harvesting."""
    losers = holdings[holdings["Gain/Loss (₹)"] < 0].copy()
    losers = losers.sort_values("Gain/Loss (₹)")
    return losers[["Ticker", "Company", "Shares", "Avg Cost (₹)", "Live Price (₹)",
                   "Current Value (₹)", "Gain/Loss (₹)", "Gain/Loss (%)"]]


# ─── XIRR / annualised return ─────────────────────────────────────────────────

def xirr(cashflows: list[tuple], guess: float = 0.1) -> float | None:
    """cashflows: list of (date, amount). Investments negative, value positive.
    Newton-Raphson; returns annualised rate as a fraction (0.15 = 15%)."""
    flows = [(pd.Timestamp(d), float(a)) for d, a in cashflows if a is not None]
    if len(flows) < 2:
        return None
    t0 = min(d for d, _ in flows)
    years = [(d - t0).days / 365.0 for d, _ in flows]
    amounts = [a for _, a in flows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    rate = guess
    for _ in range(100):
        denom = [(1 + rate) ** y for y in years]
        npv = sum(a / d for a, d in zip(amounts, denom))
        dnpv = sum(-y * a / (1 + rate) ** (y + 1) for a, y in zip(amounts, years))
        if abs(dnpv) < 1e-10:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-7:
            rate = new_rate
            break
        rate = new_rate
    return rate if -0.999 < rate < 100 else None


def portfolio_xirr(raw: pd.DataFrame, holdings: pd.DataFrame) -> float | None:
    """Annualised return using purchase dates as buy cashflows + today's value.
    Requires a purchase_date column; returns None otherwise."""
    if "purchase_date" not in raw.columns or raw["purchase_date"].isna().all():
        return None
    flows: list[tuple] = []
    for _, r in raw.iterrows():
        d = r.get("purchase_date")
        sh = r.get("shares")
        avg = r.get("avg_cost")
        if pd.isna(d) or pd.isna(sh) or pd.isna(avg):
            continue
        flows.append((d, -(sh * avg)))   # money out
    total_value = holdings["Current Value (₹)"].sum()
    if not flows or pd.isna(total_value) or total_value <= 0:
        return None
    flows.append((pd.Timestamp.now(), float(total_value)))  # money in (mark-to-market)
    return xirr(flows)


# ─── Synthetic portfolio backtest ─────────────────────────────────────────────

def synthetic_curve(closes: dict, shares_map: dict) -> pd.Series:
    """Value of *today's* share quantities over history. A backtest of the current
    basket — it ignores when you actually bought, so treat it as 'what if I'd held
    this exact basket the whole period'."""
    if not closes:
        return pd.Series(dtype=float)
    frames = []
    for ticker, series in closes.items():
        sh = shares_map.get(ticker)
        if sh and not series.empty:
            s = series.copy()
            s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
            frames.append(s.rename(ticker) * sh)
    if not frames:
        return pd.Series(dtype=float)
    mat = pd.concat(frames, axis=1).sort_index()
    mat = mat.ffill().dropna(how="all")
    return mat.sum(axis=1)


def normalize_to_100(series: pd.Series) -> pd.Series:
    series = series.dropna()
    if series.empty or series.iloc[0] == 0:
        return series
    return series / series.iloc[0] * 100


# ─── Rebalancing ──────────────────────────────────────────────────────────────

def rebalance_plan(holdings: pd.DataFrame, targets: dict) -> pd.DataFrame:
    """targets: {ticker: target_pct}. Returns drift and ₹ to trade per holding."""
    total = holdings["Current Value (₹)"].sum()
    rows = []
    for _, r in holdings.iterrows():
        t = r["Ticker"]
        cur_val = r["Current Value (₹)"]
        if pd.isna(cur_val):
            continue
        cur_pct = cur_val / total * 100 if total > 0 else 0
        tgt_pct = targets.get(t, cur_pct)
        tgt_val = total * tgt_pct / 100
        delta = tgt_val - cur_val
        rows.append({
            "Ticker": t,
            "Current %": cur_pct,
            "Target %": tgt_pct,
            "Drift %": cur_pct - tgt_pct,
            "Current Value (₹)": cur_val,
            "Target Value (₹)": tgt_val,
            "Action (₹)": delta,
        })
    return pd.DataFrame(rows)
