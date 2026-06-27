import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
import numpy as np
import pandas as pd
import io

import analytics
import screener as scr


def _closes(n=200, trend="flat", base=100.0):
    """Generate synthetic close price series."""
    if trend == "flat":
        return pd.Series([base] * n, dtype=float)
    elif trend == "rising":
        return pd.Series([base + i * 0.5 for i in range(n)], dtype=float)
    elif trend == "falling":
        return pd.Series([base + 200 - i * 0.5 for i in range(n)], dtype=float)
    return pd.Series([base] * n, dtype=float)


def _metrics_row(ticker="ACME", price=100.0, sma10=100.5, sma50=100.0,
                  rsi=55.0, distance_pct=0.5, sma10_above=True,
                  wk52_high=120.0, wk52_low=80.0):
    return pd.DataFrame([{
        "ticker": ticker, "price": price, "sma10": sma10, "sma50": sma50,
        "rsi": rsi, "distance_pct": distance_pct, "sma10_above": sma10_above,
        "wk52_high": wk52_high, "wk52_low": wk52_low,
    }])


class TestCalculateSMA(unittest.TestCase):
    def test_sma10_correct(self):
        series = pd.Series(list(range(1, 21)), dtype=float)  # 1..20
        result = analytics.calculate_sma(series, 10)
        # last 10 values: 11..20, mean = 15.5
        self.assertAlmostEqual(result, 15.5)

    def test_too_short_returns_nan(self):
        series = pd.Series([1.0, 2.0, 3.0])
        result = analytics.calculate_sma(series, 10)
        self.assertTrue(np.isnan(result))


class TestCalculateScreeningMetrics(unittest.TestCase):
    def test_distance_pct_formula(self):
        # SMA10 = SMA50 when series is flat → distance = 0
        closes = _closes(200, "flat", 100.0)
        df, skipped = analytics.calculate_screening_metrics({"FLAT": closes})
        self.assertEqual(len(skipped), 0)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df.iloc[0]["distance_pct"], 0.0, places=2)

    def test_skips_short_series(self):
        closes = pd.Series([100.0] * 30)
        df, skipped = analytics.calculate_screening_metrics({"SHORT": closes})
        self.assertIn("SHORT", skipped)
        self.assertEqual(len(df), 0)

    def test_wk52_bounds(self):
        closes = pd.Series(list(range(50, 250)), dtype=float)  # 200 values: 50..249
        df, _ = analytics.calculate_screening_metrics({"RNG": closes})
        self.assertFalse(df.empty)
        row = df.iloc[0]
        self.assertGreaterEqual(row["wk52_high"], row["wk52_low"])
        self.assertLessEqual(row["wk52_low"], row["price"])

    def test_sma10_above_flag(self):
        # Rising series: recent prices higher → SMA10 > SMA50
        closes = _closes(200, "rising", 100.0)
        df, _ = analytics.calculate_screening_metrics({"RISING": closes})
        self.assertFalse(df.empty)
        self.assertTrue(df.iloc[0]["sma10_above"])


class TestSMAProximityRule(unittest.TestCase):
    def test_within_tolerance_matches(self):
        rule = scr.SMAProximityRule(tolerance_pct=1.0)
        df = _metrics_row(distance_pct=0.8, sma10_above=True)
        mask = rule.apply(df)
        self.assertTrue(mask.iloc[0])

    def test_outside_tolerance_excluded(self):
        rule = scr.SMAProximityRule(tolerance_pct=1.0)
        df = _metrics_row(distance_pct=1.5, sma10_above=True)
        mask = rule.apply(df)
        self.assertFalse(mask.iloc[0])

    def test_bullish_only_flag(self):
        rule = scr.SMAProximityRule(tolerance_pct=2.0, bullish_only=True)
        df_bear = _metrics_row(distance_pct=0.5, sma10_above=False)
        df_bull = _metrics_row(distance_pct=0.5, sma10_above=True)
        self.assertFalse(rule.apply(df_bear).iloc[0])
        self.assertTrue(rule.apply(df_bull).iloc[0])

    def test_classify_perfect_touch(self):
        rule = scr.SMAProximityRule()
        row = pd.Series({"distance_pct": 0.05, "sma10_above": True})
        self.assertEqual(rule.classify(row), "Perfect Touch")

    def test_classify_bullish_cross(self):
        rule = scr.SMAProximityRule()
        row = pd.Series({"distance_pct": 0.5, "sma10_above": True})
        self.assertEqual(rule.classify(row), "Bullish Cross")

    def test_classify_bullish_touch(self):
        rule = scr.SMAProximityRule()
        row = pd.Series({"distance_pct": 0.5, "sma10_above": False})
        self.assertEqual(rule.classify(row), "Bullish Touch")


