# Tutorial — Getting started

By the end of this page you will have the dashboard running on your own machine
and looking at your real portfolio: one hero value, a treemap of what you hold,
and your allocation by stock and sector. Three steps, a few minutes.

You need Python 3 (`python3 --version` to check) and a holdings export from your
broker — a CSV, Excel, or PDF file. That's all.

---

## Step 1 — Install

From the project folder, install the dependencies once:

```bash
pip3 install -r requirements.txt
```

This pulls in Streamlit (the UI), pandas, yfinance, and a few helpers. It runs
once; you don't repeat it on later launches.

> If `pip3` isn't found, use `python3 -m pip install -r requirements.txt`.

## Step 2 — Run

```bash
streamlit run app.py
```

Streamlit starts a local server and opens your browser at
<http://localhost:8501>. If it doesn't open on its own, paste that address into
the browser yourself.

> If `streamlit` isn't on your PATH, use the full path printed during install
> (e.g. `~/Library/Python/3.9/bin/streamlit run app.py`), or
> `python3 -m streamlit run app.py`.

You'll see the dashboard with an empty state, asking for a file.

## Step 3 — Drop in your broker export

In the **sidebar** on the left, find the **Upload / Data** panel and drag your
broker file onto it (or click to browse). Zerodha, Groww, Upstox, Angel One,
HDFC Securities, and most other CSV/Excel/PDF exports are recognised
automatically — each file you add becomes one account.

The moment the file parses, the **Overview** tab fills in:

- the **hero value** — your total portfolio value, front and centre;
- a **treemap heatmap** — each position sized by value, coloured by profit/loss;
- **allocation** by stock and by sector, plus a per-account breakdown.

That's the working result. You're done.

---

## Where to go next

The sidebar has optional **data toggles**. They're off or light by default so the
first load is fast; turn them on when you want more depth:

- **Technical analysis** — SMA 20/50/200 and RSI trend signals. Downloads ~200
  days of history per stock, so the first load is slower for big portfolios.
- **Dividend data** — trailing-twelve-month dividend income and portfolio yield.

Flip one on, and its tab (🔬 Technical, 💰 Dividends) comes alive.

To go further:

- Add a broker format that isn't auto-detected →
  [How-to: add a broker](howto-add-a-broker.md)
- Put the app on a shareable URL → [How-to: deploy](howto-deploy.md)
- Understand how the pieces fit together →
  [Architecture](explanation-architecture.md),
  [Module reference](reference-modules.md),
  [Broker formats reference](reference-broker-formats.md)
