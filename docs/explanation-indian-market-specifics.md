# Explanation — Why Indian markets need their own handling

> Diátaxis: **Explanation.** Why a generic portfolio app doesn't fit NSE/BSE
> investors, and the specific decisions that make this one fit. For the exact
> resolution functions and tax constants, see
> [reference-modules.md](reference-modules.md).

## The problem

Generic portfolio trackers assume a US-shaped world: a clean ticker like `AAPL`, one
exchange, USD, US tax rules. An Indian retail investor's reality breaks every one of
those assumptions:

- a stock trades on **two** exchanges (NSE and BSE) and the price source needs the
  right suffix (`.NS` / `.BO`);
- broker exports often don't carry a clean ticker at all — some give a **full company
  name**, some give only an **ISIN**;
- two listed companies can share a confusingly similar name (ABB India vs Abbott
  India), so a name lookup alone guesses wrong;
- holding-period and tax rules are **Indian** (LTCG/STCG, a ₹1.25 lakh exemption,
  rates that changed in July 2024), not US;
- the benchmarks people care about are NIFTY / SENSEX / Bank Nifty / Midcap, not the
  S&P 500.

Bolt a generic tracker onto this and it either can't price half the holdings or
silently mis-identifies them. The fixes below all exist to close that gap.

## Symbol identity: NSE/BSE suffixes and the `.NS`/`.BO` resolution

Yahoo Finance — the price source — needs `RELIANCE.NS` (NSE) or `RELIANCE.BO` (BSE),
not bare `RELIANCE`. The app stores **bare** tickers internally and attaches the suffix
at fetch time, trying NSE first and falling back to BSE:

```
   bare ticker "RELIANCE"
        │
        ├─ try RELIANCE.NS  → priced?  ─ yes ─▶ use .NS, remember it (suffix_map)
        │                       │
        │                       no
        ▼
        └─ try RELIANCE.BO  → priced?  ─ yes ─▶ use .BO
```

The resolved suffix per ticker is remembered in a `suffix_map` and threaded through
every later fetch (metadata, TA, dividends) so each ticker is queried on the exchange
that actually priced it — and that map is passed as a `_`-prefixed argument so it never
pollutes the cache key.

## Three-pass name/ISIN resolution

When a broker hands over a company name or an ISIN instead of a ticker,
`market_data.resolve_symbols` runs a **fallback chain**, stopping at the first pass
that produces a confident answer. Each pass is there because the one before it has a
known blind spot:

```
   name / ISIN
        │
        ▼
  ┌───────────────────────────────────────────────────────────────┐
  │ Pass 1 — Yahoo Finance search                                  │
  │   query a few phrasings of the name; collect .NS/.BO candidates │
  │   ── DISAMBIGUATE WITH THE CSV's LTP ──                         │
  │   the candidate whose live price ≈ the CSV's price wins         │
  │   (this is what tells ABB INDIA → ABB, not Abbott India)        │
  │   ISIN: trust Yahoo's match outright (ISIN is unique)           │
  └───────────────────────────────────────────────────────────────┘
        │ miss
        ▼
  ┌───────────────────────────────────────────────────────────────┐
  │ Pass 2 — NSE official master list (EQUITY_L.csv)               │
  │   authoritative for ISIN → symbol, and a fuzzy name fallback;   │
  │   more current than Yahoo (knows recent renames/relistings)     │
  └───────────────────────────────────────────────────────────────┘
        │ miss
        ▼
  ┌───────────────────────────────────────────────────────────────┐
  │ Pass 3 — broader web (DuckDuckGo), PRICE-VALIDATED             │
  │   scrape candidate symbols that exist in the NSE master list;   │
  │   accept one ONLY if its live price ≈ the CSV's price           │
  │   (needs a real CSV price — suspended/₹0 holdings stay unresolved)│
  └───────────────────────────────────────────────────────────────┘
        │ miss
        ▼
   unresolved → shown with CSV value, no live analysis
```

### Why the CSV's LTP is the disambiguator, not name similarity

Name similarity alone is the classic failure: "ABB INDIA" fuzzy-matches *Abbott India*
because the strings look alike, even though they're different companies trading at very
different prices. The broker file already carries the holding's **last traded price**.
That price is a near-unique fingerprint — so the candidate whose live Yahoo price is
within a few percent of the CSV's LTP is almost certainly the right security. Price
proximity is decisive; name similarity is only the tie-breaker when there's no usable
LTP.

This same rule is what makes Pass 3 safe: scraping the web for "stock symbol" could
easily surface a popular ticker for an obscure holding, so the web pass **refuses** to
return anything that doesn't price-match the CSV. A wrong guess becomes *no* guess —
which is the honest outcome.

- **Trade-off:** three network passes per unresolved name are slow on a cold load.
- **Mitigation:** they run in a thread pool, only the genuinely-messy names enter the
  chain (clean tickers skip it), and the whole result is cached 24h.

## The Zerodha "Quantity Long Term" column

Indian capital-gains tax hinges on whether each share was held **>12 months**
(long-term) or not (short-term). Zerodha Console exports already tell you this in a
**Quantity Long Term** column — the broker has done the holding-period accounting. The
app prefers that column outright. Its fallback ladder for splitting a position:

```
   1. "Quantity Long Term" present?  → use it directly (lt = that, st = rest)
   2. else purchase_date present?    → age ≥ 365 days ⇒ long-term, else short-term
   3. else                           → "unknown term", excluded from the tax estimate
```

Honouring the broker's own column avoids re-deriving holding periods the broker already
computed (and possibly disagreeing with the user's contract notes).

## Indian capital-gains tax (post-23 Jul 2024)

The tax constants live in `analytics.py` and reflect the post-July-2024 Budget rates
for listed equity:

```python
LTCG_RATE     = 0.125        # 12.5% on long-term gains
LTCG_EXEMPTION = 125_000     # ₹1.25 lakh annual exemption
STCG_RATE     = 0.20         # 20% on short-term gains
LT_HOLDING_DAYS = 365        # >12 months = long-term for listed equity
```

`tax_breakdown` computes the **unrealised, if-sold-today** split: long-term gains get
the ₹1.25 L exemption applied before the 12.5% rate; short-term gains are taxed at 20%;
gains whose term can't be determined are surfaced separately and *excluded* from the
estimate rather than guessed.

- **Trade-off / honesty:** these are estimates for guidance, not tax advice — the rates
  are hardcoded and will need updating when the law changes, and the UI says so
  explicitly. Hardcoding beats a config knob for values that change once every few
  Budgets; the comment in `analytics.py` is the calibration note for when they do.

## Indian benchmarks

The "has my basket beaten the market?" backtest offers the indices Indian investors
actually track, mapped to their Yahoo symbols:

```python
BENCHMARKS = {
    "NIFTY 50":          "^NSEI",
    "SENSEX":            "^BSESN",
    "NIFTY Bank":        "^NSEBANK",
    "NIFTY Midcap 100":  "^NSEMDCP50",
}
```

A US-default S&P 500 benchmark would be meaningless here; these are the comparisons a
NSE/BSE investor can reason about.

## Related explanations

- [explanation-architecture.md](explanation-architecture.md) — where resolution and
  tax sit in the end-to-end pipeline.
- [explanation-storage-backends.md](explanation-storage-backends.md) — how the
  resolved, consolidated portfolio is persisted per user.
- [reference-modules.md](reference-modules.md) — `resolve_symbols`, `tax_breakdown`,
  `BENCHMARKS` and friends in reference form.