class TestScreeningEngine(unittest.TestCase):
    def _base_df(self):
        return pd.DataFrame([
            {"ticker": "A", "price": 100.0, "sma10": 101.0, "sma50": 100.0,
             "rsi": 55.0, "distance_pct": 1.0, "sma10_above": True,
             "wk52_high": 120.0, "wk52_low": 80.0},
            {"ticker": "B", "price": 500.0, "sma10": 495.0, "sma50": 500.0,
             "rsi": 70.0, "distance_pct": 1.0, "sma10_above": False,
             "wk52_high": 600.0, "wk52_low": 400.0},
            {"ticker": "C", "price": 50.0, "sma10": 52.0, "sma50": 50.0,
             "rsi": 40.0, "distance_pct": 4.0, "sma10_above": True,
             "wk52_high": 70.0, "wk52_low": 30.0},
        ])

    def test_price_filter(self):
        engine = scr.ScreeningEngine()
        rule = scr.SMAProximityRule(tolerance_pct=5.0)
        result, _, _ = engine.run(self._base_df(), [rule], price_min=100.0)
        self.assertTrue((result["price"] >= 100.0).all())

    def test_rsi_filter(self):
        engine = scr.ScreeningEngine()
        rule = scr.SMAProximityRule(tolerance_pct=5.0)
        result, _, _ = engine.run(self._base_df(), [rule], rsi_min=50.0, rsi_max=65.0)
        self.assertTrue((result["rsi"] > 50.0).all())
        self.assertTrue((result["rsi"] < 65.0).all())

    def test_sort_by_distance_asc(self):
        engine = scr.ScreeningEngine()
        rule = scr.SMAProximityRule(tolerance_pct=5.0)
        result, _, _ = engine.run(self._base_df(), [rule])
        dists = result["distance_pct"].tolist()
        self.assertEqual(dists, sorted(dists))

    def test_empty_universe_returns_empty(self):
        engine = scr.ScreeningEngine()
        rule = scr.SMAProximityRule()
        empty = pd.DataFrame(columns=["ticker", "price", "sma10", "sma50", "rsi",
                                       "distance_pct", "sma10_above", "wk52_high", "wk52_low"])
        result, _, _ = engine.run(empty, [rule])
        self.assertTrue(result.empty)


class TestParseWatchlistUpload(unittest.TestCase):
    def test_strip_upper_dedupe(self):
        csv_bytes = b"symbol\nreliance\nRELIANCE\n  Reliance  \nTCS\n"
        syms, err = scr.parse_watchlist_upload(csv_bytes, "test.csv")
        self.assertEqual(err, "")
        self.assertIn("RELIANCE", syms)
        self.assertIn("TCS", syms)
        self.assertEqual(syms.count("RELIANCE"), 1)  # deduped

    def test_handles_column_aliases(self):
        for col in ["ticker", "stock", "security"]:
            csv_bytes = f"{col}\nINFY\nWIPRO\n".encode()
            syms, err = scr.parse_watchlist_upload(csv_bytes, "test.csv")
            self.assertEqual(err, "")
            self.assertIn("INFY", syms)

    def test_empty_file_returns_error(self):
        syms, err = scr.parse_watchlist_upload(b"symbol\n", "test.csv")
        self.assertNotEqual(err, "")
        self.assertEqual(syms, [])


if __name__ == "__main__":
    unittest.main()
