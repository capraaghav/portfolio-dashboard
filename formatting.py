"""Formatting helpers and shared colour/label constants."""

from __future__ import annotations
import numpy as np
import pandas as pd

# ─── Theme palette (dark, champagne-gold accent) ──────────────────────────────

GOLD = "#C9A87A"      # primary accent — brand, hero value, chart lines
GAIN = "#3DDC97"      # positive (mint green)
LOSS = "#F0564A"      # negative (coral red)
BG = "#0A0A0A"        # app background
SURFACE = "#141414"   # cards / panels (metric cards)
BORDER = "#262626"    # card borders / dividers (metric cards)
TEXT = "#EDEDED"      # primary text
MUTED = "#8B8B8B"     # secondary / labels
GRID = "#1F1F1F"      # chart gridlines

# ─── UI chrome ramp (dark tonal layering; single source for app.py CSS) ──────
# Depth comes from these lightness steps, not shadows. Kept here so the CSS block,
# charts, and components all read one palette. (config.toml necessarily repeats a
# few of these — Streamlit reads theme statically and can't import Python.)
SIDEBAR = "#0C0C0C"        # sidebar surface
PANEL = "#121212"          # container cards (charts/tables wrapper)
HOVER = "#161616"          # control / nav hover, secondary button bg
SELECTED = "#18170F"       # gold-tinted black — active nav row
SHIMMER = "#1F1F1F"        # skeleton-loader sweep highlight (== GRID)
BORDER_HAIRLINE = "#1C1C1C"  # dividers, sidebar edge, tab underline
BORDER_PANEL = "#232323"     # container-card border
BORDER_CONTROL = "#2A2A2A"   # button / control border
INK_SOFT = "#B9B9B9"       # nav label default
MUTED_DEEP = "#808080"     # tertiary text floor (AA-safe, 5.0:1 on BG)
DISABLED = "#555555"       # disabled glyphs / N-A (non-text only)

SIGNAL_ORDER = ["Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish", "N/A"]
SIGNAL_COLOR = {
    "Strong Bullish": "#1f9e6b",
    "Bullish":        GAIN,
    "Neutral":        MUTED,
    "Bearish":        LOSS,
    "Strong Bearish": "#a8362c",
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
    "Strong Buy":   "#1f9e6b",
    "Buy":          GAIN,
    "Hold":         GOLD,
    "Underperform": LOSS,
    "Sell":         "#a8362c",
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


def fmt_mcap(val) -> str:
    """Market cap in Indian crore."""
    v = _num(val)
    if v is None or v == 0:
        return "—"
    cr = v / 1e7
    if cr >= 1e5:
        return f"₹{cr/1e5:.2f} L Cr"
    return f"₹{cr:,.0f} Cr"
