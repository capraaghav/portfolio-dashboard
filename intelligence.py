"""AI Portfolio Intelligence Engine — deterministic detection layer.

Pure computation, no I/O, no Streamlit (mirrors analytics.py). Turns existing
analytics output into ranked, evidence-backed insights + an explainable health
score. Every insight is produced by a deterministic detector over real metrics;
nothing here invents a conclusion. The optional natural-language layer
(ai_narrator.py, not required) only paraphrases the `body` strings produced here.

See product/EDS-ai-portfolio-intelligence.md for the full spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import analytics
from formatting import fmt_inr, fmt_pct

# ─── Tunables (single tuning surface — §15 thresholds, §14.5 weights) ─────────

TOP1_PCT = 25.0          # single-position concentration
TOP5_PCT = 60.0          # top-5 concentration
SECTOR_PCT = 35.0        # single-sector concentration
EFF_N_FLOOR = 5.0        # effective-holdings floor
BETA_HI, BETA_LO = 1.3, 0.7
RSI_HI, RSI_LO = 70.0, 30.0
WK52_NEAR = 0.98         # within 2% of 52-week high
OVER_TARGET = 0.10       # 10% above analyst mean target
OVER_PE_MULT = 1.5       # P/E vs sector-median multiple
MIN_ANALYSTS = 3
TAX_LOSS_MIN = 25_000.0  # ₹ harvestable loss worth surfacing
MOVE_NOTABLE = 3.0       # |day move %| to escalate
POS_WEIGHT_MIN = 5.0     # a position must be ≥5% of book to escalate severity

# priority = w_sev·sevW + w_mag·mag + w_conf·conf + w_fresh·fresh  (×100)
W_SEV, W_MAG, W_CONF, W_FRESH = 0.40, 0.30, 0.20, 0.10
_SEV_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


# ─── Models (§17) ─────────────────────────────────────────────────────────────

@dataclass
class Insight:
    category: str
    severity: str            # high | medium | low
    title: str
    body: str                # deterministic template prose (ground truth)
    section: str             # target nav label for "View in …"
    evidence: dict = field(default_factory=dict)
    tickers: list = field(default_factory=list)
    confidence: float = 1.0
    freshness: float = 1.0
    magnitude: float = 0.0   # 0..1, how far past threshold
    priority: float = 0.0

    @property
    def id(self) -> str:
        return f"{self.category}:{','.join(self.tickers)}"

    def score(self) -> float:
        self.priority = 100.0 * (
            W_SEV * _SEV_WEIGHT.get(self.severity, 0.3)
            + W_MAG * _clip01(self.magnitude)
            + W_CONF * _clip01(self.confidence)
            + W_FRESH * _clip01(self.freshness)
        )
        return self.priority


@dataclass
class HealthComponent:
    name: str
    subscore: float          # 0..100
    weight: float
    reason: str


@dataclass
class HealthScore:
    score: int               # 0..100
    band: str
    components: list


def _clip01(x: float) -> float:
    try:
        return float(min(1.0, max(0.0, x)))
    except (TypeError, ValueError):
        return 0.0


def _lin(x: float, best: float, worst: float) -> float:
    """Piecewise-linear map → 100 at `best`, 0 at `worst`, clamped."""
    if best == worst:
        return 100.0
    return float(min(100.0, max(0.0, (worst - x) / (worst - best) * 100.0)))


# ─── Context assembly (§14.3) ─────────────────────────────────────────────────

def _priced_coverage(holdings: pd.DataFrame) -> float:
    """Share of book *value* that is live-priced (proxy via non-null value)."""
    if holdings.empty:
        return 0.0
    vals = holdings["Current Value (₹)"]
    total = vals.sum()
    if not total or total <= 0:
        return 0.0
    priced = holdings.loc[holdings["Live Price (₹)"].notna(), "Current Value (₹)"].sum()
    return _clip01(priced / total)


def _day_move(holdings: pd.DataFrame, quotes: dict) -> dict:
    """Today's move from quotes × shares. Pure — quotes is a plain dict."""
    shares = dict(zip(holdings["Ticker"], holdings["Shares"]))
    abs_chg = prev = 0.0
    per = []
    for t, q in (quotes or {}).items():
        dc, pc = q.get("day_chg"), q.get("prev_close")
        sh = shares.get(t) or 0
        if dc is not None and pc and sh:
            abs_chg += sh * dc
            prev += sh * pc
            per.append((t, dc / pc * 100 if pc else 0.0))
    pct = (abs_chg / prev * 100) if prev > 0 else None
    per.sort(key=lambda x: x[1])
    return {
        "abs": abs_chg,
        "pct": pct,
        "top_loser": per[0] if per else None,
        "top_gainer": per[-1] if per else None,
    }


