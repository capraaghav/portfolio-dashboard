# Reference — Broker Formats & Parsed Schema

How `parsers.py` recognises a broker export and what it produces. All facts here
trace to `parsers.py`: `BROKER_FORMATS`, `GENERIC_ALIASES`, and the
classification helpers (`classify_asset`, `is_isin`, `looks_like_symbol`).

A file is parsed in this order (`parse_uploaded_file`):

1. Detect type by extension: `.pdf` → `parse_pdf`; `.xlsx`/`.xls` → Excel header
   detection; otherwise CSV.
2. Find the header row (`find_excel_header` / `find_csv_header_row`) and read the
   table.
3. If `detect_broker(df)` matches a known format, rename columns with that format's
   `map`. Otherwise apply `normalize_generic` (the alias table).
4. Tag every row with the `account` label, keep only the canonical columns, coerce
   numerics, and parse dates.

`detect_broker` returns the first `BROKER_FORMATS` entry whose `required` columns are
all present; if none match, it returns `"generic"`.

---

## Canonical parsed schema

Every parser path produces the same columns (the `_KEEP_COLS` set). One row per
holding-per-account.

| Column | Type | Meaning |
| --- | --- | --- |
| `ticker` | str | Trading symbol (uppercased; `.NS`/`.BO`/`.NSE`/`.BSE` suffixes and NSE series suffixes like `-BE`/`-BZ` stripped). May start as a company name or ISIN, resolved downstream. |
| `shares` | float | Quantity held. |
| `avg_cost` | float | Average buy price per share. May be absent (e.g. HDFC). |
| `ltp` | float | Last traded / current price as reported by the broker. |
| `current_value` | float | Broker-reported market value (fallback when live pricing fails). |
| `pnl` | float | Broker-reported profit/loss. |
| `account` | str | The account label assigned to the source file. |
| `isin` | str | ISIN when the export provides one (used to resolve a missing ticker). |
| `sector` | str | Sector when the export provides one (else filled from Yahoo later). |
| `qty_long_term` | float | Shares held >12 months (Zerodha-style). Drives the tax split. |
| `purchase_date` | datetime | Buy date when present (parsed `dayfirst=True`). Drives XIRR and the tax-term fallback. |

Numeric columns (`shares, avg_cost, ltp, current_value, pnl, qty_long_term`) are
cleaned of `₹`, commas, spaces, and `%` then coerced to numbers. Summary/footer rows
(`total`, `grand total`, blank, etc.) and over-long disclaimer paragraphs are dropped.

**ISIN coalescing.** When `ticker` is missing/blank but `isin` exists, the ISIN is
copied into `ticker` and resolved to a real symbol downstream
(`market_data.resolve_symbols`). If neither a ticker nor an ISIN column is found,
parsing raises a `ValueError`.

---

## Supported brokers (`BROKER_FORMATS`)

Each format lists the columns it requires (all must be present to match) and how its
columns map to the canonical schema.

### Zerodha Kite (`zerodha_kite`)

- **Required:** `Instrument`, `Qty.`
- **Maps:** `Instrument→ticker`, `Qty.→shares`, `Avg. cost→avg_cost`, `LTP→ltp`,
  `Cur. val→current_value`, `P&L→pnl`

### Zerodha Console (`zerodha_console`)

- **Required:** `Symbol`, `ISIN`, `Quantity`, `Average Price`
- **Maps:** `Symbol→ticker`, `ISIN→isin`, `Quantity→shares`, `Average Price→avg_cost`,
  `Last Price→ltp`, `Current Value→current_value`, `P&L→pnl`

### Zerodha Console (detailed) (`zerodha_console_v2`)

The Excel / detailed export that adds Sector, available quantity, and the long-term
quantity column.

- **Required:** `Symbol`, `ISIN`, `Sector`, `Quantity Available`, `Average Price`
- **Maps:** `Symbol→ticker`, `ISIN→isin`, `Sector→sector`, `Quantity Available→shares`,
  `Quantity Long Term→qty_long_term`, `Average Price→avg_cost`,
  `Previous Closing Price→ltp`, `Unrealized P&L→pnl`

### Groww (`groww`)

- **Required:** `Stock Symbol`, `Quantity`, `Average Price`
- **Maps:** `Stock Symbol→ticker`, `Quantity→shares`, `Average Price→avg_cost`,
  `Current Market Price→ltp`, `Current Value→current_value`, `Total Returns→pnl`

### Upstox (`upstox`)

- **Required:** `Sym`, `Qty`, `Avg. Price`
- **Maps:** `Sym→ticker`, `Qty→shares`, `Avg. Price→avg_cost`, `LTP→ltp`,
  `Curr. Val.→current_value`, `P&L→pnl`

