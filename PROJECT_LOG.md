# Project Log & Handoff — PutMaMoneyOnLowRSI

A working record of the conversation that built this low-RSI stock screener:
what was asked, what was decided (and *why*), the current state, and the open
threads. Written so the project can be picked up in Cowork (or a fresh session)
without losing context.

- **Repo:** `sunjaeda/putmamoneyonlowrsi`
- **Working branch:** `claude/stock-screener-rsi-0o8tac`
- **Hosted preview (sample data):** https://claude.ai/code/artifact/e2dcc1e9-1ca6-472f-802a-e11819ec4a49

---

## 1. What the project is

A single-page web app that screens for **oversold** stocks and ranks them by
an **attractiveness score**. Originally: pull from Yahoo Finance, filter RSI(14)
≤ 30, sort by market cap. It has since grown a weighted scoring model and a
color-graded UI.

**Core principle repeated throughout:** RSI ≤ 30 is a *screening filter to build
a watchlist*, not a buy signal. Oversold stocks can keep falling ("falling
knife"). The value is in the second layer of confirmation — trend, divergence,
volume, fundamentals.

---

## 2. Investing insight that shaped the design

(From the opening discussion — this is the reasoning the scoring model encodes.)

- **Temporary vs. structural drop.** Sympathy selloffs / sector rotation / one
  recoverable bad quarter = attractive. Eroding moat / secular decline /
  accounting red flags = trap.
- **RSI divergence** (price lower-low but RSI higher-low) — strongest single
  confirmation. *Not yet built — see open threads.*
- **Trend context (200-day MA)** — oversold *within* an uptrend mean-reverts
  more reliably than oversold in a downtrend. → became the "quality only" filter
  and a scoring input.
- **Volume** — capitulation spike marks bottoms; quiet grind-down doesn't.
- **Fundamental quality** — positive FCF, low debt, no dilution, reasonable
  valuation; insider buying during the dip is a strong tell.
- **Liquidity floor** — low RSI on illiquid micro-caps is mostly noise.

---

## 3. Files in the repo

| File | Purpose |
|---|---|
| `index.html` | The screener page — self-contained UI, reads `data.js`. |
| `fetch_data.py` | Pulls Yahoo history, computes RSI(14) (Wilder smoothing), writes `data.js`. |
| `data.js` | Generated data (`window.STOCK_DATA`). A sample ships so the page works before the first fetch. |
| `.github/workflows/deploy.yml` | Scheduled refresh + deploy (see §5). |
| `README.md` | Quick start, hosting, scoring, investing notes. |
| `PROJECT_LOG.md` | This file. |

**Why a `.js` file instead of `.json`:** a `.js` file assigning to
`window.STOCK_DATA` loads directly via `<script src>` when you double-click
`index.html` — no local server, no CORS. This was a deliberate choice to keep it
zero-infrastructure.

---

## 4. The attractiveness score (current model)

Computed client-side in `scoreStock()` inside `index.html`. A transparent
weighted blend, 0–100; missing inputs are dropped and remaining weights
re-normalized.

| Input | Weight | Higher score when… |
|---|---:|---|
| RSI(14) | **40%** | more oversold (RSI 15 → full marks, 40 → none) |
| Market cap | **30%** | larger cap (log-scaled; less likely a value trap) |
| Trend vs 200-day MA | **20%** | price above the 200-DMA (dip within an uptrend) |
| Liquidity / volume | **10%** | higher average volume (log-scaled) |

- **RSI hard floor = 15** (`RSI_FLOOR`): below 15, deeper oversold gives *no*
  extra credit — a guard so a falling knife can't out-score a healthy dip.
- **Tiers** (`tierOf()`), rendered as colored dots + label + number, with a
  matching left-edge row stripe:
  - **Strong** 70–100 · green `#0ca30c`
  - **Fair** 50–69 · amber `#fab219`
  - **Weak** 30–49 · orange `#ec835a`
  - **Poor** 0–29 · red `#d03b3b`
- Colors come from a **validated status palette** (colorblind-safe, contrast-
  checked in light/dark). Meaning is never carried by color alone — the label
  and number are always shown.
- Default sort is by score; every column is click-to-sort. Market-cap sort (the
  original requirement) is one click away.

**Weights and cut-offs are easy to tweak** at the top of the `<script>` block.

---

## 5. Hosting & refresh (decisions)

The page is **static**, so any static host serves it. The only question is who
refreshes `data.js`. Current workflow (`.github/workflows/deploy.yml`):

- Runs the Python fetcher **in GitHub's cloud** (no PC needed).
- **Schedule: weekdays at 11:00 AM US Eastern**, while the S&P market is open —
  enough for a daily RSI screen. A `gate` job handles the fact that GitHub cron
  is UTC and ignores daylight saving, so it fires exactly once at 11 AM ET
  year-round.
- Then it **both**: (a) commits the fresh `data.js` back to the repo → a
  connected **Vercel** project auto-redeploys; and (b) deploys to **GitHub
  Pages**. Both hosts stay in sync. (If only Vercel is wanted, delete the three
  Pages steps.)

**To go live (one-time):** merge the branch to `main` → Settings → Pages →
Source: "GitHub Actions" (for Pages) and/or import the repo on Vercel → run the
workflow once.

**Data is not real-time** — it's a daily snapshot, which is correct for RSI
(computed on daily closes). "Live" tick data was discussed and rejected as
overkill/impractical for a whole-universe screen.

---

## 6. Data source (open decision)

Current source is **Yahoo Finance via `yfinance`** — free, no key, but
*unofficial* and can break. The user wants to move off Yahoo. Options discussed:

- **Google Sheets + `GOOGLEFINANCE()`** ⭐ — no programming; the sheet fetches
  data and computes RSI with formulas, published as JSON the page reads. Best
  fit for "no code, not Yahoo."
- **Official API** (Financial Modeling Prep / Twelve Data) — most reliable,
  ~zero code change, needs a free API key. Batch model means a daily limit is
  fine (≈2 calls/stock/day).
- **Claude-as-updater routine** — possible but overkill/fragile; an LLM is the
  wrong tool for shuttling market numbers on a timer.

**Important clarification (MCP):** MCP + Claude *cannot* be the live backend of
a public webpage. MCP is a bridge for Claude *during a session*; a deployed page
has no Claude behind it. Making it live would require building/hosting an app
that calls the Claude API — coding + server + cost.

**Status:** user chose **"just explain, don't build yet."** No data-source
change has been made. Decision still open.

---

## 7. Environment note

Development happened in a remote cloud sandbox whose **network policy blocks
Yahoo Finance**, so the live fetch could not be run here — that's a sandbox
restriction, not a problem with the code. It runs fine on a normal machine or in
GitHub Actions. Likewise, a `localhost` server started in the sandbox is *not*
reachable from the user's browser (different machine); that's why the hosted
Artifact preview exists.

---

## 8. Open threads / next steps

- [ ] **Decide the data source** (§6) — Google Sheets vs. official API. Nothing
      built yet; awaiting the go-ahead.
- [ ] **RSI divergence** as a 5th scoring input (price lower-low + RSI
      higher-low) — the strongest confirmation signal, still unbuilt.
- [ ] **Expand the ticker universe** — currently ~80 large caps in
      `DEFAULT_UNIVERSE`; could grow to the full S&P 500 (fits Twelve Data's
      free tier; would need rate-limit handling).
- [ ] **Optional:** capitulation/volume-spike flag; live single-quote popup on
      row click; strip GitHub Pages if going Vercel-only.
- [ ] **Go live** — merge to `main`, enable the host, run the workflow once.

---

## 9. How to preview it right now

- **Hosted (easiest):** open the Artifact URL at the top of this doc.
- **Locally:** double-click `index.html` (works offline), or from the repo run
  `python -m http.server 8000` and open `http://localhost:8000` — *on your own
  machine*, not in a cloud session.

_Not financial advice. This is a screening/ranking heuristic, not a buy signal._