def _sector_pe_median(holdings: pd.DataFrame, fundamentals: dict) -> dict:
    """Median trailing P/E per sector across the user's own holdings."""
    rows = []
    for _, r in holdings.iterrows():
        pe = (fundamentals.get(r["Ticker"]) or {}).get("pe")
        if pe and pe > 0:
            rows.append((r["Sector"], pe))
    if not rows:
        return {}
    df = pd.DataFrame(rows, columns=["sector", "pe"])
    return df.groupby("sector")["pe"].median().to_dict()


def build_context(holdings, raw, prices, meta, totals, ta_signals, quotes) -> dict:
    fundamentals = meta.get("fundamentals", {}) or {}
    analyst = meta.get("analyst", {}) or {}
    total_val = totals.get("value") or 0.0

    def weight_pct(ticker) -> float:
        row = holdings.loc[holdings["Ticker"] == ticker, "Current Value (₹)"]
        v = row.iloc[0] if len(row) else np.nan
        return (v / total_val * 100) if (total_val > 0 and not pd.isna(v)) else 0.0

    return {
        "holdings": holdings,
        "raw": raw,
        "prices": prices,
        "meta": meta,
        "totals": totals,
        "fundamentals": fundamentals,
        "analyst": analyst,
        "ta": ta_signals or {},
        "rm": analytics.risk_metrics(holdings, fundamentals) or {},
        "move": _day_move(holdings, quotes),
        "tax": analytics.tax_breakdown(raw, prices, meta) or {},
        "harvest": analytics.harvest_candidates(holdings),
        "sector_pe": _sector_pe_median(holdings, fundamentals),
        "coverage": _priced_coverage(holdings),
        "weight_pct": weight_pct,
    }


# ─── Detectors (§15). Each is pure: (ctx) -> list[Insight] ────────────────────

def detect_portfolio_risk(ctx) -> list:
    rm = ctx["rm"]
    if not rm:
        return []
    conf = ctx["coverage"]
    cands = []  # (severity, magnitude, title, body, evidence)

    if rm.get("top1_pct", 0) >= TOP1_PCT:
        p = rm["top1_pct"]
        sev = "high" if p >= 35 else "medium"
        cands.append((sev, _clip01((p - TOP1_PCT) / 25),
            f"{rm['top1_ticker']} is {p:.0f}% of your book",
            f"Your largest position, {rm['top1_ticker']}, is {p:.1f}% of portfolio value. "
            f"A single name above {TOP1_PCT:.0f}% raises single-stock risk.",
            {"top1_ticker": rm["top1_ticker"], "top1_pct": round(p, 1), "threshold": TOP1_PCT}))

    if rm.get("top5_pct", 0) >= TOP5_PCT:
        p = rm["top5_pct"]
        sev = "high" if p >= 75 else "medium"
        cands.append((sev, _clip01((p - TOP5_PCT) / 30),
            f"Top 5 positions are {p:.0f}% of your book",
            f"Your five largest holdings make up {p:.1f}% of portfolio value — most of your "
            f"risk sits in a handful of names.",
            {"top5_pct": round(p, 1), "threshold": TOP5_PCT}))

    if rm.get("top_sector_pct", 0) >= SECTOR_PCT:
        p = rm["top_sector_pct"]
        cands.append(("medium", _clip01((p - SECTOR_PCT) / 30),
            f"{rm['top_sector']} is {p:.0f}% of your book",
            f"The {rm['top_sector']} sector is {p:.1f}% of portfolio value — a sector shock "
            f"would move your book sharply.",
            {"top_sector": rm["top_sector"], "top_sector_pct": round(p, 1), "threshold": SECTOR_PCT}))

    eff, n = rm.get("effective_n", 99), rm.get("n_positions", 0)
    if eff < max(EFF_N_FLOOR, 0.25 * n):
        cands.append(("medium", _clip01((max(EFF_N_FLOOR, 0.25 * n) - eff) / EFF_N_FLOOR),
            "Diversification is thinner than it looks",
            f"You hold {n} positions but their effective number is only {eff:.0f} — value is "
            f"concentrated in a few names.",
            {"effective_n": round(eff, 1), "n_positions": n}))

    beta = rm.get("portfolio_beta")
    if beta is not None and not pd.isna(beta) and (beta >= BETA_HI or beta <= BETA_LO):
        hi = beta >= BETA_HI
        cands.append(("low", _clip01(abs(beta - 1.0) / 0.6),
            f"Portfolio beta is {beta:.2f}",
            f"Your value-weighted beta is {beta:.2f} — the book is "
            f"{'more' if hi else 'less'} volatile than the index.",
            {"portfolio_beta": round(beta, 2)}))

    if not cands:
        return []
    # Keep the single highest-magnitude concentration call (avoid stacking).
    cands.sort(key=lambda c: (_SEV_WEIGHT[c[0]], c[1]), reverse=True)
    sev, mag, title, body, ev = cands[0]
    ins = Insight("PORTFOLIO_RISK", sev, title, body, "⚠️ Risk", ev,
                  tickers=[rm.get("top1_ticker")] if "top1_ticker" in ev else [],
                  confidence=conf, magnitude=mag)
    return [ins]


