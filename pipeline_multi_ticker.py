"""
Multi-ticker pipeline: run options scoring across many tickers, output combined CSV.
Uses headlines from CSV, computes sentiment, fetches options for each ticker.
Output: ticker, expiration, contractSymbol, strike, price, bid, midPrice, score, impliedVolatility
"""
import argparse
import csv
import logging
import sys

import numpy as np

from market_data import get_spot, get_options_chain
from news_sentiment import score_headlines
from rss_sentiment import get_ticker_sentiment, get_rolling_sentiment
from scoring import compute_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Diverse tickers across sectors
DEFAULT_TICKERS = [
    "SPY", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "BAC", "XOM", "UNH", "JNJ", "PFE", "LLY", "WMT", "PG", "KO",
    "HD", "DIS", "NFLX", "ADBE", "CRM", "INTC", "AMD", "GS", "BA", "CAT",
]

OUTPUT_COLS = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "midPrice", "score", "impliedVolatility"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-ticker pipeline with combined output CSV")
    parser.add_argument("--headlines_csv", type=str, required=True, help="Headlines CSV (e.g. newsapi_headlines_500.csv)")
    parser.add_argument("--tickers", type=str, default="",
                        help="Comma-separated tickers (default: SPY,AAPL,MSFT,...)")
    parser.add_argument("--output", type=str, default="output_multi_ticker.csv", help="Output CSV path")
    parser.add_argument("--r", type=float, default=0.045, help="Risk-free rate")
    parser.add_argument("--expirations", type=int, default=3, help="Max option expirations per ticker")
    parser.add_argument("--top_per_ticker", type=int, default=50, help="Top N options per ticker by |score|")
    parser.add_argument("--rss-weight", type=float, default=0.25, help="Weight for RSS/social sentiment (0-1); rest is news (default 0.25)")
    parser.add_argument("--rss-hours", type=int, default=24, help="RSS sentiment rolling window in hours (default 24)")
    parser.add_argument("--no-rss", action="store_true", help="Disable RSS/social sentiment (use news only)")
    args = parser.parse_args()

    # Load headlines
    headlines = []
    try:
        with open(args.headlines_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                headlines.append({
                    "title": row.get("title", ""),
                    "source": row.get("source", ""),
                    "publishedAt": row.get("publishedAt", ""),
                    "url": row.get("url", ""),
                })
    except Exception as e:
        logger.exception("Failed to load headlines: %s", e)
        return 1

    if not headlines:
        logger.error("No headlines loaded")
        return 1

    logger.info("Loaded %d headlines", len(headlines))

    # News sentiment from headlines
    sentiment_result = score_headlines(headlines, model_preference="auto")
    news_sentiment = sentiment_result.get("sentiment_mean", 0.0)
    logger.info("News sentiment mean: %.4f", news_sentiment)

    # Tickers
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()] if args.tickers.strip() else DEFAULT_TICKERS

    all_rows = []
    for ticker in tickers:
        try:
            spot = get_spot(ticker)
            if spot != spot or spot <= 0:
                logger.warning("No spot for %s, skipping", ticker)
                continue
            options_df = get_options_chain(ticker, max_expirations=args.expirations)
            if options_df is None or options_df.empty:
                logger.warning("No options for %s, skipping", ticker)
                continue
            # Per-ticker blended sentiment: news + RSS/social (ticker-specific or overall)
            sentiment_mean = news_sentiment
            if not args.no_rss and args.rss_weight > 0:
                rss_sent = get_ticker_sentiment(ticker, hours=args.rss_hours) or get_rolling_sentiment(args.rss_hours)
                if rss_sent is not None:
                    w = max(0.0, min(1.0, args.rss_weight))
                    sentiment_mean = (1 - w) * news_sentiment + w * rss_sent
            scored_df = compute_scores(options_df, spot, args.r, sentiment_mean)
            if "opportunity_score" not in scored_df.columns:
                continue
            top = (
                scored_df.assign(_abs=np.abs(scored_df["opportunity_score"]))
                .nlargest(args.top_per_ticker, "_abs")
                .drop(columns=["_abs"], errors="ignore")
            )
            for _, row in top.iterrows():
                exp = row.get("expiration")
                if hasattr(exp, "isoformat"):
                    exp = exp.isoformat()
                all_rows.append({
                    "ticker": ticker,
                    "expiration": str(exp) if exp is not None else "",
                    "contractSymbol": str(row.get("contractSymbol", "")),
                    "strike": row.get("strike", ""),
                    "price": row.get("lastPrice", ""),
                    "bid": row.get("bid", ""),
                    "midPrice": row.get("mid_price", ""),
                    "score": row.get("opportunity_score", ""),
                    "impliedVolatility": row.get("impliedVolatility", ""),
                })
            logger.info("%s: %d options", ticker, len(top))
        except Exception as e:
            logger.warning("%s failed: %s", ticker, e)

    # Write output
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    logger.info("Wrote %s (%d rows, %d tickers)", args.output, len(all_rows), len(set(r["ticker"] for r in all_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
