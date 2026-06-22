"""Formatting helpers and shared colour/label constants."""

from __future__ import annotations
import numpy as np
import pandas as pd

# ─── Colours & labels ─────────────────────────────────────────────────────────

GAIN = "#2ecc71"
LOSS = "#e74c3c"
MUTED = "#95a5a6"

SIGNAL_ORDER = ["Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish", "N/A"]
SIGNAL_COLOR = {
    "Strong Bullish": "#1a7a4a",
    "Bullish":        "#2ecc71",
    "Neutral":        "#95a5a6",
    "Bearish":        "#e74c3c",
    "Strong Bearish": "#922b21",
    "N/A":            "#555555",
}

REC_LABEL = {
    "strong_buy":   "Strong Buy",
    "buy":          "Buy",
    "hold":         "Hold",
    "underperform": "Underperform",
    "sell":         "Sell",
}
REC_COLOR = {
    "Strong Buy":   "#1a7a4a",
    "Buy":          "#2ecc71",
    "Hold":         "#f39c12",
    "Underperform": "#e74c3c",
    "Sell":         "#922b21",
    "—":            "#555555",
}

# ─── Number formatting (Indian lakh/crore conventions) ───────────────────────

def _num(val):
    """Coerce to a finite float, else None. Tolerates strings, NaN, inf, and the
    odd non-numeric value Yahoo Finance occasionally returns (e.g. a string P/E)."""
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, str):
        s = val.replace(",", "").replace("%", "").replace("₹", "").strip()
        try:
            val = float(s)
        except ValueError:
            return None
    try:
        f = float(val)
    except (ValueError, TypeError):
        return None
    return None if (np.isnan(f) or np.isinf(f)) else f


def _is_missing(val) -> bool:
    return _num(val) is None


def fmt_inr(val, short=False) -> str:
    v = _num(val)
    if v is None:
        return "—"
    if short:
        if abs(v) >= 1e7:
            return f"₹{v/1e7:.2f} Cr"
        if abs(v) >= 1e5:
            return f"₹{v/1e5:.2f} L"
        if abs(v) >= 1e3:
            return f"₹{v/1e3:.1f} K"
    return f"₹{v:,.2f}"


def fmt_pct(val) -> str:
    v = _num(val)
    return "—" if v is None else f"{v:+.2f}%"


def fmt_num(val, decimals=2) -> str:
    v = _num(val)
    return "—" if v is None else f"{v:,.{decimals}f}"


def fmt_int(val) -> str:
    v = _num(val)
    return "—" if v is None else f"{int(v):,}"


def fmt_mcap(val) -> str:
    """Market cap in Indian crore."""
    v = _num(val)
    if v is None or v == 0:
        return "—"
    cr = v / 1e7
    if cr >= 1e5:
        return f"₹{cr/1e5:.2f} L Cr"
    return f"₹{cr:,.0f} Cr"
