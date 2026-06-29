"""Unit tests for intelligence.py — the pure (no-I/O) detection engine.

Run from the repo root:

    python3 -m unittest tests.test_intelligence -v
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import intelligence as ie  # noqa: E402


def _holdings(rows):
    """Build a holdings-shaped DataFrame from minimal (ticker, value, ...) dicts."""
    base = {
        "Ticker": None, "Company": None, "Shares": 1.0, "Avg Cost (₹)": 100.0,
        "Live Price (₹)": 100.0, "Current Value (₹)": 0.0, "Cost Basis (₹)": 100.0,
        "Gain/Loss (₹)": 0.0, "Gain/Loss (%)": 0.0, "Sector": "Tech",
        "Accounts": "A", "_lt_shares": np.nan, "_first_buy": pd.NaT,
    }
    out = []
    for i, r in enumerate(rows):
        d = dict(base)
        d["Sector"] = f"Sec{i}"          # distinct sectors so sector-conc doesn't fire by default
        d.update(r)
        d["Company"] = d["Company"] or d["Ticker"]
        out.append(d)
    return pd.DataFrame(out)


def _ctx(holdings, **over):
    """Minimal context for a single detector under test."""
    totals = {"value": holdings["Current Value (₹)"].sum()}
    meta = {"fundamentals": over.get("fundamentals", {}),
            "analyst": over.get("analyst", {}),
            "names": {}, "sectors": {}}
    prices = over.get("prices", {r["Ticker"]: r["Live Price (₹)"]
                                 for _, r in holdings.iterrows()
                                 if not pd.isna(r["Live Price (₹)"])})
    raw = over.get("raw", pd.DataFrame(columns=["ticker", "shares", "avg_cost", "account", "ltp"]))
    ctx = ie.build_context(holdings, raw, prices, meta, totals,
                           over.get("ta", {}), over.get("quotes", {}))
    return ctx


class TestPortfolioRisk(unittest.TestCase):
    def test_concentration_fires_above_threshold(self):
        # BIG = 40% (high-severity single-name) amid 12 small diversified names,
        # so the single-position call is the kept (highest-severity) dimension.
        rows = [{"Ticker": "BIG", "Current Value (₹)": 400.0}]
        rows += [{"Ticker": f"T{i}", "Current Value (₹)": 50.0} for i in range(12)]
        out = ie.detect_portfolio_risk(_ctx(_holdings(rows)))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].category, "PORTFOLIO_RISK")
        self.assertIn("BIG", out[0].tickers)
        self.assertEqual(out[0].evidence["top1_ticker"], "BIG")

    def test_balanced_book_does_not_fire(self):
        h = _holdings([{"Ticker": f"T{i}", "Current Value (₹)": 100.0} for i in range(20)])
        self.assertEqual(ie.detect_portfolio_risk(_ctx(h)), [])


class TestTechnicalExtremes(unittest.TestCase):
    def test_overbought_fires(self):
        h = _holdings([{"Ticker": "HOT", "Current Value (₹)": 1000.0}])
        ta = {"HOT": {"signal": "Bullish", "rsi": 78.0}}
        out = ie.detect_technical_extremes(_ctx(h, ta=ta))
        self.assertEqual(len(out), 1)
        self.assertIn("HOT", out[0].tickers)

    def test_na_signal_skipped(self):
        h = _holdings([{"Ticker": "X", "Current Value (₹)": 1000.0}])
        ta = {"X": {"signal": "N/A", "rsi": np.nan}}
        self.assertEqual(ie.detect_technical_extremes(_ctx(h, ta=ta)), [])

    def test_normal_rsi_does_not_fire(self):
        h = _holdings([{"Ticker": "X", "Current Value (₹)": 1000.0}])
        ta = {"X": {"signal": "Bullish", "rsi": 55.0}}
        self.assertEqual(ie.detect_technical_extremes(_ctx(h, ta=ta)), [])


class TestOvervaluation(unittest.TestCase):
    def test_above_target_fires(self):
        h = _holdings([{"Ticker": "RICH", "Live Price (₹)": 200.0, "Current Value (₹)": 1000.0}])
        analyst = {"RICH": {"target_mean": 150.0, "n_analysts": 10}}
        out = ie.detect_overvaluation(_ctx(h, analyst=analyst))
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].evidence["flagged"][0]["above_target"])

    def test_too_few_analysts_skips_target(self):
        h = _holdings([{"Ticker": "X", "Live Price (₹)": 200.0, "Current Value (₹)": 1000.0}])
        analyst = {"X": {"target_mean": 150.0, "n_analysts": 1}}
        self.assertEqual(ie.detect_overvaluation(_ctx(h, analyst=analyst)), [])


class TestDataQuality(unittest.TestCase):
    def test_unpriced_fires(self):
        h = _holdings([
            {"Ticker": "P", "Live Price (₹)": 100.0, "Current Value (₹)": 100.0},
            {"Ticker": "U", "Live Price (₹)": np.nan, "Current Value (₹)": 50.0},
        ])
        out = ie.detect_data_quality(_ctx(h))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].evidence["n_unpriced"], 1)

    def test_all_priced_does_not_fire(self):
        h = _holdings([{"Ticker": "P", "Live Price (₹)": 100.0, "Current Value (₹)": 100.0}])
        self.assertEqual(ie.detect_data_quality(_ctx(h)), [])


class TestTodaysMove(unittest.TestCase):
    def test_move_from_quotes(self):
        h = _holdings([{"Ticker": "M", "Shares": 10.0, "Current Value (₹)": 1000.0}])
        quotes = {"M": {"day_chg": 5.0, "prev_close": 95.0}}
        out = ie.detect_todays_move(_ctx(h, quotes=quotes))
        self.assertEqual(len(out), 1)
        self.assertGreater(out[0].evidence["abs"], 0)


class TestRankingAndHealth(unittest.TestCase):
    def test_rank_sorts_and_dedups(self):
        a = ie.Insight("PORTFOLIO_RISK", "high", "t", "b", "⚠️ Risk", tickers=["X"])
        b = ie.Insight("TECHNICAL", "low", "t", "b", "🔬 Technical", tickers=["Y"])
        dup = ie.Insight("PORTFOLIO_RISK", "low", "t", "b", "⚠️ Risk", tickers=["X"])
        ranked = ie.rank([b, a, dup], top_n=5)
        self.assertEqual(ranked[0].category, "PORTFOLIO_RISK")  # high beats low
        self.assertEqual(len(ranked), 2)                        # dup dropped

    def test_health_score_in_range_and_explained(self):
        h = _holdings([{"Ticker": f"T{i}", "Current Value (₹)": 100.0} for i in range(15)])
        hs = ie.health_score(_ctx(h))
        self.assertTrue(0 <= hs.score <= 100)
        self.assertTrue(hs.band)
        self.assertEqual(round(sum(c.weight for c in hs.components), 2), 1.0)

    def test_analyze_empty_portfolio(self):
        res = ie.analyze(pd.DataFrame(), pd.DataFrame(), {}, {"fundamentals": {}, "analyst": {}},
                         {"value": 0}, {}, {})
        self.assertTrue(res["empty"])
        self.assertEqual(res["insights"], [])


class TestNoInventedEvidence(unittest.TestCase):
    """Every rendered body's numbers must come from real metrics — smoke check
    that detectors never fire on empty/missing data (the core honesty rule)."""

    def test_detectors_silent_on_missing_data(self):
        h = _holdings([{"Ticker": "X", "Live Price (₹)": 100.0, "Current Value (₹)": 100.0}])
        ctx = _ctx(h)  # no analyst, no ta, no quotes, balanced single position
        for det in (ie.detect_technical_extremes, ie.detect_overvaluation,
                    ie.detect_tax_loss_opportunity, ie.detect_todays_move):
            self.assertEqual(det(ctx), [], det.__name__)


if __name__ == "__main__":
    unittest.main()
