# 📈 Portfolio Dashboard — Indian Markets (NSE/BSE)

A **local-only** stock portfolio dashboard for Indian brokers (Zerodha, Groww,
Upstox, Angel One, or any CSV). Consolidates holdings across accounts, pulls live
NSE/BSE prices, and adds technical, fundamental, tax, risk, and analyst analysis.

**Your data never leaves your machine.** The only outbound calls are to Yahoo
Finance for prices/fundamentals — your holdings are never uploaded anywhere.

---

## Quick start

```bash
# 1. Install dependencies (first time only)
pip3 install -r requirements.txt

# 2. Run
streamlit run app.py
```

It opens automatically at <http://localhost:8501>. If `streamlit` isn't on your
PATH, use the full path printed during install, e.g.:

```bash
~/Library/Python/3.9/bin/streamlit run app.py
```

Then **drag your broker export** (CSV/Excel) into the sidebar.

---

## Features

| Tab | What it shows |
|-----|---------------|
| **📊 Overview** | Treemap heatmap (size = value, colour = P&L), allocation by stock & sector, per-account breakdown |
| **📋 Holdings** | Full table — search, sort, account filter, optional fundamentals (P/E, P/B, Mkt Cap, Beta, 52w), **Excel export**, **manual price override** for un-priced tickers |
| **📈 Performance** | Auto-saved daily **snapshots** → value timeline; **XIRR** (needs purchase dates); **benchmark backtest** of your current basket vs NIFTY 50 / SENSEX / Bank Nifty / Midcap |
| **🔬 Technical** | SMA 20/50/200 + RSI 14 trend signals (Strong Bull → Strong Bear), vs-50MA and RSI charts |
| **🎯 Analysts** | 12-month consensus price targets (low/mean/high), upside %, Buy/Hold/Sell consensus |
| **🧮 Tax** | **LTCG/STCG split** (uses Zerodha's *Quantity Long Term* column) + estimated tax; tax-loss harvesting candidates |
| **⚠️ Risk** | Concentration (largest position, top-5 weight, effective # holdings / HHI), portfolio beta, sector concentration, warnings |
| **💰 Dividends** | TTM dividend income per stock, portfolio yield, income chart |
| **🔍 Stock Detail** | Candlestick (1y) with SMA + your avg-cost line, 52-week gauge, fundamentals, analyst consensus, dividend history, recent news |
| **👁️ Watchlist** | Track stocks you don't own — live price, day change, analyst target. Saved locally |
| **⚖️ Rebalance** | Set target weights, see drift + the ₹ to buy/sell per holding |

### Sidebar data toggles
- **Sector, names, analyst targets & fundamentals** (on by default) — one Yahoo `.info` call per stock, cached 1 hour.
- **Technical analysis** (off) — downloads 200 days of history per stock (~30 s first load for big portfolios).
- **Dividend data** (off) — dividend history per stock.

Turn the heavier ones off for a faster load; turn them on when you want that analysis.

---

## Supported broker exports

Auto-detected: **Zerodha Kite**, **Zerodha Console** (incl. the detailed Excel
with Sector + Long-Term columns), **HDFC Securities**, **Reliance Securities**,
**Groww**, **Upstox**, **Angel One**. Any other broker works too as long as the
file has a Symbol/ISIN + Quantity + Price column — names are fuzzy-matched, the
header row and sheet are auto-detected even under metadata rows, and
`UPPER_SNAKE_CASE` columns (`NSE_SYMBOL`, `COST_PRICE`, `ISIN_CODE`) are handled.
Each uploaded file = one account; a stock held in multiple accounts is
consolidated into one row with a per-account breakdown.

**Files that use a full company name or only an ISIN instead of a ticker** are
automatically resolved to the right NSE/BSE symbol via Yahoo search:
- **Company names** (e.g. HDFC's `"ABB INDIA LIMITED EQ NEW RS. 2/-"`) — the
  file's own LTP disambiguates look-alikes, so "ABB India" resolves to **ABB**,
  not Abbott India.
- **ISINs** (e.g. Reliance's depository export with a blank symbol but
  `INE263A01024`) — resolved directly since an ISIN uniquely identifies the
  security (→ BEL).

Mutual funds and bonds/NCDs are detected and shown with their CSV value (no live
equity data), and can be removed entirely with the **Equity only** sidebar
toggle. Newly-listed/demerged names not yet on Yahoo are kept at CSV value and
flagged.

**Files without a cost basis** (HDFC's holdings export has only LTP + value, no
buy price) still work fully for valuation, allocation, technicals, analyst
targets, dividends, and risk — only Gain/Loss, tax, and XIRR are unavailable
until you provide average cost (e.g. via a Console/tradebook export).

---

## Notes & limitations

- **Live prices / fundamentals / targets** come from Yahoo Finance (`yfinance`),
  free and no API key. Coverage is best for large/mid-cap NSE stocks; some
  small-caps return no price (use the **manual price override** in Holdings) or
  no analyst/fundamental data.
- **Analyst targets are 12-month** consensus — the closest free proxy to a
  6-month view; no free source publishes 6-month targets for Indian equities.
- **Performance history** builds up over time from daily snapshots (stored in
  `data/snapshots.json`). The **benchmark backtest** works immediately by
  replaying your *current* quantities over history (it ignores when you actually
  bought — treat it as "what if I'd held this basket the whole period").
- **XIRR** needs purchase dates, which holdings exports don't include. Upload your
  broker **tradebook** (which has trade dates) and it computes automatically.
- **Tax figures are estimates, not advice.** Indian listed-equity rates
  (post-Jul 2024): LTCG 12.5% above ₹1.25 L/yr, STCG 20%. Verify with your CA.
- The app **never places orders or moves money** — rebalancing only suggests.

Everything is stored under `./data/` (snapshots, last session, watchlist,
overrides). Delete that folder to reset.
