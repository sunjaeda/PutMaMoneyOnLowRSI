# PutMaMoneyOnLowRSI

A single-page web app that screens for **oversold** stocks (14-day RSI ≤ 30) and
ranks them by an **attractiveness score**. Data comes from the
[Massive](https://massive.com) market-data API. You run the fetcher whenever you
want fresh numbers — there's no scheduled job.

> **Not investment advice.** This is a screening/ranking tool. RSI ≤ 30 finds
> *candidates*, not buys. See [Investing notes](#investing-notes).

---

## Quick start

You need **Python 3** and a free Massive API key from
[massive.com/dashboard](https://massive.com/dashboard).

```bash
pip install requests

export MASSIVE_TOKEN="your-key"       # macOS/Linux (never commit this)
python fetch_data.py                  # keeps only RSI <= 30
python fetch_data.py --keep-all       # keep every ticker; filter live in the page
python fetch_data.py --sleep 0.1      # faster, for a paid (higher-rate) key
```

Then open the page — **double-click `index.html`** (works offline; `data.js`
loads via a `<script>` tag, so no server and no CORS issues). To refresh, re-run
`python fetch_data.py` and reload.

> **Rate limits:** free tiers are usually ~5 requests/min and end-of-day. Each
> ticker makes 2 calls, so the default `--sleep 13` keeps a free tier safe —
> about **13 minutes for the top-30 universe**. Lower `--sleep` on a paid plan.

**Windows (PowerShell):** `setx MASSIVE_TOKEN "your-key"` (reopen the shell), then
`python fetch_data.py`.

---

## Files

| File | What it is |
|---|---|
| `index.html` | The page. Open in any browser. RSI slider, search, click-to-sort, "quality only" filter, color-graded attractiveness tiers. |
| `fetch_data.py` | Pulls daily bars + reference data from Massive, computes RSI(14) (Wilder smoothing), writes `data.js`. |
| `data.js` | The generated data (`window.STOCK_DATA`). A sample ships so the page works before your first fetch. |

**Default universe:** the top ~30 S&P 500 names by market cap, set in
`DEFAULT_UNIVERSE` in `fetch_data.py`. Edit it or pass `--tickers AAPL MSFT …`.

---

## RSI, briefly

**RSI (Relative Strength Index)** is a 0–100 momentum oscillator. **≤ 30** is
conventionally "oversold," **≥ 70** "overbought." This project uses the textbook
14-period RSI with **Wilder's smoothing**, computed from daily closes — matching
what most charting platforms show.

---

## Attractiveness score

Each stock gets a transparent, weighted **0–100 score**, shown as a color-graded
tier — **Strong** (green) / **Fair** (amber) / **Weak** (orange) / **Poor**
(red) — with the tier label and number always visible, so meaning never depends
on color alone. Rows are striped on the left edge by tier, and the table sorts by
score by default.

| Input | Weight | Higher score when… |
|---|---:|---|
| RSI(14) | 40% | more oversold (RSI ~15 → full marks, ~40 → none) |
| Market cap | 30% | larger cap (log-scaled; less likely a value trap) |
| Trend vs 200-day MA | 20% | price above the 200-DMA (a dip *within* an uptrend) |
| Liquidity / volume | 10% | higher average volume (log-scaled) |

**RSI hard floor:** below **RSI 15**, deeper oversold gives *no* extra credit — a
guard so a falling knife can't out-score a healthy dip (`RSI_FLOOR` in
`index.html`). Missing inputs are dropped and remaining weights re-normalized.
Weights and tier cut-offs live in `scoreStock()` / `tierOf()` in `index.html`.

---

## Hosting it online (optional)

The page is a static site — `index.html` + `data.js` — so any static host works
(**GitHub Pages, Netlify, Vercel, Cloudflare Pages**; all have free tiers). There
is **no server and no build step**. Workflow / scheduling was intentionally
removed: refresh on your own terms by running `python fetch_data.py`, committing
the new `data.js` (or re-uploading it), and your host serves the update.

---

## Investing notes

RSI ≤ 30 is a **screening filter, not a buy signal.** A weak stock can stay
oversold for months while it keeps falling. The edge is in confirmation:

- **Temporary vs. structural drop.** Sympathy selloffs / sector rotation / one
  recoverable bad quarter = attractive. Eroding moat / secular decline /
  accounting red flags = trap.
- **RSI divergence** (price lower-low but RSI higher-low) — selling is
  exhausting; stronger than the raw 30 line.
- **Trend context (200-day MA).** Oversold *within* an uptrend mean-reverts more
  reliably than oversold in a downtrend. → the "quality only" filter and a
  scoring input.
- **Volume.** A capitulation spike at the low often marks a bottom; a quiet
  grind lower does not.
- **Fundamental quality.** Positive FCF, manageable debt, no heavy dilution,
  reasonable valuation. Insider buying during the dip is a strong tell.
- **Liquidity floor.** Low RSI on illiquid names is often just noise.

---

## Disclaimer

For educational purposes only. Nothing here is financial advice. Markets carry
risk; do your own research.
