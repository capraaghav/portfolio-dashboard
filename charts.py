"""Reusable Plotly figure builders. Each returns a figure; the app renders it."""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from formatting import (SIGNAL_COLOR, SIGNAL_ORDER, REC_COLOR, GAIN, LOSS, GOLD, MUTED,
                        TEXT, BORDER, GRID, BG)

_MARGIN = dict(t=50, b=10, l=10, r=10)
_FONT = "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"

# Muted, on-brand qualitative palette (gold → green → teal → mauve → …)
_SEQ = [GOLD, GAIN, "#5BC0BE", "#B08FB0", "#D9A066", "#6FA8DC",
        "#C97A7A", "#8FB08F", "#A0826D", "#7AA5C9", "#C9B07A", "#9AA0A6"]

# Global dark theme applied to every figure (transparent bg, Inter font, muted grid)
_tmpl = go.layout.Template()
_tmpl.layout = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=_FONT, color=TEXT, size=13),
    title=dict(font=dict(family=_FONT, color=TEXT, size=15)),
    colorway=_SEQ,
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER, tickfont=dict(color=MUTED)),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER, tickfont=dict(color=MUTED)),
    legend=dict(font=dict(color=MUTED)),
    hoverlabel=dict(font=dict(family=_FONT)),
)
pio.templates["portfolio"] = _tmpl
pio.templates.default = "portfolio"


# ─── Allocation ───────────────────────────────────────────────────────────────

def pie_by_stock(chart_data: pd.DataFrame, top_n: int = 12) -> go.Figure | None:
    if chart_data.empty:
        return None
    top = chart_data.nlargest(top_n, "Current Value (₹)")
    others_val = chart_data["Current Value (₹)"].sum() - top["Current Value (₹)"].sum()
    top = top[["Ticker", "Current Value (₹)"]]
    if others_val > 0:
        top = pd.concat([top, pd.DataFrame([{
            "Ticker": f"Others ({len(chart_data) - top_n})",
            "Current Value (₹)": others_val,
        }])], ignore_index=True)
    fig = px.pie(top, values="Current Value (₹)", names="Ticker",
                 title=f"By Stock (top {min(top_n, len(chart_data))})", hole=0.42,
                 color_discrete_sequence=_SEQ)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=False, margin=_MARGIN)
    return fig


def pie_by_sector(chart_data: pd.DataFrame) -> go.Figure | None:
    if chart_data.empty:
        return None
    grp = (chart_data.groupby("Sector")["Current Value (₹)"].sum()
           .reset_index().sort_values("Current Value (₹)", ascending=False))
    fig = px.pie(grp, values="Current Value (₹)", names="Sector", title="By Sector",
                 hole=0.42, color_discrete_sequence=_SEQ)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, margin=_MARGIN)
    return fig


def treemap(holdings: pd.DataFrame) -> go.Figure | None:
    data = holdings.dropna(subset=["Current Value (₹)"]).copy()
    data = data[data["Current Value (₹)"] > 0]
    if data.empty:
        return None
    data["GL%"] = data["Gain/Loss (%)"].fillna(0)
    fig = px.treemap(
        data, path=[px.Constant("Portfolio"), "Sector", "Ticker"],
        values="Current Value (₹)", color="GL%",
        color_continuous_scale=["#a8362c", LOSS, "#2a2a2a", GAIN, "#1f9e6b"],
        color_continuous_midpoint=0, range_color=[-30, 30],
        custom_data=["Gain/Loss (%)", "Current Value (₹)"],
    )
    fig.update_traces(
        marker=dict(cornerradius=4),
        texttemplate="<b>%{label}</b><br>%{customdata[0]:+.1f}%",
        hovertemplate="<b>%{label}</b><br>Value: ₹%{value:,.0f}<br>P&L: %{customdata[0]:+.1f}%<extra></extra>",
    )
    fig.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=460,
                      coloraxis_colorbar=dict(title="P&L %"))
    return fig


def account_stacked(bar_data: pd.DataFrame) -> go.Figure | None:
    if bar_data.empty:
        return None
    fig = px.bar(bar_data, x="Account", y="Value", color="Ticker",
                 title="Holdings by Account", labels={"Value": "Current Value (₹)"},
                 color_discrete_sequence=_SEQ)
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return fig


# ─── Technical ───────────────────────────────────────────────────────────────

def vs_50ma_bar(ta_signals: dict, order: list | None = None) -> go.Figure | None:
    """Horizontal bar: each holding's price vs its 50-day MA. `order` (bottom→top
    ticker list) locks the row order so it matches the RSI chart row-for-row."""
    rows = []
    for t, sig in ta_signals.items():
        if sig.get("vs_50ma") is not None:
            try:
                rows.append({"Ticker": t,
                             "vs 50MA (%)": float(sig["vs_50ma"].replace("%", "").replace("+", "")),
                             "Signal": sig["signal"]})
            except ValueError:
                pass
    if not rows:
        return None
    df = pd.DataFrame(rows)
    fig = px.bar(df, x="Ticker", y="vs 50MA (%)", color="Signal",
                 color_discrete_map=SIGNAL_COLOR, height=440)
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.35)
    fig.update_layout(title_text="", showlegend=True,
                      legend=dict(orientation="h", y=1.08, x=0, title_text="", font=dict(size=11)),
                      margin=dict(t=12, b=10, l=10, r=10),
                      xaxis=dict(title_text="", tickangle=-90, tickfont=dict(size=9)),
                      yaxis=dict(title_text="", tickfont=dict(size=11)))
    if order:
        fig.update_xaxes(categoryorder="array", categoryarray=order)
    return fig


