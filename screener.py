from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import numpy as np


class ScreeningRule(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def apply(self, metrics_df: pd.DataFrame) -> pd.Series:
        """Return boolean mask over metrics_df rows."""
        ...

    @abstractmethod
    def classify(self, row: pd.Series) -> str:
        """Return signal label string for a matched row."""
        ...


class SMAProximityRule(ScreeningRule):
    name = "SMA Proximity"
    description = "SMA 10 touching SMA 50 within tolerance %"

    def __init__(self, tolerance_pct: float = 1.0, bullish_only: bool = False):
        self.tolerance_pct = tolerance_pct
        self.bullish_only = bullish_only

    def apply(self, df: pd.DataFrame) -> pd.Series:
        mask = df["distance_pct"] <= self.tolerance_pct
        if self.bullish_only:
            mask = mask & df["sma10_above"]
        return mask

    def classify(self, row: pd.Series) -> str:
        if row["distance_pct"] <= 0.1:
            return "Perfect Touch"
        if row["sma10_above"]:
            return "Bullish Cross"
        return "Bullish Touch"


class ScreeningEngine:
    def run(
        self,
        metrics_df: pd.DataFrame,
        rules: list,
        price_min: float = 0,
        price_max: Optional[float] = None,
        rsi_min: float = 50,
        rsi_max: float = 65,
    ) -> "tuple[pd.DataFrame, int, int]":
        if metrics_df.empty:
            return metrics_df, 0, 0
        df = metrics_df.copy()
        df = df[df["price"] >= price_min]
        if price_max:
            df = df[df["price"] <= price_max]
        after_price = len(df)
        # primary: SMA rules
        for rule in rules:
            df = df[rule.apply(df)]
        rejected_sma = after_price - len(df)
        # secondary: RSI
        before_rsi = len(df)
        df = df[(df["rsi"] > rsi_min) & (df["rsi"] < rsi_max)]
        rejected_rsi = before_rsi - len(df)
        df = df.copy()
        if not df.empty and rules:
            df["signal"] = df.apply(rules[0].classify, axis=1)
        else:
            df["signal"] = ""
        return df.sort_values("distance_pct").reset_index(drop=True), rejected_sma, rejected_rsi


def parse_watchlist_upload(file_bytes: bytes, filename: str) -> "tuple[list[str], str]":
    """Parse an uploaded CSV/XLS/XLSX watchlist file. Returns (symbols, error_msg).
    Accepts columns: symbol, ticker, stock, nse_symbol, security (case-insensitive).
    Normalizes: strip, upper, deduplicate."""
    import io
    SYMBOL_COLS = {"symbol", "ticker", "stock", "nse_symbol", "security"}
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        return [], f"Could not parse file: {e}"
    if df.empty:
        return [], "File is empty"
    col_map = {c.lower().strip().replace(" ", "_"): c for c in df.columns}
    col = next((col_map[k] for k in SYMBOL_COLS if k in col_map), None)
    if col is None:
        col = df.columns[0]
    symbols = (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\.(NS|BO|NSE|BSE)$", "", regex=True)
        .unique()
        .tolist()
    )
    symbols = [s for s in symbols if s and len(s) <= 20 and s not in ("NAN", "NONE", "NULL", "TICKER", "SYMBOL", "STOCK")]
    if not symbols:
        return [], "No valid symbols found in file"
    return symbols, ""


def _demo():
    df = pd.DataFrame({
        "price": [100.0, 50.0, 200.0, 30.0],
        "rsi": [55.0, 80.0, 45.0, 50.0],
        "distance_pct": [0.05, 0.5, 2.0, 0.8],
        "sma10_above": [True, False, True, False],
    })
    out, _, _ = ScreeningEngine().run(df, [SMAProximityRule(tolerance_pct=1.0)], rsi_max=70)
    assert list(out["distance_pct"]) == [0.05, 0.8], out["distance_pct"].tolist()
    assert out.iloc[0]["signal"] == "Perfect Touch", out.iloc[0]["signal"]
    assert out.iloc[1]["signal"] == "Bullish Touch", out.iloc[1]["signal"]

    bull, _, _ = ScreeningEngine().run(df, [SMAProximityRule(tolerance_pct=1.0, bullish_only=True)], rsi_max=70)
    assert list(bull["distance_pct"]) == [0.05], bull["distance_pct"].tolist()

    syms, err = parse_watchlist_upload(b"symbol\nRELIANCE\ntcs.ns\nRELIANCE\n", "wl.csv")
    assert err == "", err
    assert syms == ["RELIANCE", "TCS"], syms

    _, err = parse_watchlist_upload(b"foo,bar\n1,2\n", "wl.csv")
    assert err == "", err
    print("ok")


if __name__ == "__main__":
    _demo()
