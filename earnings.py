"""Corporate-events engine — pure, no I/O, no Streamlit (mirrors intelligence.py).

Normalises raw market data (earnings dates from market_data.fetch_earnings_events,
plus metadata) into ranked, categorised Event objects for the 📅 Earnings Calendar.

Honesty posture (same as intelligence.py): builders never invent. A builder with no
data source returns []. Today only Quarterly Results has a free data source (Yahoo
`Ticker.calendar` → Earnings Date); Earnings Call and Investor Presentation are
defined and wired but return [] until a source exists. Adding a new event type =
add one builder fn to BUILDERS, nothing else changes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable

from formatting import GAIN, GOLD, MUTED

# ─── Event types: label + emoji + colour, single source of truth ──────────────
QUARTERLY = "Quarterly Results"
EARNINGS_CALL = "Earnings Call"
PRESENTATION = "Investor Presentation"

EVENT_META = {
    QUARTERLY:     {"emoji": "📊", "color": GOLD},
    EARNINGS_CALL: {"emoji": "🎤", "color": GAIN},
    PRESENTATION:  {"emoji": "📄", "color": MUTED},
}
EVENT_TYPES = list(EVENT_META)  # display/filter order

# Future-ready: reminder offsets a notification layer would schedule off Event.when.
# No scheduler today (see PRD §6, FR "Notifications future-ready"); a job just needs
# to walk events and fire at when - offset.
REMINDER_OFFSETS = ["7 days", "1 day", "1 hour"]


@dataclass
class Event:
    symbol: str
    company: str
    type: str
    when: date                      # event date (Yahoo gives date, not time)
    quarter: str = ""               # "Q1 FY26" etc. — best-effort, may be ""
    description: str = ""
    ir_url: str | None = None
    days_remaining: int = 0         # filled by build_events relative to "today"
    status: str = "Upcoming"        # Upcoming / Today / Completed

    @property
    def emoji(self) -> str:
        return EVENT_META.get(self.type, {}).get("emoji", "•")

    @property
    def color(self) -> str:
        return EVENT_META.get(self.type, {}).get("color", MUTED)


def _status(when: date, today: date) -> str:
    if when < today:
        return "Completed"
    if when == today:
        return "Today"
    return "Upcoming"


def _quarter(when: date) -> str:
    """Indian-fiscal quarter the results most likely cover, from announcement month.
    ponytail: month→quarter heuristic (results lag the quarter ~1 month). Exact
    quarter would need the filing itself; this is good enough to label a calendar."""
    m, y = when.month, when.year
    if m in (4, 5, 6):        # Apr-Jun announce → Q4 of prior FY (Jan-Mar)
        return f"Q4 FY{(y % 100)}"
    if m in (7, 8, 9):        # Jul-Sep → Q1 (Apr-Jun)
        return f"Q1 FY{((y + 1) % 100)}"
    if m in (10, 11, 12):     # Oct-Dec → Q2 (Jul-Sep)
        return f"Q2 FY{((y + 1) % 100)}"
    return f"Q3 FY{(y % 100)}"  # Jan-Mar → Q3 (Oct-Dec)


# ─── Builders: (symbol, company, earnings_date, fundamentals) -> list[Event] ──

def _quarterly_results(sym, company, edate, fund) -> list[Event]:
    if not edate:
        return []
    return [Event(
        symbol=sym, company=company, type=QUARTERLY, when=edate,
        quarter=_quarter(edate),
        description=f"{company} is expected to report quarterly results.",
        ir_url=(fund or {}).get("website"),
    )]


def _earnings_call(sym, company, edate, fund) -> list[Event]:
    # No free, reliable call-schedule source for NSE/BSE. Return [] rather than
    # guess "same day as results". Wire a source here when one exists.
    return []


def _investor_presentation(sym, company, edate, fund) -> list[Event]:
    # No free source for IR-deck publication dates. See _earnings_call.
    return []


BUILDERS: list[Callable] = [_quarterly_results, _earnings_call, _investor_presentation]


def build_events(symbols, names: dict, earnings_dates: dict,
                 fundamentals: dict, today: date | None = None) -> list[Event]:
    """Run every builder over every symbol, fill status/days_remaining, sort by
    nearest upcoming first (completed events sink to the bottom, most-recent first)."""
    today = today or date.today()
    out: list[Event] = []
    for sym in symbols:
        company = names.get(sym, sym)
        edate = earnings_dates.get(sym)
        fund = fundamentals.get(sym, {})
        for build in BUILDERS:
            try:
                out.extend(build(sym, company, edate, fund))
            except Exception:
                continue  # one bad symbol never breaks the calendar
    for e in out:
        e.status = _status(e.when, today)
        e.days_remaining = (e.when - today).days
    # upcoming (days>=0) ascending, then completed ascending-by-recency (closest past first)
    out.sort(key=lambda e: (e.days_remaining < 0, abs(e.days_remaining)))
    return out


if __name__ == "__main__":
    t = date(2026, 6, 30)
    evs = build_events(
        ["RELIANCE", "FOO"],
        {"RELIANCE": "Reliance Industries"},
        {"RELIANCE": date(2026, 7, 17), "FOO": None},
        {"RELIANCE": {"website": "https://ril.com"}},
        today=t,
    )
    assert len(evs) == 1, evs                         # FOO has no date → no event
    e = evs[0]
    assert e.type == QUARTERLY and e.status == "Upcoming"
    assert e.days_remaining == 17 and e.quarter == "Q1 FY27"
    assert e.ir_url == "https://ril.com" and e.emoji == "📊"
    assert _status(date(2026, 6, 29), t) == "Completed"
    assert _status(t, t) == "Today"
    print("earnings.py self-check OK")
