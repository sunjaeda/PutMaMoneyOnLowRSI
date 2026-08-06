# Project Log & Handoff — PutMaMoneyOnLowRSI

A working record of this low-RSI stock screener: what it is, the key decisions,
current state, and open threads. Written so the project can be picked up in
Cowork (or a fresh session) without losing context.

- **Repo:** `sunjaeda/putmamoneyonlowrsi`
- **Working branch (also the repo's default branch):** `claude/stock-screener-rsi-0o8tac`
- **Hosted preview (sample data):** https://claude.ai/code/artifact/e2dcc1e9-1ca6-472f-802a-e11819ec4a49

---

## 1. What the project is

A single-page web app that screens for **oversold** stocks (RSI(14) ≤ 30) and
ranks them by an **attractiveness score**. Data comes from the **Massive**
market-data API. The fetcher is run **manually** whenever fresh numbers are
wanted — there is no scheduled job.

**Core principle:** RSI ≤ 30 is a *screening filter to build a watchlist*, not a
buy signal. Oversold stocks can keep falling ("falling knife"). The value is in
the second layer of confirmation — trend, divergence, volume, fundamentals.

---

## 2. Files

| File | Purpose |
|---|---|
| `index.html` | Self-contained page. Reads `data.js`. RSI slider, search, sort, quality filter, color-graded attractiveness tiers. |
| `fetch_data.py` | Pulls from the Massive API, computes RSI(14) (Wilder), writes `data.js`. Pure `requests` + stdlib. |
| `data.js` | Generated data (`window.STOCK_DATA`). A sample ships so the page works before the first fetch. |
| `README.md` | Quick start, scoring, hosting, investing notes. |
| `PROJECT_LOG.md` | This file. |

**Why a `.js` file (not `.json`):** assigning to `window.STOCK_DATA` in a `.js`
file loads via `<script src>` when you double-click `index.html` — no server, no
CORS.

---

## 3. Data source — Massive (`massive.com`)

Native stock-market data API (base `api.massive.com`, Bearer auth,
Polygon.io-compatible). Per ticker, `fetch_data.py` calls:

- `/v2/aggs/ticker/{t}/range/1/day/{from}/{to}` → daily bars → RSI, 200-DMA, volume
- `/v3/reference/tickers/{t}` → market cap, name, sector

Key is read from the `MASSIVE_TOKEN` env var only — never committed. Free tiers
are ~5 req/min and end-of-day; the script throttles with `--sleep` (default 13s
after each call → ~13 min for the top-30 universe; lower for paid keys).

**Default universe:** top ~30 S&P 500 names by market cap (`DEFAULT_UNIVERSE`).
Massive uses Polygon-style tickers (e.g. `BRK.B`).

---

## 4. Attractiveness score

Client-side in `scoreStock()` / `tierOf()` in `index.html`. A transparent
weighted 0–100 blend; missing inputs dropped and re-normalized.

| Input | Weight | Higher score when… |
|---|---:|---|
| RSI(14) | 40% | more oversold (RSI 15 → full marks, 40 → none) |
| Market cap | 30% | larger cap (log-scaled) |
| Trend vs 200-day MA | 20% | price above the 200-DMA |
| Liquidity / volume | 10% | higher average volume (log-scaled) |

- **RSI hard floor = 15** (`RSI_FLOOR`): below 15, deeper oversold gives no extra
  credit (falling-knife guard).
- **Tiers:** Strong ≥70 (green `#0ca30c`), Fair 50–69 (amber `#fab219`), Weak
  30–49 (orange `#ec835a`), Poor <30 (red `#d03b3b`) — validated status palette,
  label + number always shown, left row-stripe by tier. Default sort by score.

---

## 5. Running & hosting

- **Run:** `pip install requests`, `export MASSIVE_TOKEN=…`, `python fetch_data.py`.
- **View:** double-click `index.html` (offline-friendly), or serve the folder
  (`python -m http.server`) — on your own machine, not a cloud session.
- **Host (optional):** static site, so `index.html` + `data.js` drop onto GitHub
  Pages / Netlify / Vercel / Cloudflare Pages. Refresh = re-run the fetcher,
  re-commit/upload `data.js`. **No workflow, no schedule** (removed by request).

---

## 6. Open threads / next steps

- [ ] **First real fetch** — set `MASSIVE_TOKEN` and run `fetch_data.py`; confirm
      the field mapping (`results[].c` closes, `results.market_cap`).
- [ ] **RSI divergence** as a 5th scoring input (price lower-low + RSI higher-low).
- [ ] **Expand the universe** beyond the top 30 (mind Massive rate limits).
- [ ] **Optional:** volume-spike/capitulation flag; live single-quote on row click.

---

## 7. History notes

- The project uses **Massive exclusively** for data.
- A **scheduled GitHub Actions workflow** (auto-fetch + deploy) existed but was
  **removed** by request; runs are manual now.
- Development happens in a remote sandbox whose network policy blocks external
  data hosts, so live fetches can't run there — they work on a normal machine.

_Not financial advice. A screening/ranking heuristic, not a buy signal._
