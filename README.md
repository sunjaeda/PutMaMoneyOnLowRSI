# PutMaMoneyOnLowRSI

A single-page HTML web app that pulls stock data from Yahoo Finance, filters for
**oversold** stocks (14-day RSI ≤ 30), and lists them sorted by market
capitalization.

> **Not investment advice.** This is a screening tool. RSI ≤ 30 finds
> *candidates*, not buys. See [Investing notes](#investing-notes-read-before-trusting-the-list).

---

## Goal

| Requirement | Detail |
|---|---|
| Data source | Yahoo Finance |
| Primary filter | RSI(14) **≤ 30** (oversold) |
| Sort | Market cap (largest → smallest by default) |
| Output | An HTML page listing the matching stocks |

---

## What RSI is (quick refresher)

**RSI (Relative Strength Index)** is a momentum oscillator, range 0–100, that
measures the speed and size of recent price moves.

- **RSI ≤ 30** → conventionally "oversold" (selling may be overdone)
- **RSI ≥ 70** → conventionally "overbought"

Standard formula, 14-period:

```
RSI = 100 − (100 / (1 + RS))
RS  = average gain over 14 periods / average loss over 14 periods
```

Use **Wilder's smoothing** for the averages (not a plain simple moving average) —
that is the textbook RSI and what most charting platforms show, so results match
what users see elsewhere.

```
First avg gain  = simple mean of the first 14 gains
First avg loss  = simple mean of the first 14 losses
Then each step:
  avg gain = (prev avg gain × 13 + current gain) / 14
  avg loss = (prev avg loss × 13 + current loss) / 14
```

You need **at least ~15 daily closes** (ideally 100+ so the smoothing settles)
per ticker to compute a stable RSI(14).

---

## Architecture

```
[ Ticker universe ]
        │
        ▼
[ Fetch OHLC history + market cap ]  ← Yahoo Finance
        │
        ▼
[ Compute RSI(14) per ticker ]
        │
        ▼
[ Filter: RSI ≤ 30 ]
        │
        ▼
[ Sort: market cap desc ]
        │
        ▼
[ Render HTML table ]
```

### Data-source reality check

Yahoo Finance has **no official public API**, and browser calls to its
endpoints are blocked by **CORS**. Pick one of these before coding:

1. **CORS proxy** (fastest to prototype) — route the `query1.finance.yahoo.com`
   chart endpoint through a proxy. Fragile; fine for a demo.
2. **Small backend / serverless function** — a tiny Node/Python endpoint (or a
   library like `yfinance`) fetches and computes, the page just renders. Most
   robust.
3. **Pre-generated JSON** — a scheduled job builds a `data.json` the static page
   loads. Cheapest to host, data is as fresh as the last run.

**Recommendation:** start with option 1 to prove the pipeline, then move to
option 2 or 3.

Useful Yahoo endpoint for history (unofficial):
```
https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}?range=6mo&interval=1d
```
Market cap / summary fields come from the `quoteSummary` / `quote` endpoints.

---

## Displayed columns (proposed)

| Column | Why it's there |
|---|---|
| Ticker | Identity |
| Company name | Readability |
| Price | Context |
| RSI(14) | The core signal |
| Market cap | The sort key |
| % vs 200-day MA | Is the dip *within an uptrend*? (quality oversold) |
| Volume | Capitulation vs. quiet grind |
| Sector | Spot sector-wide selloffs |

The last three are optional for v1 but are what turn a raw list into a *usable*
watchlist — see the notes below.

---

## Investing notes (read before trusting the list)

RSI ≤ 30 is a **screening filter, not a buy signal.** A weak stock can stay
oversold for months while it keeps falling (a "falling knife"). The edge is in
the second layer of confirmation:

- **Temporary vs. structural drop.** Sympathy selloffs, sector rotation, one
  recoverable bad quarter, or broad panic = attractive. Eroding moat, secular
  decline, or accounting red flags = trap.
- **RSI divergence.** Price makes a lower low but RSI makes a *higher* low →
  selling is exhausting. Stronger than the raw 30 line.
- **Trend context (200-day MA).** Oversold *within* a long-term uptrend
  mean-reverts far more reliably than oversold in a confirmed downtrend.
- **Volume.** A capitulation spike at the low often marks a bottom; quiet
  grinding-lower does not.
- **Fundamental quality.** Positive free cash flow, manageable debt, no heavy
  dilution, reasonable valuation vs. the stock's own history. Insider buying
  during the dip is a strong vote of confidence.
- **Liquidity.** Low RSI on illiquid micro-caps is often just noise — consider a
  minimum market-cap or volume floor.

**Optional screen refinement:** require `RSI(14) ≤ 30` **AND** `price > 200-day
MA` to surface *quality* oversold names first.

---

## Roadmap

- [ ] Choose data-fetch approach (proxy / backend / pre-generated JSON)
- [ ] Define the ticker universe (e.g. S&P 500 constituents)
- [ ] Fetch OHLC history per ticker
- [ ] Implement RSI(14) with Wilder's smoothing
- [ ] Filter RSI ≤ 30, sort by market cap
- [ ] Render the HTML table
- [ ] (v2) Add 200-DMA, volume, sector columns
- [ ] (v2) Add divergence / quality-oversold flags
- [ ] Handle rate limits, missing data, and API failures gracefully

---

## Disclaimer

For educational and informational purposes only. Nothing here is financial
advice. Do your own research; markets carry risk.
