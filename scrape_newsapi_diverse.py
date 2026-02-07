"""
Scrape diverse company headlines and append to newsapi_headlines.csv.

Supports two sources:
  - eventregistry: NewsAPI.ai / Event Registry (requires NEWS_API_KEY, pip install eventregistry)
  - yahoo: Yahoo Finance via yfinance (no API key, works out of the box)

Usage:
  # Event Registry (NewsAPI.ai) - needs key + eventregistry
  $env:NEWS_API_KEY = "your_key"
  python scrape_newsapi_diverse.py

  # Yahoo Finance - no API key needed
  python scrape_newsapi_diverse.py --yahoo

  # Limit to first 50 companies (faster)
  python scrape_newsapi_diverse.py --yahoo --limit 50
"""
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CACHE_PATH = Path(__file__).resolve().parent / "newsapi_headlines.csv"

# Tickers to scrape when using Yahoo (extracted from SECTOR_QUERIES)
YAHOO_TICKERS = [
    "SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMZN", "TSLA",
    "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "AMD", "QCOM", "AVGO", "TXN", "NFLX",
    "PYPL", "SQ", "SPOT", "UBER", "ABNB", "ZM", "NOW", "WDAY", "SNOW", "DDOG", "CRWD",
    "PANW", "FTNT", "ZS", "NET", "SHOP", "ETSY", "MELI", "SE", "DASH", "TSM", "ASML",
    "MU", "WDC", "STX", "AMAT", "LRCX", "SNPS", "CDNS", "BABA", "JD", "BIDU", "SONY",
    "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "BMY", "AMGN", "GILD", "TMO", "ABT",
    "DHR", "MRNA", "REGN", "VRTX", "BIIB", "AZN", "NVS", "SNY", "GSK", "MDT", "BSX",
    "EW", "SYK", "ZBH", "ISRG", "DXCM", "BDX", "LH", "DGX", "CVS", "HCA",
    "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "V", "MA", "FI",
    "COF", "DFS", "BK", "BRK", "KKR", "BX", "CB", "TRV", "PGR", "MET", "PRU",
    "WMT", "PG", "KO", "COST", "PEP", "MCD", "NKE", "HD", "TGT", "LOW", "TJX",
    "SBUX", "CMG", "YUM", "F", "GM", "TM", "HMC", "RIVN", "LCID", "DIS",
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "OXY", "NEE", "DUK", "SO",
    "CAT", "BA", "UNP", "HON", "UPS", "FDX", "GE", "LMT", "RTX", "NOC", "DE",
    "MMM", "EMR", "CSX", "NSC", "WM", "RSG", "LIN", "SHW", "PLD", "AMT",
    "NEM", "FCX", "NUE", "DOW", "DD",
]


def _fetch_yahoo(ticker: str, n: int = 50) -> list[dict]:
    """Fetch headlines from Yahoo Finance for a ticker."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        raw = t.get_news(count=min(n, 50), tab="news")
        if not raw:
            return []
        out = []
        for a in raw:
            if not isinstance(a, dict):
                continue
            title = a.get("title") or a.get("headline") or ""
            url = a.get("link") or a.get("url") or ""
            src = a.get("provider") or a.get("source")
            if isinstance(src, dict):
                src = src.get("name") or src.get("displayName") or ""
            src = src or "Yahoo Finance"
            pub = a.get("providerPublishTime") or a.get("publishTime")
            if pub is not None and hasattr(pub, "isoformat"):
                published_at = pub.isoformat()
            elif isinstance(pub, (int, float)):
                try:
                    published_at = datetime.fromtimestamp(int(pub), tz=timezone.utc).isoformat()
                except (OSError, ValueError):
                    published_at = str(pub)
            else:
                published_at = str(pub) if pub else ""
            out.append({"title": title, "source": src, "publishedAt": published_at, "url": url})
        return out[:n]
    except Exception as e:
        print(f"  Yahoo error for {ticker}: {e}", file=sys.stderr)
        return []


def _save_to_csv(headlines: list[dict], query: str) -> None:
    if not headlines:
        return
    write_header = not CACHE_PATH.exists()
    fetched_at = datetime.now(timezone.utc).isoformat()
    with open(CACHE_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["query", "title", "source", "publishedAt", "url", "fetched_at"])
        for h in headlines:
            w.writerow([
                query, h.get("title", ""), h.get("source", ""),
                h.get("publishedAt", ""), h.get("url", ""), fetched_at,
            ])


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrape diverse company headlines → newsapi_headlines.csv"
    )
    parser.add_argument("--yahoo", action="store_true",
                        help="Use Yahoo Finance (no API key, works without eventregistry)")
    parser.add_argument("--limit", type=int, default=0, help="Limit to first N tickers/queries")
    parser.add_argument("--no-cache", action="store_true", help="Force fresh fetch (Event Registry only)")
    parser.add_argument("--cache", action="store_true", help="Use cache when available (Event Registry only)")
    args = parser.parse_args()

    if args.yahoo:
        tickers = YAHOO_TICKERS
        if args.limit > 0:
            tickers = tickers[: args.limit]
        print(f"Fetching Yahoo headlines for {len(tickers)} tickers...")
        print("Output: newsapi_headlines.csv\n")
        total = 0
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] {ticker}")
            headlines = _fetch_yahoo(ticker, n=50)
            if headlines:
                _save_to_csv(headlines, ticker)
                total += len(headlines)
                print(f"  → {len(headlines)} headlines")
            else:
                print("  → no results")
        print(f"\nDone. Total: {total} headlines across {len(tickers)} tickers.")
        return 0 if total > 0 else 1

    # Event Registry path
    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if not api_key:
        print("Error: NEWS_API_KEY must be set for Event Registry.", file=sys.stderr)
        print("Use: $env:NEWS_API_KEY = 'your_key'  (PowerShell)", file=sys.stderr)
        print("Or run with --yahoo for Yahoo Finance (no API key).", file=sys.stderr)
        return 1

    try:
        from newsapi_client import SECTOR_QUERIES_400, fetch_headlines
    except ImportError as e:
        print("Error: eventregistry not installed.", file=sys.stderr)
        print("Run: pip install eventregistry", file=sys.stderr)
        print("Or use --yahoo for Yahoo Finance.", file=sys.stderr)
        return 1

    use_cache = args.cache
    if args.no_cache:
        use_cache = False
    queries = SECTOR_QUERIES_400
    if args.limit > 0:
        queries = queries[: args.limit]
    print(f"Fetching Event Registry headlines for {len(queries)} queries...")
    print("Output: newsapi_headlines.csv\n")
    total = 0
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {query}")
        headlines = fetch_headlines(
            query=query, api_key=api_key, n=100,
            use_cache=use_cache, cache_max_age_hours=24.0,
        )
        if headlines:
            total += len(headlines)
            print(f"  → {len(headlines)} headlines")
        else:
            print("  → no results")
    print(f"\nDone. Total: {total} headlines.")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
