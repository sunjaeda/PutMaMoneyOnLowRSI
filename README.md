# PutMaMoneyOnLowRSI

A single-page HTML web app that pulls stock data from Yahoo Finance, filters for
**oversold** stocks (14-day RSI ≤ 30), and lists them sorted by market
capitalization.

> **Not investment advice.** This is a screening tool. RSI ≤ 30 finds
> *candidates*, not buys. See [Investing notes](#investing-notes-read-before-trusting-the-list).

---

## Quick start

You need **Python 3** and internet access (on your own computer — not every
network can reach Yahoo).

```bash
# 1. Install the two libraries the fetcher needs
pip install yfinance pandas

# 2. Pull data and generate data.js
python fetch_data.py                 # keeps only RSI <= 30
# or:
python fetch_data.py --keep-all      # keep every ticker; filter live in the page

# 3. Open the page — just double-click it, no server needed
#    (index.html reads the data.js the script just wrote)
```

**Files:**

| File | What it is |
|---|---|
| `index.html` | The page. Open it in any browser. Adjustable RSI slider, search, sort-by-column, "quality only" toggle. |
| `fetch_data.py` | Fetches from Yahoo, computes RSI(14), writes `data.js`. |
| `data.js` | The generated data (a sample ships in the repo so the page works before your first fetch). |

**To refresh prices**, just re-run `python fetch_data.py` and reload the page.

### Alternative fetcher: Massive market-data API (recommended, not Yahoo)

`fetch_data_massive.py` pulls from [Massive](https://massive.com) — a native
stock-market data API (base `api.massive.com`, Bearer auth, Polygon.io-
compatible). This drops Yahoo entirely: structured JSON, no scraping. Per ticker
it gets daily bars (`/v2/aggs/...`) for RSI/200-DMA/volume and reference details
(`/v3/reference/tickers/...`) for market cap, writing the identical `data.js`.

```bash
pip install requests
export MASSIVE_TOKEN="your-key"          # from massive.com/dashboard
python fetch_data_massive.py --keep-all
python fetch_data_massive.py --sleep 0.1 # faster, for a paid (higher-rate) key
```

Free tiers are typically rate-limited (~5 requests/min) and end-of-day, so the
default `--sleep 13` throttles between tickers; lower it if your plan allows.

> **Never commit the key.** It's read only from the `MASSIVE_TOKEN` environment
> variable. In GitHub Actions, add it as a repository **Secret** named
> `MASSIVE_TOKEN` (Settings → Secrets and variables → Actions → New repository
> secret). When that secret exists the workflow uses Massive automatically;
> otherwise it falls back to the direct Yahoo fetch. If a key is ever exposed,
> rotate it at massive.com/dashboard.

> Why the Python step? Browsers block direct calls to Yahoo Finance (CORS), and
> Yahoo has no official public API. Letting a tiny script fetch the data — and
> having the page read a local file — sidesteps all of that with zero servers to
> run or deploy. See [Architecture](#architecture) for the alternatives.

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

## Hosting it online (no PC, no Python on your side)

The page is a static site, so any static host works. Two paths:

### Option A — Auto-refreshing on GitHub Pages ⭐ (recommended)

GitHub runs the fetcher for you on a schedule (free), so the data stays fresh
with zero effort. A workflow is already included at
`.github/workflows/deploy.yml`. To turn it on:

1. **Merge this branch into `main`.** (Scheduled workflows only run on the
   default branch.)
2. In your repo on GitHub: **Settings → Pages → Build and deployment →
   Source → "GitHub Actions".**
3. Go to the **Actions** tab, open **"Refresh data & deploy to Pages"**, and
   click **Run workflow** once to publish immediately.

Your site goes live at `https://<your-username>.github.io/PutMaMoneyOnLowRSI/`
and re-fetches **once per weekday at 11:00 AM US Eastern**, while the S&P market
is open — plenty for a daily RSI screen. (GitHub's scheduler is UTC and ignores
daylight saving, so the workflow lists both candidate hours and a gate job runs
the deploy only when it's truly 11 AM in New York.) Click **Run workflow**
anytime for an on-demand refresh.

### Option B — Vercel (auto-refreshing too)

Vercel hosts the static site and auto-redeploys whenever the repo changes. The
included workflow refreshes `data.js` at 11 AM ET and **commits it back to the
repo**, which is exactly the signal Vercel redeploys on — so data stays fresh
with no PC and no Vercel-side cron.

1. Merge this branch into `main`.
2. On [vercel.com](https://vercel.com): **Add New → Project → Import** your
   GitHub repo.
3. Framework preset: **Other**. Leave build command empty and output directory
   as the repo root (there's no build step — it's plain HTML). Click **Deploy**.

Vercel gives you a `https://<project>.vercel.app` URL. Every 11 AM data commit
(and any manual **Run workflow**) triggers an automatic redeploy.

> The workflow keeps deploying to GitHub Pages *as well*, so both hosts stay in
> sync. If you only want Vercel, delete the `configure-pages` /
> `upload-pages-artifact` / `deploy-pages` steps from
> `.github/workflows/deploy.yml`.

### Option C — Any static host, manual data

Commit a `data.js` (run `python fetch_data.py` once, or ship the sample) and
drop `index.html` + `data.js` onto **GitHub Pages, Netlify, Vercel, or
Cloudflare Pages** — all have free tiers. The data is frozen until you upload a
new `data.js`. No servers, no build step.

> Either way there is **no server to run** — the page only ever reads a static
> `data.js`.

---

## Displayed columns

| Column | Why it's there |
|---|---|
| Ticker | Identity |
| Company name | Readability |
| **Attractiveness** | Color-graded 0–100 score (see below); the default sort |
| Price | Context |
| RSI(14) | The core signal |
| Market cap | A scoring input; click to sort by it |
| % vs 200-day MA | Is the dip *within an uptrend*? (quality oversold) |
| Sector | Spot sector-wide selloffs |

## Attractiveness score

Each stock gets a transparent, weighted **0–100 score** rendered as a
color-graded tier — **Strong** (green) / **Fair** (amber) / **Weak** (orange) /
**Poor** (red) — with the tier label and number always shown, so meaning never
depends on color alone. Rows are also striped on the left edge by tier for quick
scanning, and the table sorts by score by default.

| Input | Weight | Higher score when… |
|---|---:|---|
| RSI(14) | 40% | more oversold (RSI ~15 → full marks, ~40 → none) |
| Market cap | 30% | larger cap (log-scaled; less likely a value trap) |
| Trend vs 200-day MA | 20% | price is above the 200-DMA (a dip *within* an uptrend) |
| Liquidity / volume | 10% | higher average volume (log-scaled; easier to trade) |

**RSI hard floor:** below **RSI 15**, deeper oversold gives *no* extra credit —
a guard so a falling knife (RSI 8, still collapsing) can't out-score a healthy
dip. Set by `RSI_FLOOR` in `index.html`.

Missing inputs are dropped and the remaining weights re-normalized. The weights
and tier cut-offs live in `scoreStock()` / `tierOf()` in `index.html` — tweak
them freely. **It's a heuristic to rank a watchlist, not a buy signal.**

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