def detect_technical_extremes(ctx) -> list:
    ta, fund, wp = ctx["ta"], ctx["fundamentals"], ctx["weight_pct"]
    prices = ctx["prices"]
    overbought = []
    for t, sig in ta.items():
        if sig.get("signal") in (None, "N/A"):
            continue
        rsi = sig.get("rsi")
        if rsi is None or pd.isna(rsi):
            continue
        price = prices.get(t)
        wk_hi = (fund.get(t) or {}).get("wk52_high")
        near_hi = bool(price and wk_hi and price >= WK52_NEAR * wk_hi)
        if rsi >= RSI_HI:
            overbought.append({"ticker": t, "rsi": round(float(rsi), 0),
                               "near_52w_high": near_hi, "weight_pct": round(wp(t), 1)})
    if not overbought:
        return []
    overbought.sort(key=lambda d: d["rsi"], reverse=True)
    tickers = [d["ticker"] for d in overbought]
    at_highs = [d for d in overbought if d["near_52w_high"]]
    big = any(d["weight_pct"] >= POS_WEIGHT_MIN for d in overbought)
    sev = "medium" if (at_highs and big) else "low"
    names = ", ".join(f"{d['ticker']} (RSI {d['rsi']:.0f}"
                      f"{', at 52-wk high' if d['near_52w_high'] else ''})" for d in overbought[:4])
    n_ob = len(overbought)
    title = (f"{n_ob} holding{'s look' if n_ob > 1 else ' looks'} technically stretched")
    body = f"Overbought on RSI: {names}. Strong runs, but extended on the technicals."
    mag = _clip01((max(d["rsi"] for d in overbought) - RSI_HI) / 30)
    return [Insight("TECHNICAL", sev, title, body, "🔬 Technical",
                    {"overbought": overbought, "rsi_threshold": RSI_HI},
                    tickers=tickers, confidence=1.0, magnitude=mag)]


def detect_overvaluation(ctx) -> list:
    holdings, analyst, fund = ctx["holdings"], ctx["analyst"], ctx["fundamentals"]
    prices, sector_pe, wp = ctx["prices"], ctx["sector_pe"], ctx["weight_pct"]
    flagged = []
    for _, r in holdings.iterrows():
        t = r["Ticker"]
        price = prices.get(t)
        if not price:
            continue
        a = analyst.get(t) or {}
        f = fund.get(t) or {}
        tgt, n_an = a.get("target_mean"), a.get("n_analysts")
        pe = f.get("pe")
        above_target = bool(tgt and n_an and n_an >= MIN_ANALYSTS and price > tgt * (1 + OVER_TARGET))
        sec_med = sector_pe.get(r["Sector"])
        rich_pe = bool(pe and sec_med and pe > sec_med * OVER_PE_MULT)
        if above_target or rich_pe:
            flagged.append({
                "ticker": t, "weight_pct": round(wp(t), 1),
                "price": round(price, 1), "target_mean": round(tgt, 1) if tgt else None,
                "upside_pct": round((tgt / price - 1) * 100, 1) if tgt else None,
                "pe": round(pe, 1) if pe else None, "sector_pe": round(sec_med, 1) if sec_med else None,
                "above_target": above_target, "rich_pe": rich_pe,
            })
    if not flagged:
        return []
    flagged.sort(key=lambda d: d["weight_pct"], reverse=True)
    tickers = [d["ticker"] for d in flagged]
    both = any(d["above_target"] and d["rich_pe"] for d in flagged)
    big = any(d["weight_pct"] >= POS_WEIGHT_MIN for d in flagged)
    sev = "medium" if (both or big) else "low"
    lead = flagged[0]
    bits = []
    if lead["above_target"]:
        bits.append(f"trades {abs(lead['upside_pct']):.0f}% above the analyst mean target of "
                    f"{fmt_inr(lead['target_mean'])}")
    if lead["rich_pe"]:
        bits.append(f"carries a P/E of {lead['pe']:.0f} versus a sector median near {lead['sector_pe']:.0f}")
    extra = f" ({len(flagged) - 1} more flagged)" if len(flagged) > 1 else ""
    title = f"{lead['ticker']} looks richly valued"
    body = f"{lead['ticker']} {' and '.join(bits)}. The market is pricing it richly{extra}."
    return [Insight("OVERVALUATION", sev, title, body, "🎯 Analysts",
                    {"flagged": flagged}, tickers=tickers, confidence=1.0,
                    magnitude=_clip01(len(flagged) / 5))]