### Angel One (`angel`)

- **Required:** `NSE Symbol`, `Quantity`, `Avg. Buy Price`
- **Maps:** `NSE Symbol→ticker`, `Quantity→shares`, `Avg. Buy Price→avg_cost`,
  `Current Price→ltp`, `Current Value→current_value`, `Unrealised P&L→pnl`

### HDFC Securities (`hdfc`)

`Symbol` is the full company **name** (needs name→ticker resolution), and there is no
cost basis — only LTP, value, and quantity.

- **Required:** `Symbol`, `LTP`, `STOCK VAL.`, `AVAIL QTY`
- **Maps:** `Symbol→ticker`, `LTP→ltp`, `STOCK VAL.→current_value`, `AVAIL QTY→shares`

### PDF statements (e.g. IIFL Portfolio+)

Handled by `parse_pdf`, not `BROKER_FORMATS`. Reads each page's text and keeps lines
shaped like `TICKER qty buyprice invested ltp curval …`, mapping positionally to
`ticker, shares, avg_cost, ltp, current_value`. Requires `pdfplumber`; raises a
`ValueError` for scanned (image-only) or unusual layouts.

---

## Generic / unknown exports (`GENERIC_ALIASES`)

When no `BROKER_FORMATS` entry matches, `normalize_generic` renames columns
case-insensitively, treating `_` as a space (so `NSE_SYMBOL`, `COST_PRICE`,
`ISIN_CODE` match). The accepted aliases per canonical field:

| Canonical field | Accepted column names |
| --- | --- |
| `ticker` | ticker, symbol, stock, scrip, instrument, code, stock symbol, trading symbol, sym, nse symbol, bse symbol, script |
| `shares` | shares, qty, qty., quantity, quantity available, units, holding qty, no. of shares, no of shares, net qty, avail qty, available qty, free qty, net quantity |
| `avg_cost` | avg cost, avg. cost, average cost, average price, buy price, cost price, avg price, avg. price, avg buy price, avg. buy price, purchase price |
| `ltp` | ltp, last price, current price, cmp, market price, price, last traded price, current market price |
| `current_value` | current value, cur. val, cur. val., market value, present value, curr. val., current market value, stock val., stock val, stock value, value |
| `pnl` | p&l, pnl, profit/loss, gain/loss, returns, total returns, unrealized p&l, unrealised p&l, net p&l |
| `isin` | isin, isin code, isin_code |
| `sector` | sector, industry |
| `qty_long_term` | quantity long term, long term qty, lt quantity |
| `purchase_date` | purchase date, buy date, trade date, date, order execution time, transaction date |

To add a new named broker instead of relying on the generic path, see
[howto-add-a-broker.md](howto-add-a-broker.md).

---

## Classification & symbol helpers

These decide whether a value is a clean ticker, an ISIN, or a verbose company name —
and what asset class a holding is.

- **`is_isin(s)`** — true for an Indian ISIN matching `^IN[A-Z][0-9A-Z]{9}$` (12
  characters, starts with `IN`), e.g. `INE002A01018`. Used to trigger ISIN-based
  resolution and to trust Yahoo's exact match for it.
- **`looks_like_symbol(s)`** — true when the value is already a clean ticker: no
  spaces, 1–15 characters, only `[A-Z0-9&.\-]`. So `RELIANCE` and `BAJAJ-AUTO` pass;
  `ABB INDIA LIMITED EQ NEW RS. 2/-` does not.
- **`classify_asset(name)`** — returns:
  - `"Mutual Fund"` if the name contains `MUTUAL FUND`, `MUTUALFUND`, or ` MF `;
  - `"Bond/NCD"` if it contains `NCD`, `DEBENTURE`, `BOND`, or a `FVRS<digits>`
    pattern;
  - `"Equity"` otherwise.

  The "Equity only" sidebar toggle uses this to drop funds and bonds (which can't be
  priced as stocks). See [reference-config.md](reference-config.md).
- **`clean_company_name(name)`** — strips broker instrument junk (`-EQ`, ` EQUITY`,
  face values, trailing series codes; keeps up to and including `LIMITED`/`LTD`) to a
  searchable name, e.g. `ABB INDIA LIMITED EQ NEW RS. 2/-` → `ABB INDIA LIMITED`.

---

## Related

- [reference-modules.md](reference-modules.md) — per-module reference (parser entry
  points live in `parsers.py`; resolution in `market_data.py`).
- [reference-config.md](reference-config.md) — runtime config, the "Equity only"
  toggle, and cache TTLs.
- [explanation-architecture.md](explanation-architecture.md) — how parsing,
  resolution, and pricing fit together.
- [howto-add-a-broker.md](howto-add-a-broker.md) — step-by-step for a new export
  format.
