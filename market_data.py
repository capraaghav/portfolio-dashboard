"""All Yahoo Finance data fetching, cached. Indian NSE/BSE tickers.

Cache TTLs:
    quotes      5 min   (live prices + day change)
    metadata    1 hour  (sector, name, analyst targets, fundamentals)
    TA signals  1 hour  (200d history → SMA/RSI)
    dividends   6 hour
    benchmark   1 hour
Per-stock detail (history, news) is fetched on demand and lightly cached.

Note on st.cache_data: a parameter whose name starts with '_' is excluded from
the cache key. We use that to pass the resolved-suffix map without breaking caching.
"""

from __future__ import annotations
import datetime
import difflib
import io
import re
import time
from collections import Counter
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

import analytics

SUFFIXES = [".NS", ".BO"]


# ─── Company-name → ticker resolution (for brokers like HDFC) ────────────────

_SEARCH_SESSION = None


def _yahoo_session():
    global _SEARCH_SESSION
    if _SEARCH_SESSION is None:
        try:
            from curl_cffi import requests as creq
            _SEARCH_SESSION = creq.Session(impersonate="chrome")
        except Exception:
            import requests as preq
            _SEARCH_SESSION = preq.Session()
            _SEARCH_SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
    return _SEARCH_SESSION


def _yahoo_search(query: str, count: int = 8) -> list:
    for attempt in range(2):
        try:
            r = _yahoo_session().get(
                "https://query2.finance.yahoo.com/v1/finance/search",
                params={"q": query, "quotesCount": count, "newsCount": 0}, timeout=10)
            quotes = r.json().get("quotes")
            if quotes is not None:
                return quotes
        except Exception:
            pass
        time.sleep(0.5)
    return []


def _norm_name(s: str) -> str:
    s = str(s).upper()
    for w in ["LIMITED", "LTD", "THE ", " EQ", " NEW"]:
        s = s.replace(w, "")
    s = s.replace("&", " ")
    s = re.sub(r"\bAND\b", " ", s)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", "", s)).strip()


def _core_query(cleaned: str) -> str:
    """A simplified query — Yahoo search sometimes returns only foreign listings for the
    full 'X AND Y LIMITED' form but resolves correctly for the bare 'X Y' core."""
    s = re.sub(r"\b(LIMITED|LTD)\b", "", str(cleaned).upper())
    s = re.sub(r"\bAND\b", " ", s.replace("&", " "))
    return re.sub(r"\s+", " ", s).strip()


def _resolve_one_name(query: str, csv_ltp: float | None = None) -> str | None:
    """Resolve a company name to a bare NSE/BSE ticker. Searches the full name and a
    simplified core query, merges candidates, then lets the CSV's LTP decide (the
    candidate whose live price matches the CSV price wins — catches 'ABB INDIA' → ABB,
    not Abbott India). Falls back to name similarity when no price match is found."""
    qup = query.strip().upper()
    # If the cleaned name is itself a clean ticker (e.g. 'SAIL' from 'SAIL EQUITY
    # SHARES'), use it directly — Yahoo's fuzzy search often returns a look-alike.
    if not re.match(r"^IN[A-Z][0-9A-Z]{9}$", qup) and re.match(r"^[A-Z0-9&\-]{2,12}$", qup):
        return qup

    # Search several phrasings — Yahoo's NSE coverage is sensitive to exact wording.
    queries = [query]
    no_suffix = re.sub(r"\s+", " ", re.sub(r"\b(LIMITED|LTD)\b", "", qup)).strip()
    if no_suffix and no_suffix != qup:
        queries.append(no_suffix)
    core = _core_query(query)
    if core and core not in (qup, no_suffix):
        queries.append(core)

    seen, cands = set(), []
    for q in queries:
        for c in _yahoo_search(q):
            sym = str(c.get("symbol", ""))
            if sym.endswith((".NS", ".BO")) and sym not in seen:
                seen.add(sym)
                cands.append((sym, c.get("longname") or c.get("shortname") or ""))
    if not cands:
        return None

    # An ISIN uniquely identifies the security — trust Yahoo's match (the ISIN won't
    # name-match the company, so don't require similarity or a price check).
    if re.match(r"^IN[A-Z][0-9A-Z]{9}$", query.strip().upper()):
        cands.sort(key=lambda x: not x[0].endswith(".NS"))  # prefer NSE
        return cands[0][0].rsplit(".", 1)[0]

    nq = _norm_name(query)
    scored = [(sym, difflib.SequenceMatcher(None, nq, _norm_name(ln)).ratio()) for sym, ln in cands]
    scored.sort(key=lambda x: (not x[0].endswith(".NS"), -x[1]))

    # Price proximity is decisive when we have the CSV LTP
    if csv_ltp and csv_ltp > 0:
        priced = []
        for sym, score in scored[:6]:
            try:
                px = yf.Ticker(sym).fast_info.last_price
            except Exception:
                px = None
            if px and abs(px / csv_ltp - 1) <= 0.06:
                priced.append((sym, score, abs(px / csv_ltp - 1)))
        if priced:
            priced.sort(key=lambda x: (not x[0].endswith(".NS"), -x[1], x[2]))
            return priced[0][0].rsplit(".", 1)[0]

    # Fallback: best name match
    top_sym, top_score = scored[0]
    return top_sym.rsplit(".", 1)[0] if top_score >= 0.62 else None


