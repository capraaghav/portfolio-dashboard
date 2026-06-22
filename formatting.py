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

def _is_missing(val) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    return False


def fmt_inr(val, short=False) -> str:
    if _is_missing(val):
        return "—"
    if short:
        if abs(val) >= 1e7:
            return f"₹{val/1e7:.2f} Cr"
        if abs(val) >= 1e5:
            return f"₹{val/1e5:.2f} L"
        if abs(val) >= 1e3:
            return f"₹{val/1e3:.1f} K"
    return f"₹{val:,.2f}"


def fmt_pct(val) -> str:
    if _is_missing(val):
        return "—"
    return f"{val:+.2f}%"


def fmt_num(val, decimals=2) -> str:
    if _is_missing(val):
        return "—"
    return f"{val:,.{decimals}f}"


def fmt_int(val) -> str:
    if _is_missing(val):
        return "—"
    return f"{int(val):,}"


def fmt_mcap(val) -> str:
    """Market cap in Indian crore."""
    if _is_missing(val) or val == 0:
        return "—"
    cr = val / 1e7
    if cr >= 1e5:
        return f"₹{cr/1e5:.2f} L Cr"
    return f"₹{cr:,.0f} Cr"
