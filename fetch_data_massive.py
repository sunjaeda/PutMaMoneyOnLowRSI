#!/usr/bin/env python3
"""
fetch_data_massive.py — build data.js using the Massive Web Render API as the
data-access layer instead of calling Yahoo Finance directly.

Massive (https://joinmassive.com) is a web-access/proxy service: you hand it a
URL and it fetches the page server-side from a residential IP, handling
JS/anti-bot/geo, and returns the body. We use it two ways per ticker:

  1. format=raw      on Yahoo's price-history JSON endpoint  -> RSI, 200-DMA, volume
  2. format=markdown on the Yahoo quote page                 -> market cap, sector

The output is the same window.STOCK_DATA shape that index.html already reads, so
nothing on the page changes.

Requirements:
    pip install requests

The API token is read from the MASSIVE_TOKEN environment variable — never hard-code
it and never commit it. Get/rotate it at dashboard.joinmassive.com -> Developer -> API Keys.

    export MASSIVE_TOKEN="your-token"        # macOS/Linux
    python fetch_data_massive.py             # RSI <= 30
    python fetch_data_massive.py --keep-all  # keep every ticker; filter in the page
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    sys.exit("Missing dep. Run:  pip install requests")

MASSIVE_ENDPOINT = "https://render.joinmassive.com/browser"
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


def massive_fetch(target_url: str, fmt: str = "raw", geo: str = "US") -> str:
    """Fetch a URL through Massive and return the response body as text."""
    resp = requests.get(
        MASSIVE_ENDPOINT,
        params={"url": target_url, "format": fmt, "geo": geo},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


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


def parse_market_cap(markdown: str):
    """Pull 'Market Cap' from the Yahoo quote page markdown, e.g. '3.27T' -> 3.27e12."""
    m = re.search(r"Market Cap[^0-9]{0,20}([0-9][0-9.,]*)\s*([TBMK]?)", markdown, re.I)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    mult = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3, "": 1.0}[m.group(2).upper()]
    return num * mult


def parse_sector(markdown: str):
    m = re.search(r"Sector[^A-Za-z]{0,10}([A-Z][A-Za-z ]{2,40})", markdown)
    return m.group(1).strip() if m else "—"


def _extract_json(text: str):
    """Massive's raw mode should return the body verbatim; be defensive anyway."""
    try:
        return json.loads(text)
    except Exception:
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j != -1:
            return json.loads(text[i:j + 1])
        raise


def analyze(ticker: str):
    # 1) Price history via Yahoo's chart JSON, fetched through Massive.
    chart_url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(ticker)}?range=1y&interval=1d"
    )
    data = _extract_json(massive_fetch(chart_url, fmt="raw"))
    result = data["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    closes = [c for c in quote.get("close", []) if c is not None]
    vols = [v for v in quote.get("volume", []) if v is not None]
    if len(closes) < 30:
        return None

    rsi = wilder_rsi(closes, 14)
    if rsi is None:
        return None
    price = round(closes[-1], 2)
    ma200 = sum(closes[-200:]) / min(len(closes), 200)
    pct_vs_200 = round((price / ma200 - 1) * 100, 1) if ma200 else None
    avg_vol = int(sum(vols[-20:]) / min(len(vols), 20)) if vols else None

    # 2) Market cap + sector from the quote page markdown, fetched through Massive.
    market_cap, sector = None, "—"
    try:
        md = massive_fetch(f"https://finance.yahoo.com/quote/{ticker}/", fmt="markdown")
        market_cap = parse_market_cap(md)
        sector = parse_sector(md)
    except Exception:
        pass  # history is enough to score; market cap is a bonus column

    return {
        "ticker": ticker,
        "name": result["meta"].get("shortName") or ticker,
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

    ap = argparse.ArgumentParser(description="Screen stocks by RSI(14) via the Massive Web Render API.")
    ap.add_argument("--rsi", type=float, default=30, help="Max RSI to keep (default 30).")
    ap.add_argument("--tickers", nargs="+", help="Custom ticker list.")
    ap.add_argument("--keep-all", action="store_true", help="Write all tickers; filter in the page.")
    ap.add_argument("--out", default="data.js", help="Output file (default data.js).")
    args = ap.parse_args()

    universe = args.tickers or DEFAULT_UNIVERSE
    print(f"Fetching {len(universe)} tickers via Massive...")

    rows = []
    for i, tk in enumerate(universe, 1):
        try:
            row = analyze(tk)
        except Exception as e:
            print(f"  [{i}/{len(universe)}] {tk}: skipped ({e})")
            continue
        if row is None:
            print(f"  [{i}/{len(universe)}] {tk}: no usable data")
            continue
        flag = "OVERSOLD" if row["rsi"] <= args.rsi else ""
        print(f"  [{i}/{len(universe)}] {tk}: RSI={row['rsi']} {flag}")
        rows.append(row)
        time.sleep(0.2)  # be polite to the API

    if not args.keep_all:
        rows = [r for r in rows if r["rsi"] <= args.rsi]

    rows.sort(key=lambda r: (r["marketCap"] or -1), reverse=True)

    payload = {
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "rsiThreshold": args.rsi,
        "universeSize": len(universe),
        "source": "massive",
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