_ISIN_PAT = re.compile(r"^IN[A-Z][0-9A-Z]{9}$")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nse_master() -> dict:
    """NSE's official equity list — the authoritative web source for Indian tickers
    (more current than Yahoo; e.g. it knows Adani Wilmar is now 'AWL'). Returns
    {'isin': {isin: symbol}, 'names': [(norm_name, symbol)], 'symbols': set}."""
    try:
        r = _yahoo_session().get(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv", timeout=20)
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        sym = df["SYMBOL"].astype(str).str.strip()
        return {
            "isin": dict(zip(df["ISIN NUMBER"].astype(str).str.strip(), sym)),
            "names": [(_norm_name(n), s) for n, s in zip(df["NAME OF COMPANY"], sym)],
            "symbols": set(sym),
        }
    except Exception:
        return {"isin": {}, "names": [], "symbols": set()}


def _match_nse_master(query: str, master: dict) -> str | None:
    """Resolve against the official NSE list: exact ISIN, else fuzzy company name."""
    if not master.get("names"):
        return None
    qup = query.strip().upper()
    if _ISIN_PAT.match(qup):
        return master["isin"].get(qup)
    nq = _norm_name(query)
    if not nq:
        return None
    best_sym, best_score = None, 0.0
    for norm, sym in master["names"]:
        sc = difflib.SequenceMatcher(None, nq, norm).ratio()
        if sc > best_score:
            best_score, best_sym = sc, sym
    return best_sym if best_score >= 0.78 else None


def _web_resolve(name: str, csv_ltp: float | None, master: dict) -> str | None:
    """Last resort — consult the broader web (DuckDuckGo) for renamed companies Yahoo
    no longer maps (e.g. 'Adani Wilmar' -> AWL). Only accepts a symbol whose live price
    matches the CSV price, so it never guesses a popular ticker for an obscure holding.
    Requires a real CSV price; suspended/₹0 holdings stay unresolved on purpose."""
    if not master.get("symbols") or not csv_ltp or csv_ltp <= 0:
        return None
    try:
        r = _yahoo_session().get("https://html.duckduckgo.com/html/",
                                 params={"q": f"{name} NSE stock symbol share price"}, timeout=15)
    except Exception:
        return None
    tokens = re.findall(r"\b([A-Z][A-Z0-9&\-]{2,12})\b", r.text.upper())
    counts = Counter(t for t in tokens if t in master["symbols"] and t not in ("NSE", "BSE"))
    if not counts:
        return None
    best = None  # (symbol, price_proximity) — keep the closest price match
    for sym, _freq in counts.most_common(8):
        for suf in SUFFIXES:
            try:
                px = yf.Ticker(sym + suf).fast_info.last_price
            except Exception:
                px = None
            if px:
                prox = abs(px / csv_ltp - 1)
                if prox <= 0.06 and (best is None or prox < best[1]):
                    best = (sym, prox)
                break
    return best[0] if best else None


@st.cache_data(ttl=86400, show_spinner=False)
def resolve_symbols(names: tuple, _query_map: dict, _ltp_map: dict) -> dict:
    """{original_name: bare_ticker_or_None}. Cached 24h. Resolution chain:
    1) Yahoo Finance search (with CSV-price disambiguation),
    2) NSE official symbol master (authoritative for ISINs + name misses),
    3) broader web search (DuckDuckGo) validated against the NSE list + price."""
    out: dict[str, str | None] = {}
    if not names:
        return out
    master = fetch_nse_master()

    def one(n):
        q = _query_map.get(n, n)
        ltp = _ltp_map.get(n)
        qup = str(q).strip().upper()
        # ISIN: the NSE list is authoritative; fall back to Yahoo if absent
        if _ISIN_PAT.match(qup):
            return n, (master["isin"].get(qup) or _resolve_one_name(q, ltp))
        sym = _resolve_one_name(q, ltp)               # 1) Yahoo
        if sym:
            return n, sym
        sym = _match_nse_master(q, master)            # 2) NSE official list
        if sym:
            return n, sym
        return n, _web_resolve(q, ltp, master)        # 3) broader web

    with ThreadPoolExecutor(max_workers=min(10, len(names))) as ex:
        for n, sym in ex.map(one, names):
            out[n] = sym
    return out


# ─── Suffix resolution + live quotes ──────────────────────────────────────────

def _resolve_one(ticker: str) -> tuple[str, str, float | None, float | None]:
    """Return (ticker, suffix, last_price, previous_close). Tries NSE then BSE."""
    for suffix in SUFFIXES:
        try:
            fi = yf.Ticker(ticker + suffix).fast_info
            price = fi.last_price
            if price and price > 0:
                try:
                    prev = float(fi.previous_close)
                except Exception:
                    prev = None
                return ticker, suffix, round(float(price), 2), prev
        except Exception:
            pass
    return ticker, "", None, None


def _quote_from_close(close: pd.Series, suffix: str) -> dict:
    price = round(float(close.iloc[-1]), 2)
    prev = round(float(close.iloc[-2]), 2) if len(close) >= 2 else None
    chg = (price - prev) if prev else None
    return {"price": price, "prev_close": prev, "day_chg": chg,
            "day_chg_pct": (chg / prev * 100) if (chg and prev) else None, "suffix": suffix}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_quotes(tickers: tuple) -> dict:
    """{ticker: {price, prev_close, day_chg, day_chg_pct, suffix}}.
    Bulk-downloads recent closes in one request per exchange (avoids per-ticker rate
    limits); day change is close-over-close. Falls back to fast_info for stragglers."""
    out: dict[str, dict] = {}
    if not tickers:
        return out
    remaining = list(tickers)
    for suffix in SUFFIXES:                         # .NS batch, then .BO for leftovers
        if not remaining:
            break
        syms = [t + suffix for t in remaining]
        try:
            data = yf.download(syms, period="5d", auto_adjust=True, progress=False,
                               threads=True, group_by="ticker")
        except Exception:
            data = None
        if data is None or data.empty:
            continue
        single = len(syms) == 1
        still = []
        for t in remaining:
            try:
                close = (data["Close"] if single else data[t + suffix]["Close"]).dropna()
                if not close.empty and float(close.iloc[-1]) > 0:
                    out[t] = _quote_from_close(close, suffix)
                else:
                    still.append(t)
            except Exception:
                still.append(t)
        remaining = still

    if remaining:                                   # fast_info fallback for the rest
        with ThreadPoolExecutor(max_workers=min(8, len(remaining))) as ex:
            for t, suf, price, prev in ex.map(_resolve_one, remaining):
                chg = (price - prev) if (price is not None and prev) else None
                out[t] = {"price": price, "prev_close": prev, "day_chg": chg,
                          "day_chg_pct": (chg / prev * 100) if (chg and prev) else None,
                          "suffix": suf or ".NS"}

    for t in tickers:                               # ensure every ticker has an entry
        out.setdefault(t, {"price": None, "prev_close": None, "day_chg": None,
                           "day_chg_pct": None, "suffix": ".NS"})
    return out


def prices_from_quotes(quotes: dict) -> dict:
    return {t: q.get("price") for t, q in quotes.items()}


def suffix_map_from_quotes(quotes: dict) -> dict:
    return {t: q.get("suffix", ".NS") for t, q in quotes.items()}


# ─── Metadata: sector, name, analyst targets, fundamentals ───────────────────

def _fetch_meta_one(ticker: str, suffix: str) -> tuple:
    info = None
    for attempt in range(3):
        try:
            info = yf.Ticker(ticker + suffix).info
            if info and (info.get("longName") or info.get("shortName")
                         or info.get("regularMarketPrice") or info.get("targetMeanPrice")):
                break
        except Exception:
            info = None
        time.sleep(0.4 * (attempt + 1))  # back off on rate limits
    if not info:
        return ticker, "Unknown", ticker, {}, {}
    def _f(x):  # numeric fields → finite float or None (Yahoo sometimes sends strings)
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return None if (v != v or v in (float("inf"), float("-inf"))) else v

    try:
        sector = info.get("sector") or "Unknown"
        name = info.get("longName") or info.get("shortName") or ticker
        analyst = {
            "target_low":    _f(info.get("targetLowPrice")),
            "target_high":   _f(info.get("targetHighPrice")),
            "target_mean":   _f(info.get("targetMeanPrice")),
            "target_median": _f(info.get("targetMedianPrice")),
            "n_analysts":    _f(info.get("numberOfAnalystOpinions")),
            "rec_key":       info.get("recommendationKey"),
            "rec_mean":      _f(info.get("recommendationMean")),
        }
        fundamentals = {
            "pe":          _f(info.get("trailingPE")),
            "forward_pe":  _f(info.get("forwardPE")),
            "pb":          _f(info.get("priceToBook")),
            "market_cap":  _f(info.get("marketCap")),
            "beta":        _f(info.get("beta")),
            "roe":         _f(info.get("returnOnEquity")),
            "profit_margin": _f(info.get("profitMargins")),
            "debt_to_equity": _f(info.get("debtToEquity")),
            "div_yield":   _f(info.get("dividendYield")),
            "wk52_high":   _f(info.get("fiftyTwoWeekHigh")),
            "wk52_low":    _f(info.get("fiftyTwoWeekLow")),
            "industry":    info.get("industry"),
            "website":     info.get("website"),  # IR link for Earnings Calendar
        }
        return ticker, sector, name, analyst, fundamentals
    except Exception:
        return ticker, "Unknown", ticker, {}, {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_metadata(tickers: tuple, _suffix_map: dict) -> dict:
    """Sector, company name, analyst targets, fundamentals — one .info call each."""
    sectors, names, analyst, fundamentals = {}, {}, {}, {}
    if not tickers:
        return {"sectors": {}, "names": {}, "analyst": {}, "fundamentals": {}}
    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as ex:
        futures = {
            ex.submit(_fetch_meta_one, t, _suffix_map.get(t, ".NS")): t
            for t in tickers
        }
        for future in as_completed(futures):
            ticker, sector, name, adata, fdata = future.result()
            sectors[ticker] = sector
            names[ticker] = name
            analyst[ticker] = adata
            fundamentals[ticker] = fdata
    return {"sectors": sectors, "names": names, "analyst": analyst, "fundamentals": fundamentals}


def _earnings_date_one(ticker: str, suffix: str):
    """Next earnings date from Yahoo's calendar, or None. Never raises."""
    try:
        cal = yf.Ticker(ticker + suffix).calendar or {}
        dates = cal.get("Earnings Date") or []
        if isinstance(dates, (list, tuple)):
            dates = [d for d in dates if d is not None]
            d = min(dates) if dates else None
        else:
            d = dates or None
        return d.date() if isinstance(d, datetime.datetime) else d
    except Exception:
        return None


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_earnings_events(tickers: tuple, _suffix_map: dict) -> dict:
    """{ticker: next earnings date | None}. One failing ticker never breaks the rest.
    Cached 6h — corporate-event dates move on the order of days, not minutes."""
    out = {}
    if not tickers:
        return out
    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as ex:
        futures = {
            ex.submit(_earnings_date_one, t, _suffix_map.get(t, ".NS")): t
            for t in tickers
        }
        for future in as_completed(futures):
            out[futures[future]] = future.result()
    return out


# ─── Technical analysis (200d history → signals) ─────────────────────────────

def _fetch_history_one(ticker: str, suffix: str, period: str = "200d") -> tuple[str, pd.Series]:
    order = [suffix] + [s for s in SUFFIXES if s != suffix]
    for suf in order:
        try:
            hist = yf.Ticker(ticker + suf).history(period=period, auto_adjust=True)
            if not hist.empty:
                return ticker, hist["Close"].dropna()
        except Exception:
            pass
    return ticker, pd.Series(dtype=float)


def _download_closes(tickers: tuple, suffix_map: dict, period: str = "200d") -> dict:
    """Bulk-download closing prices in ONE request to avoid per-ticker rate limits.
    Falls back to individual fetches only for tickers the batch missed."""
    closes: dict[str, pd.Series] = {}
    if not tickers:
        return closes
    sym_of = {t: t + suffix_map.get(t, ".NS") for t in tickers}
    syms = list(dict.fromkeys(sym_of.values()))
    try:
        data = yf.download(syms, period=period, auto_adjust=True, progress=False,
                           threads=True, group_by="ticker")
    except Exception:
        data = None
    if data is not None and not data.empty:
        single = len(syms) == 1
        for t, s in sym_of.items():
            try:
                ser = (data["Close"] if single else data[s]["Close"]).dropna()
                if not ser.empty:
                    closes[t] = ser
            except Exception:
                pass
    missing = [t for t in tickers if t not in closes]
    if missing:
        with ThreadPoolExecutor(max_workers=min(6, len(missing))) as ex:
            for t, ser in ex.map(lambda x: _fetch_history_one(x, suffix_map.get(x, ".NS"), period), missing):
                if not ser.empty:
                    closes[t] = ser
    return closes


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ta_signals(tickers: tuple, _suffix_map: dict) -> dict:
    """Bulk-download 200d closes, compute SMA20/50/200 + RSI14 per ticker."""
    if not tickers:
        return {}
    closes = _download_closes(tickers, _suffix_map, "200d")
    return {t: analytics.compute_signal(closes.get(t, pd.Series(dtype=float))) for t in tickers}


# ─── Dividends ────────────────────────────────────────────────────────────────

def _fetch_div_one(ticker: str, suffix: str, price: float | None) -> tuple[str, dict]:
    order = [suffix] + [s for s in SUFFIXES if s != suffix]
    for suf in order:
        try:
            divs = yf.Ticker(ticker + suf).dividends
            if divs is not None and not divs.empty:
                cutoff = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                ttm = float(divs[divs.index >= cutoff].sum())
                yld = (ttm / price * 100) if (price and ttm) else None
                return ticker, {
                    "ttm": ttm,
                    "yield_pct": yld,
                    "last_amount": float(divs.iloc[-1]),
                    "last_date": divs.index[-1].date().isoformat(),
                    "history": divs,
                }
        except Exception:
            pass
    return ticker, {"ttm": 0.0, "yield_pct": None, "last_amount": None, "last_date": None, "history": None}


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_dividends(tickers: tuple, _suffix_map: dict, _price_map: dict) -> dict:
    """{ticker: {ttm, yield_pct, last_amount, last_date, history}}."""
    out: dict[str, dict] = {}
    if not tickers:
        return out
    with ThreadPoolExecutor(max_workers=min(12, len(tickers))) as ex:
        futures = {
            ex.submit(_fetch_div_one, t, _suffix_map.get(t, ".NS"), _price_map.get(t)): t
            for t in tickers
        }
        for future in as_completed(futures):
            ticker, data = future.result()
            out[ticker] = data
    return out


# ─── Per-stock detail (on demand) ────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_history_single(ticker: str, suffix: str, period: str = "1y") -> pd.DataFrame:
    order = [suffix] + [s for s in SUFFIXES if s != suffix]
    for suf in order:
        try:
            hist = yf.Ticker(ticker + suf).history(period=period, auto_adjust=True)
            if not hist.empty:
                return hist
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_single(ticker: str, suffix: str, limit: int = 6) -> list:
    order = [suffix] + [s for s in SUFFIXES if s != suffix]
    for suf in order:
        try:
            news = yf.Ticker(ticker + suf).news or []
            out = []
            for item in news[:limit]:
                content = item.get("content", item)  # yfinance schema varies by version
                title = content.get("title") or item.get("title")
                if not title:
                    continue
                link = (
                    (content.get("canonicalUrl") or {}).get("url")
                    or (content.get("clickThroughUrl") or {}).get("url")
                    or item.get("link")
                )
                publisher = (
                    (content.get("provider") or {}).get("displayName")
                    or item.get("publisher")
                    or ""
                )
                out.append({"title": title, "link": link, "publisher": publisher})
            if out:
                return out
        except Exception:
            pass
    return []


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_closes(tickers: tuple, _suffix_map: dict, period: str = "1y") -> dict:
    """{ticker: close_series} over `period` — used to backtest the current basket.
    Uses the bulk downloader (one request) to stay under Yahoo rate limits."""
    return _download_closes(tickers, _suffix_map, period)


# ─── Benchmark indices ───────────────────────────────────────────────────────

BENCHMARKS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY Bank": "^NSEBANK",
    "NIFTY Midcap 100": "^NSEMDCP50",
}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_benchmark(symbol: str, period: str = "1y") -> pd.Series:
    try:
        hist = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        return hist["Close"].dropna()
    except Exception:
        return pd.Series(dtype=float)


# ─── Universe lists for Screener ─────────────────────────────────────────────

UNIVERSE_URLS = {
    "Nifty 500": "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "Nifty 50":  "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
}

# Static fallback — used when NSE is unreachable. Covers ~50 liquid large-caps.
_NIFTY50_FALLBACK = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "TITAN", "SUNPHARMA", "WIPRO", "ULTRACEMCO", "BAJFINANCE", "HCLTECH",
    "POWERGRID", "NTPC", "NESTLEIND", "TECHM", "INDUSINDBK", "ONGC", "TATAMOTORS",
    "ADANIENT", "BAJAJFINSV", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
    "GRASIM", "HEROMOTOCO", "HINDALCO", "JSWSTEEL", "M&M", "SBILIFE",
    "BRITANNIA", "CIPLA", "BPCL", "APOLLOHOSP", "TATACONSUM", "HDFCLIFE",
    "ADANIPORTS", "LTIM", "BAJAJ-AUTO", "UPL", "TATASTEEL",
]