def rsi_bar(ta_signals: dict, order: list | None = None) -> go.Figure | None:
    """Horizontal RSI bars with shaded overbought (>70) / oversold (<30) zones.
    `order` matches vs_50ma_bar so the same ticker sits on the same row."""
    rows = [{"Ticker": t, "RSI": s["rsi"], "Signal": s["signal"]}
            for t, s in ta_signals.items()
            if s.get("rsi") is not None and not (isinstance(s["rsi"], float) and np.isnan(s["rsi"]))]
    if not rows:
        return None
    df = pd.DataFrame(rows)
    fig = px.bar(df, x="Ticker", y="RSI", color="Signal",
                 color_discrete_map=SIGNAL_COLOR, height=440)
    fig.add_hrect(y0=70, y1=100, fillcolor=LOSS, opacity=0.10, line_width=0,
                  annotation_text="Overbought", annotation_position="top left",
                  annotation_font=dict(size=10, color=LOSS))
    fig.add_hrect(y0=0, y1=30, fillcolor=GAIN, opacity=0.10, line_width=0,
                  annotation_text="Oversold", annotation_position="bottom left",
                  annotation_font=dict(size=10, color=GAIN))
    fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.25)
    fig.update_layout(title_text="", showlegend=False, margin=dict(t=12, b=10, l=10, r=10),
                      xaxis=dict(title_text="", tickangle=-90, tickfont=dict(size=9)),
                      yaxis=dict(title_text="", range=[0, 100], tickfont=dict(size=11)))
    if order:
        fig.update_xaxes(categoryorder="array", categoryarray=order)
    return fig


def signal_distribution_bar(counts: dict) -> go.Figure | None:
    """Single stacked horizontal bar: portfolio trend mix, bull→bear, by proportion."""
    seq = [s for s in SIGNAL_ORDER if s != "N/A"]   # bull→bear, excluding the N/A bucket
    present = [(s, counts.get(s, 0)) for s in seq if counts.get(s, 0) > 0]
    if not present:
        return None
    fig = go.Figure()
    for s, c in present:
        fig.add_bar(y=[""], x=[c], orientation="h", name=s,
                    marker=dict(color=SIGNAL_COLOR[s], line=dict(width=0)),
                    text=str(c), textposition="inside", insidetextanchor="middle",
                    textfont=dict(color=BG, size=12),
                    hovertemplate=f"{s}: {c}<extra></extra>")
    fig.update_layout(barmode="stack", height=58, showlegend=False, bargap=0,
                      title_text="", margin=dict(t=2, b=2, l=2, r=2),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


# ─── Analyst targets ─────────────────────────────────────────────────────────

def analyst_range(rng_df: pd.DataFrame) -> go.Figure | None:
    if rng_df.empty:
        return None
    rng_df = rng_df.sort_values("Mean %", ascending=True)
    colors = [REC_COLOR.get(c, "#95a5a6") for c in rng_df["Consensus"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Target range (low → high)", y=rng_df["Ticker"],
        x=rng_df["High %"] - rng_df["Low %"], base=rng_df["Low %"], orientation="h",
        marker_color=colors, marker_opacity=0.35,
        hovertemplate="<b>%{y}</b><br>Low: %{base:.1f}%<br>High: %{x:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(
        name="Mean target", y=rng_df["Ticker"], x=rng_df["Mean %"], mode="markers",
        marker=dict(symbol="diamond", size=8, color=colors, line=dict(width=1, color="white")),
        hovertemplate="<b>%{y}</b><br>Mean upside: %{x:.1f}%<extra></extra>"))
    fig.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.5,
                  annotation_text="Current price", annotation_position="top right")
    fig.update_layout(barmode="overlay", height=max(400, len(rng_df) * 20),
                      margin=dict(t=30, b=20, l=10, r=30), xaxis_title="% change from current price",
                      xaxis_ticksuffix="%", legend=dict(orientation="h", y=1.05),
                      yaxis=dict(tickfont=dict(size=10)))
    return fig


# ─── Performance ─────────────────────────────────────────────────────────────

