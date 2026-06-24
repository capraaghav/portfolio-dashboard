"""Unit tests for analytics.py — the pure (no-I/O) portfolio math.

Run from the repo root with the stdlib runner (no pytest needed):

    python3 -m unittest discover -s tests -v
    python3 -m unittest tests.test_analytics -v
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analytics  # noqa: E402


class TestRSI(unittest.TestCase):
    def test_all_gains_pins_to_100(self):
        # A monotonically rising series has zero average loss → RSI saturates at 100.
        s = pd.Series(range(1, 21), dtype=float)
        self.assertEqual(analytics.rsi(s), 100.0)

    def test_too_short_returns_nan(self):
        # Fewer diffs than `period` → undefined → NaN.
        s = pd.Series(range(1, 11), dtype=float)
        self.assertTrue(np.isnan(analytics.rsi(s, period=14)))


class TestComputeSignal(unittest.TestCase):
    def test_short_series_is_na(self):
        sig = analytics.compute_signal(pd.Series(range(10), dtype=float))
        self.assertEqual(sig["signal"], "N/A")
        self.assertIsNone(sig["vs_50ma"])

    def test_rising_basket_is_strong_bullish(self):
        # Price above SMA50, SMA50 above SMA200 (golden) → Strong Bullish.
        sig = analytics.compute_signal(pd.Series(range(1, 201), dtype=float))
        self.assertEqual(sig["signal"], "Strong Bullish")
        self.assertTrue(sig["vs_50ma"].startswith("+"))

    def test_falling_basket_is_strong_bearish(self):
        sig = analytics.compute_signal(pd.Series(range(200, 0, -1), dtype=float))
        self.assertEqual(sig["signal"], "Strong Bearish")


class TestBuildHoldings(unittest.TestCase):
    def _raw(self):
        # Same ticker held in two accounts at different cost.
        return pd.DataFrame([
            {"ticker": "ACME", "shares": 10, "avg_cost": 100.0, "account": "X"},
            {"ticker": "ACME", "shares": 10, "avg_cost": 200.0, "account": "Y"},
        ])

    def test_consolidates_across_accounts(self):
        h = analytics.build_holdings(self._raw(), {"ACME": 300.0}, {})
        self.assertEqual(len(h), 1)
        row = h.iloc[0]
        self.assertEqual(row["Shares"], 20)
        self.assertAlmostEqual(row["Avg Cost (₹)"], 150.0)        # weighted: 3000/20
        self.assertAlmostEqual(row["Cost Basis (₹)"], 3000.0)
        self.assertAlmostEqual(row["Current Value (₹)"], 6000.0)  # 20 * 300
        self.assertAlmostEqual(row["Gain/Loss (₹)"], 3000.0)
        self.assertAlmostEqual(row["Gain/Loss (%)"], 100.0)
        self.assertEqual(row["Accounts"], "X, Y")

    def test_unpriced_ticker_leaves_value_nan(self):
        h = analytics.build_holdings(self._raw(), {}, {})
        self.assertTrue(np.isnan(h.iloc[0]["Current Value (₹)"]))


class TestPortfolioTotals(unittest.TestCase):
    def test_totals_sum_and_pct(self):
        holdings = pd.DataFrame({
            "Current Value (₹)": [6000.0, 2000.0],
            "Cost Basis (₹)": [3000.0, 2500.0],
            "Gain/Loss (₹)": [3000.0, -500.0],
        })
        t = analytics.portfolio_totals(holdings)
        self.assertAlmostEqual(t["value"], 8000.0)
        self.assertAlmostEqual(t["cost"], 5500.0)
        self.assertAlmostEqual(t["pnl"], 2500.0)
        self.assertAlmostEqual(t["pnl_pct"], 2500.0 / 5500.0 * 100)
        self.assertEqual(t["n_holdings"], 2)


class TestRiskMetrics(unittest.TestCase):
    def _holdings(self):
        return pd.DataFrame({
            "Ticker": ["AAA", "BBB"],
            "Current Value (₹)": [6000.0, 2000.0],
            "Sector": ["Energy", "IT"],
        })

    def test_concentration_math(self):
        rm = analytics.risk_metrics(self._holdings())
        # weights 0.75 / 0.25 → HHI = 0.625, effective N = 1.6
        self.assertAlmostEqual(rm["hhi"], 0.625)
        self.assertAlmostEqual(rm["effective_n"], 1.6)
        self.assertAlmostEqual(rm["top1_pct"], 75.0)
        self.assertEqual(rm["top1_ticker"], "AAA")
        self.assertAlmostEqual(rm["top5_pct"], 100.0)
        self.assertEqual(rm["n_positions"], 2)

    def test_empty_returns_empty_dict(self):
        empty = pd.DataFrame({"Ticker": [], "Current Value (₹)": [], "Sector": []})
        self.assertEqual(analytics.risk_metrics(empty), {})

    def test_weighted_beta(self):
        rm = analytics.risk_metrics(self._holdings(),
                                    {"AAA": {"beta": 1.0}, "BBB": {"beta": 2.0}})
        # (1.0*6000 + 2.0*2000) / 8000 = 1.25
        self.assertAlmostEqual(rm["portfolio_beta"], 1.25)


class TestTaxBreakdown(unittest.TestCase):
    def test_long_term_column_split(self):
        raw = pd.DataFrame([
            {"ticker": "ACME", "shares": 10, "avg_cost": 100.0,
             "account": "X", "qty_long_term": 6},
        ])
        tax = analytics.tax_breakdown(raw, {"ACME": 200.0}, {})
        # gain/share = 100; LT 6→600, ST 4→400
        self.assertAlmostEqual(tax["lt_gain"], 600.0)
        self.assertAlmostEqual(tax["st_gain"], 400.0)
        self.assertAlmostEqual(tax["ltcg_tax"], 0.0)          # under ₹1.25L exemption
        self.assertAlmostEqual(tax["stcg_tax"], 80.0)         # 400 * 20%
        self.assertAlmostEqual(tax["total_tax"], 80.0)
        self.assertFalse(tax["all_unknown"])

    def test_no_term_info_is_all_unknown(self):
        raw = pd.DataFrame([
            {"ticker": "ACME", "shares": 10, "avg_cost": 100.0, "account": "X"},
        ])
        tax = analytics.tax_breakdown(raw, {"ACME": 200.0}, {})
        self.assertTrue(tax["all_unknown"])
        self.assertAlmostEqual(tax["unknown_gain"], 1000.0)

    def test_unpriced_ticker_skipped(self):
        raw = pd.DataFrame([
            {"ticker": "ACME", "shares": 10, "avg_cost": 100.0, "account": "X"},
        ])
        self.assertEqual(analytics.tax_breakdown(raw, {}, {}), {})


class TestHarvestCandidates(unittest.TestCase):
    def test_only_losers_returned(self):
        holdings = pd.DataFrame({
            "Ticker": ["WIN", "LOSE"], "Company": ["Win Co", "Lose Co"],
            "Shares": [1, 1], "Avg Cost (₹)": [100.0, 100.0],
            "Live Price (₹)": [150.0, 50.0],
            "Current Value (₹)": [150.0, 50.0],
            "Gain/Loss (₹)": [50.0, -50.0], "Gain/Loss (%)": [50.0, -50.0],
        })
        out = analytics.harvest_candidates(holdings)
        self.assertEqual(list(out["Ticker"]), ["LOSE"])


class TestXIRR(unittest.TestCase):
    def test_ten_percent_one_year(self):
        flows = [("2024-01-01", -1000.0), ("2025-01-01", 1100.0)]
        r = analytics.xirr(flows)
        self.assertAlmostEqual(r, 0.10, places=2)

    def test_single_flow_is_none(self):
        self.assertIsNone(analytics.xirr([("2024-01-01", -1000.0)]))

    def test_all_same_sign_is_none(self):
        self.assertIsNone(analytics.xirr([("2024-01-01", -1000.0),
                                          ("2025-01-01", -500.0)]))


class TestNormalizeTo100(unittest.TestCase):
    def test_rebases_first_point_to_100(self):
        out = analytics.normalize_to_100(pd.Series([200.0, 250.0, 300.0]))
        self.assertAlmostEqual(out.iloc[0], 100.0)
        self.assertAlmostEqual(out.iloc[1], 125.0)
        self.assertAlmostEqual(out.iloc[2], 150.0)


class TestRebalancePlan(unittest.TestCase):
    def test_drift_and_trade_amount(self):
        holdings = pd.DataFrame({
            "Ticker": ["AAA", "BBB"],
            "Current Value (₹)": [6000.0, 2000.0],
        })
        plan = analytics.rebalance_plan(holdings, {"AAA": 50.0, "BBB": 50.0})
        a = plan[plan["Ticker"] == "AAA"].iloc[0]
        self.assertAlmostEqual(a["Current %"], 75.0)
        self.assertAlmostEqual(a["Target %"], 50.0)
        self.assertAlmostEqual(a["Target Value (₹)"], 4000.0)
        self.assertAlmostEqual(a["Action (₹)"], -2000.0)   # sell ₹2000 of AAA


class TestSyntheticCurve(unittest.TestCase):
    def test_weights_shares_over_history(self):
        idx = pd.date_range("2024-01-01", periods=3)
        closes = {"AAA": pd.Series([100.0, 110.0, 120.0], index=idx)}
        curve = analytics.synthetic_curve(closes, {"AAA": 2})
        self.assertAlmostEqual(curve.iloc[0], 200.0)
        self.assertAlmostEqual(curve.iloc[-1], 240.0)

    def test_empty_closes_returns_empty(self):
        self.assertTrue(analytics.synthetic_curve({}, {"AAA": 2}).empty)


if __name__ == "__main__":
    unittest.main(verbosity=2)
