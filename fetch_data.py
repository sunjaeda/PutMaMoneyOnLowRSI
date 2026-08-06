#!/usr/bin/env python3
"""
fetch_data.py — pull stock data from Yahoo Finance, compute RSI(14), and write
a data.js file that index.html reads.

Why a .js file (and not .json)?  A .js file assigning to `window.STOCK_DATA`
loads directly from the file system when you double-click index.html — no local
web server, no CORS headaches.

Usage:
    pip install yfinance pandas
    python fetch_data.py                 # default: RSI <= 30, default universe
    python fetch_data.py --rsi 35        # loosen the oversold threshold
    python fetch_data.py --tickers AAPL MSFT NVDA
    python fetch_data.py --keep-all      # write every ticker, filter in the page

The page can also re-filter/re-sort client-side, so --keep-all lets you explore
different thresholds without re-fetching.
"""

import argparse
import datetime as dt
import json
import sys

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    sys.exit("Missing deps. Run:  pip install yfinance pandas")


# Top ~30 S&P 500 names by market cap (approximate, as of 2026 — easily edited,
# or pass --tickers). Yahoo uses BRK-B (not BRK.B).
DEFAULT_UNIVERSE = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "BRK-B",
    "JPM", "LLY", "V", "XOM", "MA", "COST", "WMT", "UNH", "HD", "PG", "JNJ",
    "NFLX", "ABBV", "BAC", "ORCL", "CVX", "KO", "CRM", "AMD", "PLTR", "MRK",
]


def wilder_rsi(closes: pd.Series, period: int = 14) -> float:
    """Textbook RSI(14) using Wilder's smoothing (matches most charts)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # First average = simple mean of the first `period` values.
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    # Then Wilder smoothing for the rest.
    for i in range(period + 1, len(closes)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if pd.isna(last_gain) or pd.isna(last_loss):
        return None
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return round(100 - (100 / (1 + rs)), 2)


def analyze(ticker: str):
    """Return a dict of metrics for one ticker, or None if data is unusable."""
    tk = yf.Ticker(ticker)
    hist = tk.history(period="1y", interval="1d")
    if hist is None or len(hist) < 30:
        return None

    closes = hist["Close"].dropna()
    if len(closes) < 20:
        return None

    rsi = wilder_rsi(closes, 14)
    if rsi is None:
        return None

    price = round(float(closes.iloc[-1]), 2)
    ma200 = closes.rolling(200).mean().iloc[-1]
    pct_vs_200 = round((price / ma200 - 1) * 100, 1) if pd.notna(ma200) else None
    avg_vol = int(hist["Volume"].tail(20).mean()) if "Volume" in hist else None

    # .info can be slow/flaky; guard it.
    try:
        info = tk.info or {}
    except Exception:
        info = {}

    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "price": price,
        "rsi": rsi,
        "marketCap": info.get("marketCap"),
        "sector": info.get("sector") or "—",
        "pctVs200": pct_vs_200,
        "avgVolume": avg_vol,
        "aboveMA200": (pct_vs_200 is not None and pct_vs_200 > 0),
    }


def main():
    ap = argparse.ArgumentParser(description="Screen stocks by RSI(14) from Yahoo Finance.")
    ap.add_argument("--rsi", type=float, default=30, help="Max RSI to keep (default 30).")
    ap.add_argument("--tickers", nargs="+", help="Custom ticker list (overrides default universe).")
    ap.add_argument("--keep-all", action="store_true", help="Write all tickers; filter in the page.")
    ap.add_argument("--out", default="data.js", help="Output file (default data.js).")
    args = ap.parse_args()

    universe = args.tickers or DEFAULT_UNIVERSE
    print(f"Fetching {len(universe)} tickers from Yahoo Finance...")

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

    if not args.keep_all:
        rows = [r for r in rows if r["rsi"] <= args.rsi]

    # Sort by market cap, largest first. Unknown caps sink to the bottom.
    rows.sort(key=lambda r: (r["marketCap"] or -1), reverse=True)

    payload = {
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "rsiThreshold": args.rsi,
        "universeSize": len(universe),
        "stocks": rows,
    }

    with open(args.out, "w") as f:
        f.write("// Auto-generated by fetch_data.py — do not edit by hand.\n")
        f.write("window.STOCK_DATA = ")
        json.dump(payload, f, indent=2)
        f.write(";\n")

    kept = len(rows)
    print(f"\nWrote {kept} stock(s) to {args.out}. Open index.html to view.")


if __name__ == "__main__":
    main()