def snapshot_line(snap_df: pd.DataFrame) -> go.Figure | None:
    if snap_df.empty or len(snap_df) < 1:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=snap_df["date"], y=snap_df["Total Value"], mode="lines+markers",
                             name="Portfolio Value", line=dict(color=GOLD, width=2.5),
                             fill="tozeroy", fillcolor="rgba(201,168,122,0.12)"))
    if snap_df["Total Cost"].notna().any():
        fig.add_trace(go.Scatter(x=snap_df["date"], y=snap_df["Total Cost"], mode="lines",
                                 name="Invested (cost)", line=dict(color=GAIN, width=1.5, dash="dot")))
    fig.update_layout(title="Portfolio Value Over Time", height=420,
                      margin=dict(t=50, b=20, l=10, r=10),
                      yaxis_title="₹", legend=dict(orientation="h", y=1.08), hovermode="x unified")
    return fig


def benchmark_overlay(port_norm: pd.Series, bench_norm: pd.Series, bench_name: str) -> go.Figure | None:
    if port_norm.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=port_norm.index, y=port_norm.values, mode="lines",
                             name="My Portfolio", line=dict(color=GOLD, width=2.5)))
    if not bench_norm.empty:
        fig.add_trace(go.Scatter(x=bench_norm.index, y=bench_norm.values, mode="lines",
                                 name=bench_name, line=dict(color="#7AA5C9", width=2, dash="dash")))
    fig.add_hline(y=100, line_dash="dot", line_color="white", opacity=0.3)
    fig.update_layout(title=f"Portfolio vs {bench_name} (rebased to 100)", height=420,
                      margin=dict(t=50, b=20, l=10, r=10), yaxis_title="Indexed (start = 100)",
                      legend=dict(orientation="h", y=1.08), hovermode="x unified")
    return fig


# ─── Per-stock detail ────────────────────────────────────────────────────────

def candlestick(hist: pd.DataFrame, ticker: str, avg_cost: float | None = None) -> go.Figure | None:
    if hist is None or hist.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"],
                                 low=hist["Low"], close=hist["Close"], name=ticker,
                                 increasing_line_color=GAIN, decreasing_line_color=LOSS))
    close = hist["Close"]
    if len(close) >= 50:
        fig.add_trace(go.Scatter(x=hist.index, y=close.rolling(50).mean(), name="SMA 50",
                                 line=dict(color=GOLD, width=1.2)))
    if len(close) >= 200:
        fig.add_trace(go.Scatter(x=hist.index, y=close.rolling(200).mean(), name="SMA 200",
                                 line=dict(color="#9AA0A6", width=1.2)))
    if avg_cost and not pd.isna(avg_cost):
        fig.add_hline(y=avg_cost, line_dash="dash", line_color=GAIN, opacity=0.7,
                      annotation_text=f"Avg cost ₹{avg_cost:,.0f}", annotation_position="bottom right")
    fig.update_layout(title=f"{ticker} — price history", height=460,
                      margin=dict(t=50, b=20, l=10, r=10), xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.08))
    return fig


def wk52_gauge(price: float, low: float, high: float) -> go.Figure | None:
    if not all([price, low, high]) or high <= low:
        return None
    pct = (price - low) / (high - low) * 100
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=price, number={"prefix": "₹", "valueformat": ",.0f"},
        title={"text": f"52-week range · {pct:.0f}% of band"},
        gauge={"axis": {"range": [low, high]},
               "bar": {"color": GOLD},
               "steps": [{"range": [low, low + (high - low) * 0.33], "color": "rgba(231,76,60,0.3)"},
                         {"range": [low + (high - low) * 0.33, low + (high - low) * 0.66], "color": "rgba(149,165,166,0.3)"},
                         {"range": [low + (high - low) * 0.66, high], "color": "rgba(46,204,113,0.3)"}]}))
    fig.update_layout(height=250, margin=dict(t=50, b=10, l=30, r=30))
    return fig


def health_gauge(score: int, band: str = "") -> go.Figure | None:
    """0–100 Portfolio Health gauge (gold bar, near-black track)."""
    if score is None:
        return None
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"color": GOLD, "size": 40}, "suffix": ""},
        title={"text": band, "font": {"color": MUTED, "size": 14}},
        gauge={"axis": {"range": [0, 100], "tickcolor": MUTED, "tickfont": {"color": MUTED}},
               "bar": {"color": GOLD},
               "bgcolor": "rgba(0,0,0,0)",
               "borderwidth": 0,
               "steps": [{"range": [0, 30], "color": "rgba(240,86,74,0.18)"},
                         {"range": [30, 50], "color": "rgba(149,165,166,0.15)"},
                         {"range": [50, 75], "color": "rgba(201,168,122,0.15)"},
                         {"range": [75, 100], "color": "rgba(61,220,151,0.18)"}]}))
    fig.update_layout(height=220, margin=dict(t=40, b=10, l=30, r=30))
    return fig


def dividend_history(divs: pd.Series) -> go.Figure | None:
    if divs is None or divs.empty:
        return None
    recent = divs[divs.index >= (pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365 * 5))]
    if recent.empty:
        recent = divs
    fig = px.bar(x=recent.index, y=recent.values, labels={"x": "", "y": "Dividend / share (₹)"},
                 title="Dividend history (last 5 yrs)")
    fig.update_traces(marker_color=GAIN)
    fig.update_layout(height=300, margin=dict(t=50, b=20, l=10, r=10))
    return fig
