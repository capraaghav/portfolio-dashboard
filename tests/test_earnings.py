import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from datetime import date

import analytics
import earnings


class TestBuildEvents(unittest.TestCase):
    TODAY = date(2026, 6, 30)

    def _build(self, edates, names=None, fund=None):
        syms = list(edates)
        names = names or {s: s for s in syms}
        return earnings.build_events(syms, names, edates, fund or {}, today=self.TODAY)

    def test_no_date_yields_no_event(self):
        # honesty posture: missing data → nothing invented
        self.assertEqual(self._build({"FOO": None}), [])

    def test_quarterly_event_fields(self):
        evs = self._build({"RELIANCE": date(2026, 7, 17)},
                          {"RELIANCE": "Reliance Industries"},
                          {"RELIANCE": {"website": "https://ril.com"}})
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual(e.type, earnings.QUARTERLY)
        self.assertEqual(e.status, "Upcoming")
        self.assertEqual(e.days_remaining, 17)
        self.assertEqual(e.quarter, "Q1 FY27")
        self.assertEqual(e.ir_url, "https://ril.com")

    def test_status_today_and_completed(self):
        evs = self._build({"A": self.TODAY, "B": date(2026, 6, 20)})
        by_sym = {e.symbol: e for e in evs}
        self.assertEqual(by_sym["A"].status, "Today")
        self.assertEqual(by_sym["A"].days_remaining, 0)
        self.assertEqual(by_sym["B"].status, "Completed")
        self.assertEqual(by_sym["B"].days_remaining, -10)

    def test_sorted_nearest_upcoming_first_completed_last(self):
        evs = self._build({
            "FAR": date(2026, 8, 1),    # +32
            "SOON": date(2026, 7, 2),   # +2
            "PAST": date(2026, 6, 25),  # -5
        })
        self.assertEqual([e.symbol for e in evs], ["SOON", "FAR", "PAST"])

    def test_quarter_boundaries(self):
        self.assertEqual(earnings._quarter(date(2026, 5, 1)), "Q4 FY26")
        self.assertEqual(earnings._quarter(date(2026, 8, 1)), "Q1 FY27")
        self.assertEqual(earnings._quarter(date(2026, 11, 1)), "Q2 FY27")
        self.assertEqual(earnings._quarter(date(2026, 2, 1)), "Q3 FY26")

    def test_unsourced_types_return_empty(self):
        # earnings call + presentation builders have no data source yet
        self.assertEqual(earnings._earnings_call("X", "X", date(2026, 7, 1), {}), [])
        self.assertEqual(earnings._investor_presentation("X", "X", date(2026, 7, 1), {}), [])


class TestTradingViewList(unittest.TestCase):
    def test_default_nse_prefix(self):
        self.assertEqual(analytics.tradingview_list(["RELIANCE", "TCS"]),
                         "NSE:RELIANCE, NSE:TCS")

    def test_bse_suffix_maps_to_bse(self):
        self.assertEqual(analytics.tradingview_list(["ABC"], {"ABC": ".BO"}), "BSE:ABC")

    def test_header_prefix(self):
        self.assertEqual(analytics.tradingview_list(["A", "B"], header="Watchlist"),
                         "###Watchlist,NSE:A, NSE:B")

    def test_skips_empty_tickers(self):
        self.assertEqual(analytics.tradingview_list([None, "", "A"]), "NSE:A")


if __name__ == "__main__":
    unittest.main()