def detect_tax_loss_opportunity(ctx) -> list:
    harvest, tax = ctx["harvest"], ctx["tax"]
    if harvest is None or harvest.empty:
        return []
    loss = float(harvest["Gain/Loss (₹)"].sum())  # negative
    if -loss < TAX_LOSS_MIN:
        return []
    has_gains = bool(tax) and (tax.get("lt_gain", 0) > 0 or tax.get("st_gain", 0) > 0)
    n = len(harvest)
    title = f"{fmt_inr(abs(loss))} of harvestable losses across {n} position{'s' if n > 1 else ''}"
    body = (f"{n} holding{'s sit' if n > 1 else ' sits'} at an unrealised loss totalling "
            f"{fmt_inr(abs(loss))}"
            + (". You also have unrealised gains, so booking some losses could offset taxable gains. "
               if has_gains else ". ")
            + "Estimate only — not tax advice.")
    return [Insight("TAX_LOSS", "medium", title, body, "🧮 Tax",
                    {"harvestable_loss": round(loss, 0), "n": n, "has_gains": has_gains},
                    tickers=list(harvest["Ticker"].head(5)), confidence=ctx["coverage"],
                    magnitude=_clip01(-loss / (TAX_LOSS_MIN * 4)))]


def detect_todays_move(ctx) -> list:
    m = ctx["move"]
    pct = m.get("pct")
    if pct is None:
        return []
    sev = "low" if abs(pct) >= MOVE_NOTABLE else "low"
    g, l = m.get("top_gainer"), m.get("top_loser")
    driver = ""
    if abs(pct) >= 0.1 and g and l:
        lead = g if pct >= 0 else l
        driver = f", led by {lead[0]} ({lead[1]:+.1f}%)"
    title = f"Your book moved {fmt_pct(pct)} today"
    body = f"Portfolio value changed {fmt_inr(m['abs'])} ({fmt_pct(pct)}) today{driver}."
    return [Insight("TODAYS_MOVE", sev, title, body, "📈 Performance",
                    {"abs": round(m["abs"], 0), "pct": round(pct, 2),
                     "top_gainer": g, "top_loser": l},
                    tickers=[g[0]] if g else [], confidence=1.0,
                    magnitude=_clip01(abs(pct) / 6))]


def detect_data_quality(ctx) -> list:
    holdings = ctx["holdings"]
    n_total = len(holdings)
    if n_total == 0:
        return []
    n_unpriced = int(holdings["Live Price (₹)"].isna().sum())
    if n_unpriced == 0:
        return []
    cov = ctx["coverage"]
    title = f"{n_unpriced} of {n_total} holdings have no live price"
    body = (f"{n_unpriced} holding{'s are' if n_unpriced > 1 else ' is'} valued from your file, not "
            f"live data. Insights cover the {n_total - n_unpriced} priced holding"
            f"{'s' if n_total - n_unpriced != 1 else ''}; treat the rest as approximate.")
    return [Insight("DATA_QUALITY", "low", title, body, "📋 Holdings",
                    {"n_unpriced": n_unpriced, "n_total": n_total, "coverage": round(cov, 2)},
                    tickers=[], confidence=1.0, magnitude=_clip01(n_unpriced / n_total))]


DETECTORS = [
    detect_portfolio_risk,
    detect_technical_extremes,
    detect_overvaluation,
    detect_tax_loss_opportunity,
    detect_todays_move,
    detect_data_quality,
]


