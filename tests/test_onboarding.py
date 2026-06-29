"""Onboarding sample-data tests — the bundled demo must parse into the canonical
schema and drive the analytics + intelligence pipeline end to end (no network).

Run: python3 -m unittest tests.test_onboarding -v
"""

import io
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analytics  # noqa: E402
import intelligence  # noqa: E402
from parsers import parse_all  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_SAMPLE = _ROOT / "data" / "sample"
_DEMO_FILES = [("demo_long_term.csv", "Demo — Long Term"),
               ("demo_trading.csv", "Demo — Trading")]


def _load_demo_raw():
    uploads, names = [], {}
    for fname, label in _DEMO_FILES:
        buf = io.BytesIO((_SAMPLE / fname).read_bytes())
        buf.name = fname
        uploads.append(buf)
        names[fname] = label
    raw, errs = parse_all(uploads, names)
    return raw, errs


class TestSampleFilesExist(unittest.TestCase):
    def test_both_files_present(self):
        for fname, _ in _DEMO_FILES:
            self.assertTrue((_SAMPLE / fname).exists(), fname)


class TestDemoParsesToCanonical(unittest.TestCase):
    def test_canonical_schema_and_two_accounts(self):
        raw, errs = _load_demo_raw()
        self.assertEqual(errs, [])
        self.assertIsNotNone(raw)
        for col in ("ticker", "shares", "avg_cost", "account"):
            self.assertIn(col, raw.columns, col)
        self.assertEqual(set(raw["account"].unique()),
                         {"Demo — Long Term", "Demo — Trading"})
        self.assertGreaterEqual(len(raw), 10)


class TestDemoDrivesPipeline(unittest.TestCase):
    def test_holdings_and_insights(self):
        raw, _ = _load_demo_raw()
        # Offline: price each ticker from its file LTP (what build_holdings falls back to).
        prices = raw.groupby("ticker")["ltp"].first().to_dict()
        meta = {"sectors": {}, "names": {}, "analyst": {}, "fundamentals": {}}
        holdings = analytics.build_holdings(raw, prices, meta)
        totals = analytics.portfolio_totals(holdings)
        self.assertGreater(totals["value"], 0)

        res = intelligence.analyze(holdings, raw, prices, meta, totals, {}, {})
        self.assertFalse(res["empty"])
        # The demo is seeded to fire at least concentration + tax-loss offline.
        self.assertGreaterEqual(len(res["insights"]), 1)
        cats = {i.category for i in res["insights"]}
        self.assertTrue({"PORTFOLIO_RISK", "TAX_LOSS"} & cats)


if __name__ == "__main__":
    unittest.main()
