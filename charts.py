"""Reusable Plotly figure builders. Each returns a figure; the app renders it."""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from formatting import SIGNAL_COLOR, REC_COLOR, GAIN, LOSS

_MARGIN = dict(t=50, b=10, l=10, r=10)


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
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=False, margin=_MARGIN)
    return fig


def pie_by_sector(chart_data: pd.DataFrame) -> go.Figure | None:
    if chart_data.empty:
        return None
    grp = (chart_data.groupby("Sector")["Current Value (₹)"].sum()
           .reset_index().sort_values("Current Value (₹)", ascending=False))
    fig = px.pie(grp, values="Current Value (₹)", names="Sector", title="By Sector",
                 hole=0.42, color_discrete_sequence=px.colors.qualitative.Pastel)
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
        color_continuous_scale=["#922b21", "#e74c3c", "#2c3e50", "#2ecc71", "#1a7a4a"],
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
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return fig


# ─── Technical ───────────────────────────────────────────────────────────────

def vs_50ma_bar(ta_signals: dict) -> go.Figure | None:
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
    df = pd.DataFrame(rows).sort_values("vs 50MA (%)")
    fig = px.bar(df, x="vs 50MA (%)", y="Ticker", orientation="h", color="Signal",
                 color_discrete_map=SIGNAL_COLOR, title="Price vs 50-Day Moving Average (%)",
                 height=max(350, len(df) * 18))
    fig.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.4)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.05),
                      margin=dict(t=60, b=20, l=10, r=20), yaxis=dict(tickfont=dict(size=10)))
    return fig


def rsi_bar(ta_signals: dict) -> go.Figure | None:
    rows = [{"Ticker": t, "RSI": s["rsi"], "Signal": s["signal"]}
            for t, s in ta_signals.items()
            if s.get("rsi") is not None and not (isinstance(s["rsi"], float) and np.isnan(s["rsi"]))]
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("RSI")
    fig = px.bar(df, x="RSI", y="Ticker", orientation="h", color="Signal",
                 color_discrete_map=SIGNAL_COLOR, title="RSI (14-day)",
                 height=max(350, len(df) * 18))
    fig.add_vline(x=70, line_dash="dot", line_color=LOSS,
                  annotation_text="Overbought (70)", annotation_position="top right")
    fig.add_vline(x=30, line_dash="dot", line_color=GAIN,
                  annotation_text="Oversold (30)", annotation_position="bottom right")
    fig.add_vline(x=50, line_dash="dash", line_color="white", opacity=0.3)
    fig.update_layout(showlegend=False, margin=dict(t=60, b=20, l=10, r=20),
                      xaxis=dict(range=[0, 100]), yaxis=dict(tickfont=dict(size=10)))
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
                             name="Portfolio Value", line=dict(color="#3498db", width=2.5),
                             fill="tozeroy", fillcolor="rgba(52,152,219,0.1)"))
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
                             name="My Portfolio", line=dict(color="#3498db", width=2.5)))
    if not bench_norm.empty:
        fig.add_trace(go.Scatter(x=bench_norm.index, y=bench_norm.values, mode="lines",
                                 name=bench_name, line=dict(color="#e67e22", width=2, dash="dash")))
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
                                 low=hist["Low"], close=hist["Close"], name=ticker))
    close = hist["Close"]
    if len(close) >= 50:
        fig.add_trace(go.Scatter(x=hist.index, y=close.rolling(50).mean(), name="SMA 50",
                                 line=dict(color="#f39c12", width=1.2)))
    if len(close) >= 200:
        fig.add_trace(go.Scatter(x=hist.index, y=close.rolling(200).mean(), name="SMA 200",
                                 line=dict(color="#9b59b6", width=1.2)))
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
               "bar": {"color": "#3498db"},
               "steps": [{"range": [low, low + (high - low) * 0.33], "color": "rgba(231,76,60,0.3)"},
                         {"range": [low + (high - low) * 0.33, low + (high - low) * 0.66], "color": "rgba(149,165,166,0.3)"},
                         {"range": [low + (high - low) * 0.66, high], "color": "rgba(46,204,113,0.3)"}]}))
    fig.update_layout(height=250, margin=dict(t=50, b=10, l=30, r=30))
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
