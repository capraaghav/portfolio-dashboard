# 📈 Portfolio Dashboard — Setup (for everyone)

A private stock portfolio dashboard for Indian markets (NSE/BSE). It runs entirely
on **your own computer** — your holdings are never uploaded anywhere.

---

## Step 1 — Install Python (one time)

- **Mac:** Python 3 is usually already installed. If not, get it from
  <https://www.python.org/downloads/>.
- **Windows:** install from <https://www.python.org/downloads/> and **tick
  "Add Python to PATH"** on the first screen of the installer.

## Step 2 — Start the dashboard

- **Mac:** double-click **`run.command`**.
  *(First time only: right-click it → **Open** → **Open**, to get past macOS's
  "unidentified developer" warning.)*
- **Windows:** double-click **`run.bat`**.

The first launch installs what it needs (~1 minute), then opens your browser at
**http://localhost:8501**.

### Prefer the terminal? (any OS)
```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Step 3 — Use it

Drag your broker export (CSV or Excel) into the **sidebar**. Supported: Zerodha,
HDFC Securities, Reliance Securities, Groww, Upstox, Angel One, or any file with
Symbol/ISIN + Quantity + Price columns. Each file = one account; upload several to
combine them.

---

**Privacy:** everything runs locally. The only internet calls are to Yahoo Finance
for live prices and fundamentals — your portfolio itself never leaves your machine.

To stop it, close the terminal window that opened (or press `Ctrl+C` in it).

Full feature list and notes are in **README.md**.
