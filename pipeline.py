"""
CLI entrypoint: fetch market data + news sentiment, compute BS and opportunity scores, output CSV/JSON.

Single ticker:
  python pipeline.py --ticker SPY --headlines_csv newsapi_headlines.csv
  python pipeline.py --ticker AAPL

Multi-ticker (combines into output_multi_ticker.csv):
  python pipeline.py --headlines_csv newsapi_headlines.csv --tickers-from-headlines --output output_multi_ticker.csv
  python pipeline.py --headlines_csv newsapi_headlines.csv --tickers AAPL,MSFT,NVDA --output output_multi_ticker.csv
"""
import argparse
import csv
import json
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

from market_data import get_spot, get_options_chain
from news_sentiment import fetch_headlines, score_headlines
from rss_sentiment import get_ticker_sentiment, get_rolling_sentiment
from scoring import compute_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# For --tickers-from-headlines: use same set as pipeline_multi_ticker
try:
    from pipeline_multi_ticker import KNOWN_TICKERS
except ImportError:
    KNOWN_TICKERS = frozenset([
        "SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JNJ", "UNH", "PFE", "JPM", "BAC", "WMT", "PG", "KO", "XOM", "CVX", "GE", "LMT", "RTX",
    ])


def _extract_tickers_from_headlines_csv(csv_path: str) -> list[str]:
    """Extract unique tickers from headlines CSV query column."""
    tickers = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q = (row.get("query") or "").strip()
                if not q:
                    continue
                tokens = re.findall(r"\b([A-Z]{2,5})\b", q.upper())
                tickers.update(t for t in tokens if t in KNOWN_TICKERS)
    except Exception as e:
        logger.warning("Could not extract tickers from headlines: %s", e)
        return []
    return sorted(tickers)