def detect_all(ctx) -> list:
    out = []
    for det in DETECTORS:
        try:
            out.extend(det(ctx) or [])
        except Exception:
            # A detector must never crash the engine (NFR-2). Skip and continue.
            continue
    return out


def rank(insights: list, top_n: int = 5) -> list:
    seen = set()
    ranked = []
    for ins in sorted(insights, key=lambda i: i.score(), reverse=True):
        key = (ins.category, tuple(ins.tickers))
        if key in seen:
            continue
        seen.add(key)
        ranked.append(ins)
    return ranked[:top_n]


# ─── Portfolio Health Score (§16) ─────────────────────────────────────────────

def health_score(ctx) -> HealthScore:
    rm = ctx["rm"]
    fund, holdings = ctx["fundamentals"], ctx["holdings"]
    analyst, prices, sector_pe = ctx["analyst"], ctx["prices"], ctx["sector_pe"]
    total_val = ctx["totals"].get("value") or 0.0
    comps = []

    # Diversification (top1 + effective_n), 0.30
    top1 = rm.get("top1_pct", 100.0)
    eff = rm.get("effective_n", 1.0)
    div = (_lin(top1, best=10, worst=40) + _lin(-eff, best=-15, worst=-2)) / 2
    comps.append(HealthComponent("Diversification", div, 0.30,
        f"Largest {top1:.0f}%, effective holdings {eff:.0f}"))

    # Sector balance, 0.20
    sec = rm.get("top_sector_pct", 100.0)
    comps.append(HealthComponent("Sector balance", _lin(sec, best=20, worst=60), 0.20,
        f"{rm.get('top_sector', '—')} is {sec:.0f}% of book"))

    # Valuation — share of book value that is stretched, 0.20
    stretched_val = 0.0
    for _, r in holdings.iterrows():
        t, price = r["Ticker"], prices.get(r["Ticker"])
        v = r["Current Value (₹)"]
        if not price or pd.isna(v):
            continue
        a, f = analyst.get(t) or {}, ctx["fundamentals"].get(t) or {}
        tgt, n_an, pe = a.get("target_mean"), a.get("n_analysts"), f.get("pe")
        sec_med = sector_pe.get(r["Sector"])
        if (tgt and n_an and n_an >= MIN_ANALYSTS and price > tgt * (1 + OVER_TARGET)) \
                or (pe and sec_med and pe > sec_med * OVER_PE_MULT):
            stretched_val += v
    stretched_pct = (stretched_val / total_val * 100) if total_val > 0 else 0.0
    comps.append(HealthComponent("Valuation", _lin(stretched_pct, best=0, worst=50), 0.20,
        f"{stretched_pct:.0f}% of book trades rich"))

    # Volatility (beta), 0.15
    beta = rm.get("portfolio_beta")
    if beta is None or pd.isna(beta):
        vol = 75.0
        vol_reason = "beta unavailable"
    else:
        vol = _lin(abs(beta - 0.95), best=0.15, worst=0.65)
        vol_reason = f"beta {beta:.2f}"
    comps.append(HealthComponent("Volatility", vol, 0.15, vol_reason))

    # Data quality, 0.15
    cov = ctx["coverage"] * 100
    comps.append(HealthComponent("Data quality", _lin(cov, best=100, worst=50), 0.15,
        f"{cov:.0f}% live-priced"))

    score = round(sum(c.subscore * c.weight for c in comps))
    band = ("Resilient" if score >= 75 else "Balanced" if score >= 50
            else "Watchful" if score >= 30 else "Fragile")
    return HealthScore(int(score), band, comps)


# ─── Public entry point ───────────────────────────────────────────────────────

def analyze(holdings, raw, prices, meta, totals, ta_signals, quotes, top_n: int = 5) -> dict:
    """Run the full deterministic pipeline. Returns insights + health + move.

    Pure: callers pass already-fetched data; no I/O happens here.
    """
    empty = (holdings is None or holdings.empty
             or not (totals.get("value") or 0) > 0)
    if empty:
        return {"insights": [], "health": None, "move": {}, "empty": True}
    ctx = build_context(holdings, raw, prices, meta, totals, ta_signals, quotes)
    insights = rank(detect_all(ctx), top_n=top_n)
    return {
        "insights": insights,
        "health": health_score(ctx),
        "move": ctx["move"],
        "empty": False,
    }
