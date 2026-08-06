#!/usr/bin/env python3
"""
fetch_data_massive.py — build data.js from the Massive stock-market data API
(https://massive.com), a native JSON market-data provider (base api.massive.com,
Polygon.io-compatible). This replaces Yahoo entirely: no scraping, structured data.

Per ticker it makes two REST calls:
  1. /v2/aggs/ticker/{t}/range/1/day/{from}/{to}   -> daily OHLCV -> RSI, 200-DMA, volume
  2. /v3/reference/tickers/{t}                      -> market cap, name, sector

Output is the same window.STOCK_DATA shape index.html already reads.

Requirements:
    pip install requests

The API key is read from MASSIVE_TOKEN — never hard-code or commit it. Get/rotate
it at massive.com/dashboard.

    export MASSIVE_TOKEN="your-key"
    python fetch_data_massive.py --keep-all
    python fetch_data_massive.py --sleep 0.1      # faster, for a paid (higher-rate) key

Free tiers are usually rate-limited (~5 requests/min) and end-of-day — the default
--sleep throttles to stay under that. Lower it if your plan allows.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Missing dep. Run:  pip install requests")

API_BASE = "https://api.massive.com"
TOKEN = os.environ.get("MASSIVE_TOKEN")

# Same default universe as fetch_data.py — edit freely, or pass --tickers.
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "UNH",
    "XOM", "JNJ", "WMT", "MA", "PG", "HD", "CVX", "ABBV", "KO", "PEP", "COST",
    "MRK", "ADBE", "CRM", "BAC", "PFE", "TMO", "MCD", "CSCO", "ACN", "ABT",
    "DHR", "NKE", "TXN", "DIS", "WFC", "PM", "VZ", "INTC", "AMD", "QCOM", "IBM",
    "GE", "CAT", "HON", "UNP", "LOW", "BA", "SBUX", "GS", "MS", "BLK", "AXP",
    "T", "C", "CVS", "AMGN", "INTU", "SPGI", "NOW", "ISRG", "GILD", "MDT",
    "BKNG", "PLD", "SYK", "TJX", "MDLZ", "REGN", "VRTX", "TGT", "EL", "PARA",
]


def api_get(path: str, params: dict | None = None, retries: int = 4) -> dict:
    """GET a Massive REST endpoint with Bearer auth and simple 429 backoff."""
    url = API_BASE + path
    headers = {"Authorization": f"Bearer {TOKEN}"}
    for attempt in range(retries):
        r = requests.get(url, params=params or {}, headers=headers, timeout=30)
        if r.status_code == 429:                     # rate limited — back off
            time.sleep(2 ** attempt * 5)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return r.json()


def wilder_rsi(closes, period: int = 14):
    """Textbook RSI(14) with Wilder's smoothing (matches most charts). Pure Python."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def analyze(ticker: str):
    # 1) ~15 months of daily bars, oldest first.
    today = dt.date.today()
    frm = (today - dt.timedelta(days=460)).isoformat()
    to = today.isoformat()
    aggs = api_get(
        f"/v2/aggs/ticker/{ticker}/range/1/day/{frm}/{to}",
        {"adjusted": "true", "sort": "asc", "limit": 50000},
    )
    results = aggs.get("results") or []
    closes = [b["c"] for b in results if b.get("c") is not None]
    vols = [b["v"] for b in results if b.get("v") is not None]
    if len(closes) < 30:
        return None

    rsi = wilder_rsi(closes, 14)
    if rsi is None:
        return None
    price = round(closes[-1], 2)
    ma200 = sum(closes[-200:]) / min(len(closes), 200)
    pct_vs_200 = round((price / ma200 - 1) * 100, 1) if ma200 else None
    avg_vol = int(sum(vols[-20:]) / min(len(vols), 20)) if vols else None

    # 2) Reference details for market cap / name / sector (best-effort).
    name, market_cap, sector = ticker, None, "—"
    try:
        det = api_get(f"/v3/reference/tickers/{ticker}").get("results", {}) or {}
        name = det.get("name") or ticker
        market_cap = det.get("market_cap")
        sector = det.get("sic_description") or "—"
    except Exception:
        pass

    return {
        "ticker": ticker,
        "name": name,
        "price": price,
        "rsi": rsi,
        "marketCap": market_cap,
        "sector": sector,
        "pctVs200": pct_vs_200,
        "avgVolume": avg_vol,
        "aboveMA200": (pct_vs_200 is not None and pct_vs_200 > 0),
    }


def main():
    if not TOKEN:
        sys.exit("Set MASSIVE_TOKEN in your environment first (never commit it).")

    ap = argparse.ArgumentParser(description="Screen stocks by RSI(14) from the Massive market-data API.")
    ap.add_argument("--rsi", type=float, default=30, help="Max RSI to keep (default 30).")
    ap.add_argument("--tickers", nargs="+", help="Custom ticker list.")
    ap.add_argument("--keep-all", action="store_true", help="Write all tickers; filter in the page.")
    ap.add_argument("--sleep", type=float, default=13.0,
                    help="Seconds between tickers (default 13 to respect free ~5/min tiers).")
    ap.add_argument("--out", default="data.js", help="Output file (default data.js).")
    args = ap.parse_args()

    universe = args.tickers or DEFAULT_UNIVERSE
    print(f"Fetching {len(universe)} tickers from the Massive API...")

    rows = []
    for i, tk in enumerate(universe, 1):
        try:
            row = analyze(tk)
        except Exception as e:
            print(f"  [{i}/{len(universe)}] {tk}: skipped ({e})")
            continue
        if row is None:
            print(f"  [{i}/{len(universe)}] {tk}: no usable data")
        else:
            flag = "OVERSOLD" if row["rsi"] <= args.rsi else ""
            print(f"  [{i}/{len(universe)}] {tk}: RSI={row['rsi']} {flag}")
            rows.append(row)
        if i < len(universe):
            time.sleep(args.sleep)

    if not args.keep_all:
        rows = [r for r in rows if r["rsi"] <= args.rsi]

    rows.sort(key=lambda r: (r["marketCap"] or -1), reverse=True)

    payload = {
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "rsiThreshold": args.rsi,
        "universeSize": len(universe),
        "source": "massive.com",
        "stocks": rows,
    }
    with open(args.out, "w") as f:
        f.write("// Auto-generated by fetch_data_massive.py — do not edit by hand.\n")
        f.write("window.STOCK_DATA = ")
        json.dump(payload, f, indent=2)
        f.write(";\n")

    print(f"\nWrote {len(rows)} stock(s) to {args.out}. Open index.html to view.")


if __name__ == "__main__":
    main()
