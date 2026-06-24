# How-to — Add support for a new broker export

You have a broker export the dashboard doesn't recognise cleanly, and you want it
to parse. Most files already work through the generic fallback — this page covers
both that path and how to add an explicit format when the fallback isn't enough.

All of this lives in [`parsers.py`](../parsers.py); see also the
[broker formats reference](reference-broker-formats.md).

## Prerequisites

- The app installed and running (see
  [Getting started](tutorial-getting-started.md)).
- A copy of the broker export you want to support.
- The column headers of that file in front of you.

## Try the generic fallback first

Before writing any code, just upload the file. If parsing fails or columns look
wrong, open it and check the headers against `GENERIC_ALIASES` in `parsers.py`.

`normalize_generic()` maps your file's columns to the internal schema by matching
header names (case-insensitive, `UPPER_SNAKE_CASE` normalised to spaces) against
these alias lists:

```python
GENERIC_ALIASES = {
    "ticker":   ["ticker", "symbol", "stock", "scrip", "instrument", "sym",
                 "nse symbol", ...],
    "shares":   ["shares", "qty", "quantity", "units", "net qty", ...],
    "avg_cost": ["avg cost", "average price", "buy price", "cost price", ...],
    "ltp":      ["ltp", "last price", "current price", "cmp", "price", ...],
    ...
}
```

A file only needs a ticker/ISIN column plus quantity (and ideally a price) to
work. If your file's header is just an unlisted synonym — say `Scrip Code` for
the ticker — adding that string to the right alias list is the entire fix. Most
new brokers need nothing more.

## Add an explicit broker format

Add an explicit entry only when the generic fallback can't do the job — e.g. two
columns collide on the same alias, the export needs columns the generic schema
doesn't map (sector, long-term quantity), or the header names are too generic to
match safely.

Add an entry to `BROKER_FORMATS` in `parsers.py`. Each entry has two keys:

```python
BROKER_FORMATS = {
    "my_broker": {
        # required: exact column names that must ALL be present for this
        # format to be detected. Pick the most distinctive ones.
        "required": ["Scrip Name", "Net Qty", "Avg Rate"],
        # map: source column -> internal field name
        "map": {
            "Scrip Name": "ticker",
            "Net Qty":    "shares",
            "Avg Rate":   "avg_cost",
            "LTP":        "ltp",
            "Market Value": "current_value",
            "P&L":        "pnl",
        },
    },
}
```

The internal field names you can map to are:
`ticker`, `shares`, `avg_cost`, `ltp`, `current_value`, `pnl`, `isin`, `sector`,
`qty_long_term`, `purchase_date`.

How detection works: `detect_broker()` walks `BROKER_FORMATS` in order and picks
the first format whose `required` columns are all present. If none match, it
falls through to `normalize_generic()`. So make `required` distinctive enough not
to false-match another broker's file.

You don't need to handle `₹`/comma stripping, header rows buried under metadata,
multi-sheet Excel, ISIN-only rows, or NSE series suffixes (`-BE`, `-EQ`) — the
shared parsing in `parse_uploaded_file()` already does all of that.

## Verification

1. Restart the app (`streamlit run app.py`) so the edited `parsers.py` reloads.
2. Drag the broker file into the sidebar **Upload / Data** panel.
3. Confirm it parses: the **Overview** hero value and treemap populate, and the
   **Holdings** table shows the right tickers, quantities, and prices.

A quick non-UI check, if you prefer:

```python
from parsers import parse_uploaded_file
df = parse_uploaded_file(open("my_export.csv", "rb"), "Test")
print(df[["ticker", "shares", "avg_cost", "ltp"]])
```

## Troubleshooting

- **"Could not find a ticker/symbol or ISIN column."** No column matched the
  `ticker` alias list and there's no ISIN to fall back on. Add your header to
  `GENERIC_ALIASES["ticker"]`, or map it explicitly in a `BROKER_FORMATS` entry.
- **Parses, but values are blank or wrong.** A header mapped to the wrong field,
  or two source columns matched the same alias (only the first is kept). Add an
  explicit `BROKER_FORMATS` entry to pin the mapping.
- **Detected as the wrong broker.** Another format's `required` columns also
  appear in your file. Make your new format's `required` list more distinctive,
  or place it so its distinctive columns disambiguate it.
- **Numbers come through as text.** They shouldn't — `₹`, commas, `%`, and
  whitespace are stripped automatically. If they don't, the column was mapped to
  a non-numeric field; recheck your `map`.
- **PDF export doesn't parse.** Text-based PDFs (e.g. IIFL Portfolio+) are
  scraped line by line; scanned/image-only PDFs can't be read — use a CSV/Excel
  export instead.

## See also

- [Broker formats reference](reference-broker-formats.md) — the full table of
  built-in formats and aliases.
- [Module reference](reference-modules.md) — what each module does.
- [Architecture](explanation-architecture.md) — how parsing fits the whole flow.
