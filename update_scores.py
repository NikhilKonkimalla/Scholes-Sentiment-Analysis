"""
Update scores in output_multi_ticker.csv using the new scoring formula (neutral sentiment = mispricing alignment).
Reads the existing CSV, recomputes opportunity_score, writes back.

Usage:
  python update_scores.py
  python update_scores.py --input output_multi_ticker.csv --output output_multi_ticker.csv
"""
import argparse
import csv
import logging
from datetime import datetime, timezone
import re

import pandas as pd

from market_data import get_spot, get_options_chain
from scoring import compute_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute scores in output_multi_ticker.csv")
    parser.add_argument("--input", default="output_multi_ticker.csv", help="Input CSV path")
    parser.add_argument("--output", default="", help="Output CSV path (default: overwrite input)")
    parser.add_argument("--r", type=float, default=0.045, help="Risk-free rate")
    args = parser.parse_args()
    out_path = args.output or args.input

    df = pd.read_csv(args.input)
    if df.empty:
        logger.error("Empty CSV")
        return 1

    # Infer option_type from contractSymbol (e.g. AAPL260209C00210000 = call, AAPL260209P00210000 = put)
    def opt_type(sym: str) -> str:
        s = str(sym).upper()
        if re.search(r"\d{6}P\d", s):
            return "put"
        return "call"

    df["option_type"] = df["contractSymbol"].astype(str).apply(opt_type)

    # Parse expiration -> time_to_expiry_years
    now = datetime.now(timezone.utc)
    def parse_exp(exp_str):
        try:
            s = str(exp_str).replace("Z", "+00:00")
            if "T" in s:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            delta = (dt - now).total_seconds()
            return max(delta / (365 * 24 * 3600), 1e-6)
        except Exception:
            return 0.01

    df["time_to_expiry_years"] = df["expiration"].apply(parse_exp)

    # Estimate ask from bid/mid, use 0 for volume/OI
    mid = pd.to_numeric(df["midPrice"], errors="coerce").fillna(0)
    bid = pd.to_numeric(df["bid"], errors="coerce").fillna(0)
    df["ask"] = mid + (mid - bid).clip(lower=0.01)
    df["volume"] = 1
    df["openInterest"] = 1
    df["mid_price"] = mid
    df["lastPrice"] = df.get("price", mid)

    # Group by ticker, fetch spot, run scoring
    tickers = df["ticker"].unique().tolist()
    logger.info("Updating scores for %d rows, %d tickers", len(df), len(tickers))

    scored_rows = []
    for ticker in tickers:
        sub = df[df["ticker"] == ticker].copy()
        if sub.empty:
            continue
        try:
            spot = get_spot(ticker)
            if pd.isna(spot) or spot <= 0:
                logger.warning("No spot for %s, keeping old scores", ticker)
                scored_rows.append(sub)
                continue
        except Exception as e:
            logger.warning("Spot failed for %s: %s", ticker, e)
            scored_rows.append(sub)
            continue

        # Build options-like df for scoring
        opts = sub.rename(columns={"impliedVolatility": "impliedVolatility"}).copy()
        opts = opts[["ticker", "expiration", "option_type", "contractSymbol", "strike",
                    "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility",
                    "mid_price", "time_to_expiry_years"]].copy()
        opts["strike"] = pd.to_numeric(opts["strike"], errors="coerce")
        opts["impliedVolatility"] = pd.to_numeric(opts["impliedVolatility"], errors="coerce").fillna(0.2)

        scored = compute_scores(opts, float(spot), args.r, sentiment_mean=0.0)
        if scored.empty or "opportunity_score" not in scored.columns:
            scored_rows.append(sub)
            continue

        sub["score"] = scored["opportunity_score"].values
        sub["score"] = sub["score"].round(4)
        scored_rows.append(sub)
        logger.info("%s: updated %d rows", ticker, len(sub))

    out = pd.concat(scored_rows, ignore_index=True)
    out_cols = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "midPrice", "score", "impliedVolatility"]
    out[out_cols].to_csv(out_path, index=False)
    logger.info("Wrote %s", out_path)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