_NIFTY500_FALLBACK = _NIFTY50_FALLBACK  # trimmed fallback; real list loads from NSE


@st.cache_data(ttl=86400, show_spinner=False)
def get_universe(name: str) -> list[str]:
    """Return bare NSE symbols for a named universe. Cached 24h.
    Falls back to a static list if NSE is unreachable."""
    url = UNIVERSE_URLS.get(name)
    if not url:
        return _NIFTY50_FALLBACK
    try:
        r = _yahoo_session().get(url, timeout=20)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        sym_col = next(
            (c for c in df.columns if c.upper() in ("SYMBOL", "SYMBOLS")), None
        )
        if sym_col is None:
            sym_col = df.columns[0]
        symbols = (
            df[sym_col]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .unique()
            .tolist()
        )
        symbols = [s for s in symbols if s and len(s) <= 20]
        return symbols if symbols else _NIFTY50_FALLBACK
    except Exception:
        fallback = _NIFTY500_FALLBACK if "500" in name else _NIFTY50_FALLBACK
        return fallback


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_screener_history(tickers: tuple, _suffix_map: dict, period: str = "200d") -> dict:
    """Bulk-download closing prices for screener universe. Cached 1h.
    Returns {ticker: close_series}. Wraps _download_closes()."""
    if not tickers:
        return {}
    return _download_closes(tickers, _suffix_map, period)
