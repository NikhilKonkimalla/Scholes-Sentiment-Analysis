"""
Multi-ticker pipeline: run options scoring across many tickers, output combined CSV.
Uses headlines from CSV, computes sentiment, fetches options for each ticker.

The output carries the risk signal alongside the score: a contract can score highly on
mispricing while being untradeable (no volume, wide spread), and dropping risk_flag from
the output left the API unable to qualify a high-confidence badge.

Also writes a data_meta.json sidecar next to the output so the frontend can show an
accurate "data as of" date.
"""
import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone

import numpy as np

from market_data import get_spot, get_options_chain
from news_sentiment import score_headlines, fetch_headlines_yahoo
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

OUTPUT_COLS = [
    "ticker", "expiration", "contractSymbol", "strike",
    "price", "bid", "ask", "midPrice",
    "score", "impliedVolatility",
    # Risk / liquidity signal. riskFlag is the decision; the rest are the inputs it
    # is derived from, so the UI can explain why a contract is flagged.
    "volume", "openInterest", "theoPrice", "liquidityScore", "spreadPenalty", "riskFlag",
]


def _cell(value):
    """
    CSV cell for a possibly-NaN numeric.

    Empty rather than the string "nan": the API parses these back to floats and
    jsonify would emit a bare NaN literal, which is not valid JSON.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "" if value is None else value
    return "" if f != f else f


def write_metadata(output_path: str, rows: list[dict]) -> None:
    """
    Write data_meta.json beside the output CSV.

    The frontend reads this for its "data as of" label. A sidecar rather than the
    CSV's mtime because mtimes are unreliable in deployment: a fresh git checkout
    stamps every file with the deploy time, which would report stale data as new.
    """
    meta_path = os.path.join(os.path.dirname(os.path.abspath(output_path)), "data_meta.json")
    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": os.path.basename(output_path),
        "rows": len(rows),
        "tickerCount": len({r["ticker"] for r in rows}),
        "riskFlagged": sum(1 for r in rows if r.get("riskFlag") is True),
    }
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
        logger.info("Wrote %s", meta_path)
    except OSError as e:
        logger.warning("Could not write %s: %s", meta_path, e)


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
    parser.add_argument("--per-ticker-news", action="store_true", help="Fetch ticker-specific headlines (Yahoo) per ticker for nuanced sentiment; slower")
    parser.add_argument("--per-ticker-news-n", type=int, default=25, help="Headlines per ticker when using --per-ticker-news (default 25)")
    parser.add_argument("--sentiment-weight", type=float, default=1.0, help="Weight for sentiment vs mispricing (1.0 = sentiment only; bearish -> favor puts)")
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
            # Per-ticker sentiment: optional ticker-specific news, then blend with global + RSS
            sentiment_mean = news_sentiment
            if getattr(args, "per_ticker_news", False):
                ticker_headlines = fetch_headlines_yahoo(ticker, n=getattr(args, "per_ticker_news_n", 25))
                if ticker_headlines:
                    ticker_result = score_headlines(ticker_headlines, model_preference="auto")
                    ticker_news = ticker_result.get("sentiment_mean", news_sentiment)
                    sentiment_mean = 0.7 * ticker_news + 0.3 * news_sentiment
                    logger.info("%s: per-ticker news sentiment %.4f (blended with global)", ticker, sentiment_mean)
            if not args.no_rss and args.rss_weight > 0:
                # `or` would discard a genuine neutral 0.0; None means "no data".
                rss_sent = get_ticker_sentiment(ticker, hours=args.rss_hours)
                if rss_sent is None:
                    rss_sent = get_rolling_sentiment(args.rss_hours)
                if rss_sent is not None:
                    w = max(0.0, min(1.0, args.rss_weight))
                    sentiment_mean = (1 - w) * sentiment_mean + w * rss_sent
            scored_df = compute_scores(
                options_df, spot, args.r, sentiment_mean,
                sentiment_weight=getattr(args, "sentiment_weight", 1.0),
            )
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
                risk = row.get("risk_flag")
                all_rows.append({
                    "ticker": ticker,
                    "expiration": str(exp) if exp is not None else "",
                    "contractSymbol": str(row.get("contractSymbol", "")),
                    "strike": _cell(row.get("strike")),
                    "price": _cell(row.get("lastPrice")),
                    "bid": _cell(row.get("bid")),
                    "ask": _cell(row.get("ask")),
                    "midPrice": _cell(row.get("mid_price")),
                    "score": _cell(row.get("opportunity_score")),
                    "impliedVolatility": _cell(row.get("impliedVolatility")),
                    "volume": _cell(row.get("volume")),
                    "openInterest": _cell(row.get("openInterest")),
                    "theoPrice": _cell(row.get("theo_price")),
                    "liquidityScore": _cell(row.get("liquidity_score")),
                    "spreadPenalty": _cell(row.get("spread_penalty")),
                    "riskFlag": bool(risk) if risk is not None else "",
                })
            logger.info("%s: %d options", ticker, len(top))
        except Exception as e:
            logger.warning("%s failed: %s", ticker, e)

    # Write output
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    flagged = sum(1 for r in all_rows if r.get("riskFlag") is True)
    logger.info("Wrote %s (%d rows, %d tickers, %d risk-flagged)",
                args.output, len(all_rows), len(set(r["ticker"] for r in all_rows)), flagged)

    if all_rows:
        write_metadata(args.output, all_rows)

    return 0


if __name__ == "__main__":
    sys.exit(main())
