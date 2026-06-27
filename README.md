# 📈 Portfolio Dashboard — Indian Markets (NSE/BSE)

**See everything you own — across every broker — in one honest view.**

A private, local-only dashboard for Indian stock investors. Drop in your broker
export (Zerodha, Groww, Upstox, Angel One, HDFC, IIFL, or any CSV/Excel/PDF) and
instantly get a consolidated picture of your holdings with live NSE/BSE prices,
plus technical, fundamental, tax, risk, dividend, and analyst analysis — and a
built-in stock screener to find new opportunities.

> 🔒 **Your data never leaves your machine.** The only outbound calls are to
> Yahoo Finance for prices and fundamentals. Your holdings, quantities, and costs
> are never uploaded, logged, or shared with anyone.

---

## Table of contents

- [Who this is for](#who-this-is-for)
- [What problem it solves](#what-problem-it-solves)
- [Quick start (5 minutes)](#quick-start-5-minutes)
- [How to get your broker file](#how-to-get-your-broker-file)
- [The dashboard, tab by tab](#the-dashboard-tab-by-tab)
- [Supported brokers & file types](#supported-brokers--file-types)
- [Sidebar toggles — speed vs depth](#sidebar-toggles--speed-vs-depth)
- [Frequently asked questions](#frequently-asked-questions)
- [Troubleshooting](#troubleshooting)
- [Privacy & where your data lives](#privacy--where-your-data-lives)
- [Limitations & honest caveats](#limitations--honest-caveats)
- [Full documentation](#full-documentation)

---

## Who this is for

- **Retail investors in India** holding NSE/BSE stocks across one or more
  brokers who want a single, accurate view instead of logging into each app.
- Anyone tired of broker dashboards that hide P&L, scatter accounts, or can't
  tell you your **tax liability**, **portfolio risk**, or **whether you're
  beating the index**.
- Investors who care about **privacy** — this runs entirely on your own
  computer. Nothing is uploaded.

No coding knowledge needed to use it. If you can install one program and drag a
file, you're set.

---

## What problem it solves

If you hold stocks in more than one place — say some in Zerodha, some in your
spouse's Groww, a few from an old HDFC account — no single screen tells you the
truth. This app:

1. **Consolidates** every account into one portfolio. A stock held in three
   accounts shows as **one row** with a per-account breakdown.
2. **Prices it live** from Yahoo Finance — no manual updates.
3. **Analyzes it** the way a paid tool would: P&L, allocation, technical
   signals, analyst targets, dividend income, risk concentration, and
   **Indian-specific tax** (LTCG/STCG).
4. **Finds new ideas** with a screener that scans the Nifty 500 (or your own
   watchlist) for stocks matching a momentum strategy.

All free, all local.

---

## Quick start (5 minutes)

You need **Python 3** installed (`python3 --version` to check — Macs usually
have it; Windows users grab it from [python.org](https://www.python.org/downloads/)).

```bash
# 1. Install dependencies (first time only)
pip3 install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Your browser opens automatically at **<http://localhost:8501>**.

If your terminal says `streamlit: command not found`, it installed to a folder
not on your PATH. Use the full path printed during install, for example:

```bash
~/Library/Python/3.9/bin/streamlit run app.py
```

**Windows / Mac shortcut:** double-click `scripts/run.command` (Mac) or
`scripts/run.bat` (Windows) instead of typing commands.

Once it's open, **drag your broker export file into the sidebar** — and you'll
see your portfolio in seconds.

---

## How to get your broker file

You need a **holdings** or **tradebook** export. Most brokers let you download
one in a few clicks:

| Broker | Where to find it |
|--------|------------------|
| **Zerodha** | Console → Portfolio → Holdings → **Download**. For tax & XIRR, also grab Console → Reports → **Tradebook**. |
| **Groww** | Stocks → Holdings → **Download / Export**. |
| **Upstox** | Portfolio → Holdings → **Export**. |
| **Angel One** | Portfolio → **Download holdings**. |
| **HDFC Securities** | Portfolio → Holdings → **Export to Excel**. |
| **IIFL** | Portfolio+ → **PDF statement**. |
| **Any other broker** | Any CSV/Excel with a Symbol (or ISIN) + Quantity + Price column works. |

You can upload **more than one file** — each becomes a separate "account," and
overlapping stocks are merged automatically.

---

## The dashboard, tab by tab

| Tab | What it gives you |
|-----|-------------------|
| **📊 Overview** | The big picture: a heatmap treemap (box size = how much you hold, colour = profit/loss), allocation by stock and by sector, and a per-account breakdown. Top KPIs show today's change, number of holdings, accounts, and how many prices loaded live. |
| **📋 Holdings** | Your full table — searchable and sortable, filterable by account. Optional fundamentals (P/E, P/B, market cap, beta, 52-week range). **Export to Excel** in one click. Got a stock with no live price? Use the **manual price override**. |
| **📈 Performance** | Tracks your portfolio value over time via auto-saved daily **snapshots**. Computes **XIRR** (your true annualised return, if you supply purchase dates) and runs a **benchmark backtest** of your current basket against NIFTY 50, SENSEX, Bank Nifty, or Midcap. |
| **🔬 Technical** | Trend signals for each holding — SMA 20/50/200 and RSI 14, classified from **Strong Bull** to **Strong Bear** — plus price-vs-50MA and RSI charts. |
| **🔎 Screener** | Find *new* stocks. Scans the **Nifty 500 / Nifty 50** (or a watchlist you upload) for a momentum setup: the 10-day average crossing the 50-day average **and** RSI in a healthy 50–65 range (positive momentum, not yet overbought). Shows exactly why each stock passed, what got filtered out, and exports results to CSV/Excel. |
| **🎯 Analysts** | 12-month consensus price targets (low / mean / high), implied upside %, and the Buy/Hold/Sell breakdown for each holding. |
| **🧮 Tax** | The India-specific number brokers won't show you: your **LTCG vs STCG split** and estimated tax, plus **tax-loss-harvesting** candidates to offset gains. |
| **⚠️ Risk** | How exposed you really are: largest position, top-5 weight, effective number of holdings (HHI), portfolio beta, sector concentration, and plain-English warnings. |
| **💰 Dividends** | Trailing-twelve-month dividend income per stock, your overall portfolio yield, and an income chart. |
| **🔍 Stock Detail** | Deep-dive on any one stock: 1-year candlestick with SMAs and **your average-cost line**, a 52-week-range gauge, fundamentals, analyst consensus, dividend history, and recent news. |
| **👁️ Watchlist** | Track stocks you *don't* own yet — live price, day change, analyst target. Saved locally between sessions. |
| **⚖️ Rebalance** | Set target weights for your holdings and see the drift, plus the exact ₹ amount to buy or sell to hit them. (Suggestions only — it never places orders.) |

---

## Supported brokers & file types

**Auto-detected formats:** Zerodha Kite, Zerodha Console (including the detailed
Excel with Sector + Long-Term columns), HDFC Securities, Reliance Securities,
IndusInd, IIFL Portfolio+ (PDF), Groww, Upstox, Angel One.

**File types:** CSV, Excel (`.xls`/`.xlsx`), and text-based **PDF** statements.

The parser is forgiving — it auto-detects the header row and sheet even under
broker metadata rows, handles `UPPER_SNAKE_CASE` columns (`NSE_SYMBOL`,
`COST_PRICE`, `ISIN_CODE`), and scrapes PDF tables page-by-page.

**Files with no ticker** still work. The app resolves the right symbol via Yahoo
search:
- **Company names** — e.g. HDFC's `"ABB INDIA LIMITED EQ NEW RS. 2/-"` resolves
  to **ABB** (the file's own price disambiguates look-alikes, so it won't confuse
  ABB India with Abbott India).
- **ISINs** — e.g. a depository export with a blank symbol but `INE263A01024`
  resolves directly to **BEL** (an ISIN uniquely identifies the security).

**Mutual funds and bonds/NCDs** are detected and shown at their CSV value (no
live equity data); hide them entirely with the **Equity only** sidebar toggle.

**Files without a cost basis** (e.g. HDFC holdings exports show only current
value, no buy price) still work fully for valuation, allocation, technicals,
analyst targets, dividends, and risk. Only Gain/Loss, tax, and XIRR stay
unavailable until you supply average cost — upload a Console/tradebook export and
those light up too.

---

## Sidebar toggles — speed vs depth

The dashboard fetches more data the deeper you analyze. To keep loads fast, the
heavier data sources are toggles:

| Toggle | Default | Cost | What it adds |
|--------|---------|------|--------------|
| **Sector, names, analyst targets & fundamentals** | **On** | One Yahoo `.info` call per stock, cached 1 hour | Sectors, company names, P/E, P/B, beta, analyst targets |
| **Technical analysis** | Off | ~200 days of history per stock (≈30 s first load for big portfolios) | The Technical tab signals and charts |
| **Dividend data** | Off | Dividend history per stock | The Dividends tab |

Turn the heavy ones off for a snappy load; flip them on when you want that
analysis. Everything is cached, so the second load is instant. Hit **🔄 Refresh
data** to clear caches and re-fetch.

---

## Frequently asked questions

**Is this free?**
Yes — entirely. No subscription, no API key, no account. Prices come from Yahoo
Finance's free endpoints.

**Do I need to know how to code?**
No. You run two commands once (or double-click the launcher), then it's all
point-and-click in your browser.

**Is my portfolio data sent anywhere?**
No. It stays on your computer in a local `./data/` folder. The app only contacts
Yahoo Finance, and only to ask for *public* prices and fundamentals of the
tickers you hold — never your quantities or costs.

**Can I track multiple brokers / family accounts?**
Yes. Upload one file per account. Overlapping stocks merge into a single row with
a per-account breakdown.

**Why is one of my stocks missing a price?**
Yahoo's coverage is best for large/mid-caps. Some small-caps or freshly-listed
names return no price — use the **manual price override** in the Holdings tab to
fill it in.

**Does it place trades or move money?**
Never. It's read-only. Rebalancing only *suggests* what to buy/sell.

**Can I host it online so others can use it?**
Yes — see [`docs/howto-deploy.md`](docs/howto-deploy.md). It supports a
multi-user hosted mode (each visitor's data stays private to their session) and
an optional Supabase cloud backend with login.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `streamlit: command not found` | It installed off your PATH. Run with the full path, e.g. `~/Library/Python/3.9/bin/streamlit run app.py`. |
| `pip3: command not found` | Python isn't installed or not on PATH. Install Python 3 from [python.org](https://www.python.org/downloads/). |
| Prices show "—" for some stocks | Yahoo has no data for that ticker. Use **manual price override** in Holdings. |
| My broker file isn't recognised | As long as it has Symbol/ISIN + Quantity + Price columns it should parse. See [`docs/howto-add-a-broker.md`](docs/howto-add-a-broker.md). |
| Want to start fresh | Delete the `./data/` folder — that clears snapshots, last session, watchlist, and overrides. |
| App is slow on first load | Turn off **Technical** and **Dividend** toggles; they download per-stock history. Subsequent loads are cached. |

---

## Privacy & where your data lives

Everything is stored locally under `./data/`:
- `snapshots.json` — your daily portfolio-value history (powers Performance)
- last-session parquet — so your portfolio reloads instantly
- watchlist + manual price overrides

This folder is **git-ignored** — it never goes into the repository. Delete it any
time to reset the app to a clean state.

---

## Limitations & honest caveats

- **Live prices, fundamentals, and targets** come from Yahoo Finance (`yfinance`)
  — free, no key, but coverage is best for large/mid-cap NSE stocks. Some
  small-caps return no price or no analyst/fundamental data.
- **Analyst targets are 12-month** consensus — the closest free proxy available;
  no free source publishes 6-month targets for Indian equities.
- **Performance history** accumulates over time from daily snapshots. The
  **benchmark backtest** works immediately by replaying your *current* quantities
  over history — it ignores when you actually bought, so read it as "what if I'd
  held this exact basket the whole period," not your real timed return.
- **XIRR** needs purchase dates, which holdings exports don't carry. Upload your
  **tradebook** (it has trade dates) and XIRR computes automatically.
- **Tax figures are estimates, not advice.** Indian listed-equity rates
  (post-Jul 2024): LTCG 12.5% above ₹1.25 L/year, STCG 20%. Always verify with
  your CA.
- The app **never places orders or moves money.**

---

## Full documentation

In-depth docs live in [`docs/`](docs/README.md), organised by the
[Diátaxis](https://diataxis.fr) framework:

- **Tutorial** — [Getting started](docs/tutorial-getting-started.md)
- **How-to** — [add a broker](docs/howto-add-a-broker.md),
  [deploy](docs/howto-deploy.md), [set up locally](docs/howto-setup.md),
  [host the landing page](docs/howto-host-landing-page.md)
- **Reference** — [modules](docs/reference-modules.md),
  [broker formats](docs/reference-broker-formats.md),
  [configuration](docs/reference-config.md)
- **Explanation** — [architecture](docs/explanation-architecture.md),
  [storage backends](docs/explanation-storage-backends.md),
  [Indian-market specifics](docs/explanation-indian-market-specifics.md)

See also the [product spec & PRD](product/) and the
[design system](docs/design-system.md).
