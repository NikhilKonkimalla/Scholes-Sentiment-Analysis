"""
Scrape NewsAPI for diverse company headlines and append to newsapi_headlines.csv.

Fetches headlines across 400+ companies (tech, health, finance, consumer, energy,
industrials, materials, real estate) and saves to newsapi_headlines.csv.

Requires: NEWS_API_KEY environment variable (NewsAPI.ai / Event Registry key)

Usage:
    set NEWS_API_KEY=your_key
    python scrape_newsapi_diverse.py              # Full run (400 queries)
    python scrape_newsapi_diverse.py --limit 50   # First 50 companies (faster)
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from newsapi_client import SECTOR_QUERIES_400, fetch_headlines


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrape NewsAPI for diverse company headlines → newsapi_headlines.csv"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit to first N queries (0 = all 400)",
    )
    parser.add_argument("--no-cache", action="store_true", help="Force fresh API fetch (default)")
    parser.add_argument("--cache", action="store_true", help="Use cached headlines when available (saves API credits)")
    args = parser.parse_args()

    use_cache = args.cache  # default: fetch fresh

    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if not api_key:
        print("Error: NEWS_API_KEY must be set. Run: set NEWS_API_KEY=your_key", file=sys.stderr)
        return 1

    queries = SECTOR_QUERIES_400
    if args.limit > 0:
        queries = queries[: args.limit]

    if args.no_cache:
        use_cache = False
    print(f"Fetching headlines for {len(queries)} diverse companies...")
    print("Output: newsapi_headlines.csv\n")

    total = 0
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {query}")
        headlines = fetch_headlines(
            query=query,
            api_key=api_key,
            n=100,
            use_cache=use_cache,
            cache_max_age_hours=24.0,
        )
        if headlines:
            total += len(headlines)
            print(f"  → {len(headlines)} headlines")
        else:
            print("  → no results")

    print(f"\nDone. Total: {total} headlines across {len(queries)} companies.")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
