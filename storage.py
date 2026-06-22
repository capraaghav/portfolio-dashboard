"""Local persistence — portfolio snapshots (for performance history) and the
last parsed session (so the user need not re-upload every launch).

Everything is written under ./data/ next to the app. Nothing leaves the machine.
"""

from __future__ import annotations
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
SNAPSHOT_FILE = DATA_DIR / "snapshots.json"
SESSION_FILE = DATA_DIR / "last_session.parquet"
SESSION_META = DATA_DIR / "last_session.json"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
OVERRIDES_FILE = DATA_DIR / "price_overrides.json"


def configure(data_dir) -> None:
    """Point all persistence at `data_dir`. Used to give each visitor of a hosted
    (multi-user) deployment their own isolated directory, so no one can see another
    user's saved holdings, snapshots, watchlist, or overrides."""
    global DATA_DIR, SNAPSHOT_FILE, SESSION_FILE, SESSION_META, WATCHLIST_FILE, OVERRIDES_FILE
    DATA_DIR = Path(data_dir)
    SNAPSHOT_FILE = DATA_DIR / "snapshots.json"
    SESSION_FILE = DATA_DIR / "last_session.parquet"
    SESSION_META = DATA_DIR / "last_session.json"
    WATCHLIST_FILE = DATA_DIR / "watchlist.json"
    OVERRIDES_FILE = DATA_DIR / "price_overrides.json"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ─── Snapshots (performance history) ─────────────────────────────────────────

def load_snapshots() -> list[dict]:
    if not SNAPSHOT_FILE.exists():
        return []
    try:
        return json.loads(SNAPSHOT_FILE.read_text())
    except Exception:
        return []


def save_snapshot(totals: dict, holdings: pd.DataFrame, when: str | None = None) -> bool:
    """Append today's snapshot. One snapshot per calendar date (re-saving overwrites today)."""
    _ensure_dir()
    snaps = load_snapshots()
    stamp = when or date.today().isoformat()

    per_stock = {}
    for _, r in holdings.iterrows():
        v = r.get("Current Value (₹)")
        if pd.notna(v):
            per_stock[r["Ticker"]] = round(float(v), 2)

    entry = {
        "date": stamp,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "total_value": None if pd.isna(totals.get("value")) else round(float(totals["value"]), 2),
        "total_cost": None if pd.isna(totals.get("cost")) else round(float(totals["cost"]), 2),
        "total_pnl": None if pd.isna(totals.get("pnl")) else round(float(totals["pnl"]), 2),
        "n_holdings": int(totals.get("n_holdings", 0)),
        "holdings": per_stock,
    }

    snaps = [s for s in snaps if s.get("date") != stamp]  # replace same-day
    snaps.append(entry)
    snaps.sort(key=lambda s: s["date"])
    SNAPSHOT_FILE.write_text(json.dumps(snaps, indent=2))
    return True


def snapshots_df() -> pd.DataFrame:
    snaps = load_snapshots()
    if not snaps:
        return pd.DataFrame()
    df = pd.DataFrame([{
        "date": pd.to_datetime(s["date"]),
        "Total Value": s.get("total_value"),
        "Total Cost": s.get("total_cost"),
        "Total P&L": s.get("total_pnl"),
        "Holdings": s.get("n_holdings"),
    } for s in snaps])
    return df.sort_values("date").reset_index(drop=True)


def auto_snapshot_if_new(totals: dict, holdings: pd.DataFrame) -> bool:
    """Save automatically at most once per calendar day. Returns True if it wrote."""
    snaps = load_snapshots()
    today = date.today().isoformat()
    if any(s.get("date") == today for s in snaps):
        return False
    save_snapshot(totals, holdings)
    return True


# ─── Last-session persistence ────────────────────────────────────────────────

def save_session(raw: pd.DataFrame) -> None:
    _ensure_dir()
    try:
        raw.to_parquet(SESSION_FILE, index=False)
        SESSION_META.write_text(json.dumps({
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "rows": len(raw),
            "accounts": sorted(raw["account"].unique().tolist()) if "account" in raw else [],
        }, indent=2))
    except Exception:
        # Parquet needs pyarrow; fall back to CSV so persistence still works.
        raw.to_csv(SESSION_FILE.with_suffix(".csv"), index=False)


def load_session() -> pd.DataFrame | None:
    if SESSION_FILE.exists():
        try:
            return pd.read_parquet(SESSION_FILE)
        except Exception:
            pass
    csv = SESSION_FILE.with_suffix(".csv")
    if csv.exists():
        try:
            df = pd.read_csv(csv)
            if "purchase_date" in df.columns:
                df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
            return df
        except Exception:
            pass
    return None


def session_meta() -> dict:
    if SESSION_META.exists():
        try:
            return json.loads(SESSION_META.read_text())
        except Exception:
            return {}
    return {}


# ─── Small key/value prefs (watchlist, manual price overrides) ───────────────

def load_watchlist() -> list[str]:
    if WATCHLIST_FILE.exists():
        try:
            return json.loads(WATCHLIST_FILE.read_text())
        except Exception:
            return []
    return []


def save_watchlist(tickers: list[str]) -> None:
    _ensure_dir()
    WATCHLIST_FILE.write_text(json.dumps(sorted(set(tickers)), indent=2))


def load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        try:
            return json.loads(OVERRIDES_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_overrides(overrides: dict) -> None:
    _ensure_dir()
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))