def _serialize_for_json(obj: object) -> object:
    """Convert datetime and other non-JSON-serializable types."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, (float,)):
        if obj != obj:  # NaN
            return None
        return obj
    raise TypeError(type(obj))


def _run_multi_ticker(args) -> int:
    """Multi-ticker flow: headlines CSV -> per-ticker sentiment -> options -> combined output."""
    if not args.headlines_csv.strip():
        logger.error("Multi-ticker requires --headlines_csv")
        return 1

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
                    "query": (row.get("query") or "").strip(),
                })
    except Exception as e:
        logger.exception("Failed to load headlines: %s", e)
        return 1

    if not headlines:
        logger.error("No headlines loaded")
        return 1

    # Sample for speed
    if len(headlines) > 500:
        import random
        by_query: dict[str, list] = {}
        for h in headlines:
            q = h.get("query", "") or "_"
            by_query.setdefault(q, []).append(h)
        sampled = []
        per_q = max(1, 500 // max(1, len(by_query)))
        for group in by_query.values():
            sampled.extend(random.sample(group, min(per_q, len(group))))
        random.shuffle(sampled)
        headlines = sampled[:500]
        logger.info("Sampled 500 headlines from %d query groups", len(by_query))

    if args.tickers_from_headlines:
        tickers = _extract_tickers_from_headlines_csv(args.headlines_csv)
        if not tickers:
            logger.error("No tickers extracted from headlines")
            return 1
        logger.info("Extracted %d tickers from headlines", len(tickers))
    else:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    sentiment_result = score_headlines(headlines, model_preference=args.model)
    global_sentiment = sentiment_result.get("sentiment_mean", 0.0)
    headline_scores = sentiment_result.get("headline_scores", [])

    def _ticker_in_query(ticker: str, query: str) -> bool:
        if not query:
            return False
        words = set(re.findall(r"[A-Z0-9.]+", query.upper()))
        return ticker.upper() in words

    ticker_sentiment_map: dict[str, float] = {}
    if headline_scores and len(headline_scores) == len(headlines):
        for t in tickers:
            scores = [hs.get("score", 0.0) for h, hs in zip(headlines, headline_scores)
                      if _ticker_in_query(t, h.get("query", ""))]
            if scores:
                ticker_sentiment_map[t] = float(np.mean(scores))

    all_rows = []
    for ticker in tickers:
        try:
            spot = get_spot(ticker)
            if spot != spot or spot <= 0:
                logger.warning("No spot for %s, skipping", ticker)
                continue
            options_df = get_options_chain(ticker, max_expirations=min(args.expirations, 3))
            if options_df is None or options_df.empty:
                logger.warning("No options for %s, skipping", ticker)
                continue
            sentiment_mean = ticker_sentiment_map.get(ticker, global_sentiment)
            if not args.no_rss:
                try:
                    rss_sent = get_ticker_sentiment(ticker, hours=args.rss_hours) or get_rolling_sentiment(args.rss_hours)
                    if rss_sent is not None:
                        w = max(0.0, min(1.0, args.rss_weight))
                        sentiment_mean = (1 - w) * sentiment_mean + w * rss_sent
                except ImportError:
                    pass
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
                raw_score = row.get("opportunity_score")
                try:
                    score_val = float(raw_score) if raw_score is not None else 0.0
                except (TypeError, ValueError):
                    score_val = 0.0
                if score_val != score_val:
                    score_val = 0.0
                all_rows.append({
                    "ticker": ticker,
                    "expiration": str(exp) if exp is not None else "",
                    "contractSymbol": str(row.get("contractSymbol", "")),
                    "strike": row.get("strike", ""),
                    "price": row.get("lastPrice", ""),
                    "bid": row.get("bid", ""),
                    "midPrice": row.get("mid_price", ""),
                    "score": round(score_val, 4),
                    "impliedVolatility": row.get("impliedVolatility", ""),
                })
            logger.info("%s: %d options", ticker, len(top))
        except Exception as e:
            logger.warning("%s failed: %s", ticker, e)

    out_cols = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "midPrice", "score", "impliedVolatility"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    logger.info("Wrote %s (%d rows, %d tickers)", args.output, len(all_rows), len(set(r["ticker"] for r in all_rows)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Options opportunity pipeline: market data + BS + news sentiment + scoring."
    )
    parser.add_argument("--ticker", type=str, default="SPY", help="Underlying ticker")
    parser.add_argument("--expirations", type=int, default=6, help="Max option expirations")
    parser.add_argument("--r", type=float, default=0.045, help="Risk-free rate")
    parser.add_argument("--news_source", type=str, default="yahoo", choices=["newsapi", "yahoo"],
                        help="News source: newsapi (requires NEWS_API_KEY) or yahoo (ticker-based)")
    parser.add_argument("--news_query", type=str, default="SPY OR S&P 500", help="NewsAPI search query (used only if --news_source=newsapi)")
    parser.add_argument("--headlines", type=int, default=100, help="Number of headlines to fetch (NewsAPI.ai: up to 100 per search)")
    parser.add_argument("--headlines_csv", type=str, default="",
                        help="Load headlines from CSV file instead of fetching (e.g. newsapi_headlines_dummy.csv)")
    parser.add_argument("--no-cache", action="store_true", help="Force NewsAPI fetch (ignore local CSV cache)")
    parser.add_argument("--cache-hours", type=float, default=24.0, help="NewsAPI cache validity in hours (default: 24)")
    parser.add_argument("--model", type=str, default="auto", choices=["auto", "vader"], help="Sentiment model")
    parser.add_argument("--rss-weight", type=float, default=0.25, help="Weight for RSS/social sentiment (0-1); rest is news (default 0.25)")
    parser.add_argument("--rss-hours", type=int, default=24, help="RSS sentiment rolling window in hours (default 24)")
    parser.add_argument("--no-rss", action="store_true", help="Disable RSS/social sentiment (use news only)")
    parser.add_argument("--tickers", type=str, default="", help="Multi-ticker: comma-separated list (e.g. AAPL,MSFT,NVDA)")
    parser.add_argument("--tickers-from-headlines", action="store_true", help="Multi-ticker: extract tickers from headlines CSV query column")
    parser.add_argument("--output", type=str, default="output_multi_ticker.csv", help="Output path for multi-ticker combined CSV")
    parser.add_argument("--top-per-ticker", type=int, default=25, help="Top N options per ticker in multi-ticker mode")
    args = parser.parse_args()

    # Multi-ticker mode
    if args.tickers_from_headlines or args.tickers.strip():
        return _run_multi_ticker(args)

    ticker = args.ticker.strip().upper()
    if not ticker:
        logger.error("Ticker is required")
        return 1

    # 1) Spot + options chain
    logger.info("Fetching spot and options chain for %s", ticker)
    try:
        spot = get_spot(ticker)
        if spot != spot:  # NaN
            logger.error("Could not get spot price for %s", ticker)
            return 1
        options_df = get_options_chain(ticker, max_expirations=args.expirations)
        if options_df is None or options_df.empty:
            logger.error("No options chain for %s", ticker)
            return 1
    except Exception as e:
        logger.exception("Market data failed: %s", e)
        return 1

    # 2) Headlines + sentiment (NewsAPI, Yahoo Finance, or CSV file)
    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if args.headlines_csv.strip():
        import csv
        csv_path = args.headlines_csv.strip()
        headlines = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    headlines.append({
                        "title": row.get("title", ""),
                        "source": row.get("source", ""),
                        "publishedAt": row.get("publishedAt", ""),
                        "url": row.get("url", ""),
                    })
            logger.info("Loaded %d headlines from %s", len(headlines), csv_path)
        except Exception as e:
            logger.exception("Failed to load headlines from CSV: %s", e)
            return 1
    else:
        headlines = fetch_headlines(
            args.news_source,
            query=args.news_query,
            api_key=api_key,
            ticker=ticker,
            n=args.headlines,
            use_cache=not args.no_cache,
            cache_max_age_hours=args.cache_hours,
        )
    sentiment_result = score_headlines(headlines, model_preference=args.model)
    sentiment_result["news_source"] = "csv" if args.headlines_csv.strip() else args.news_source
    news_sentiment = sentiment_result.get("sentiment_mean", 0.0)
    if "warning" in sentiment_result:
        logger.warning("Sentiment: %s", sentiment_result["warning"])

    # Blend in RSS/social sentiment from rss_sentiment.db (optional)
    sentiment_mean = news_sentiment
    if not args.no_rss and args.rss_weight > 0:
        rss_sent = get_ticker_sentiment(ticker, hours=args.rss_hours) or get_rolling_sentiment(args.rss_hours)
        if rss_sent is not None:
            w = max(0.0, min(1.0, args.rss_weight))
            sentiment_mean = (1 - w) * news_sentiment + w * rss_sent
            logger.info("Sentiment: news=%.4f, rss=%.4f (weight=%.2f) -> combined=%.4f", news_sentiment, rss_sent, w, sentiment_mean)
        else:
            logger.debug("No RSS sentiment for %s (rss_sentiment.db empty or no data)", ticker)
    sentiment_result["sentiment_mean"] = sentiment_mean

    # 3) BS + scoring
    try:
        scored_df = compute_scores(options_df, spot, args.r, sentiment_mean)
    except Exception as e:
        logger.exception("Scoring failed: %s", e)
        return 1

    # 4) Output CSV (convert expiration for CSV if datetime)
    csv_path = f"output_{ticker}.csv"
    out_df = scored_df.copy()
    if "expiration" in out_df.columns and hasattr(out_df["expiration"].iloc[0], "isoformat"):
        out_df["expiration"] = out_df["expiration"].astype(str)
    out_df.to_csv(csv_path, index=False)
    logger.info("Wrote %s", csv_path)

    # 5) Simplified CSV: optiontype, price, strike, score (top 100 by |opportunity_score|)
    if "opportunity_score" in scored_df.columns:
        simple = (
            scored_df.assign(_abs=np.abs(scored_df["opportunity_score"]))
            .nlargest(100, "_abs")
            .drop(columns=["_abs"], errors="ignore")
        )
        simple_csv = simple[["option_type", "mid_price", "strike", "opportunity_score"]].copy()
        simple_csv.columns = ["optiontype", "price", "strike", "score"]
        simple_path = f"output_{ticker}_simple.csv"
        simple_csv.to_csv(simple_path, index=False)
        logger.info("Wrote %s", simple_path)

    # JSON sentiment
    json_path = f"sentiment_{ticker}.json"
    with open(json_path, "w") as f:
        json.dump(sentiment_result, f, default=_serialize_for_json, indent=2)
    logger.info("Wrote %s", json_path)

    # Top 15 by abs(opportunity_score)
    if "opportunity_score" not in scored_df.columns:
        logger.warning("No opportunity_score column")
        return 0
    top = (
        scored_df.assign(_abs=np.abs(scored_df["opportunity_score"]))
        .nlargest(15, "_abs")
        .drop(columns=["_abs"], errors="ignore")
    )
    cols_show = [
        "contractSymbol", "option_type", "strike", "expiration",
        "mid_price", "theo_price", "pricing_gap_pct", "opportunity_score", "risk_flag",
    ]
    cols_show = [c for c in cols_show if c in top.columns]
    print("\n--- Top 15 opportunities by |opportunity_score| ---")
    print(top[cols_show].to_string(index=False))

    

    return 0


if __name__ == "__main__":
    sys.exit(main())
