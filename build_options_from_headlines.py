"""
Build a big options CSV with all categories (ticker, expiration, contractSymbol,
strike, price, bid, midPrice, score, impliedVolatility) for every company
that appears in newsapi_headlines.csv.

Extracts unique tickers from the headlines query column, runs the pipeline
for each ticker, and outputs a combined CSV.

Usage:
    python build_options_from_headlines.py
    python build_options_from_headlines.py --headlines newsapi_headlines.csv --output options_all.csv
"""
import argparse
import csv
import logging
import os
import re
import sys

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Known tickers from sector queries + common ETFs (used to extract from query strings)
KNOWN_TICKERS = frozenset([
    "SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "AMD", "QCOM", "AVGO", "TXN", "NFLX",
    "PYPL", "SQ", "SPOT", "UBER", "ABNB", "ZM", "NOW", "WDAY", "SNOW", "DDOG", "CRWD",
    "PANW", "FTNT", "ZS", "NET", "SHOP", "ETSY", "MELI", "SE", "GRAB", "DASH",
    "TSM", "ASML", "MU", "WDC", "STX", "AMAT", "LRCX", "SNPS", "CDNS", "ANSS",
    "TEAM", "DOCU", "TWLO", "OKTA", "ESTC", "BABA", "JD", "BIDU", "SONY",
    "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "BMY", "AMGN", "GILD", "TMO", "ABT", "DHR",
    "MRNA", "REGN", "VRTX", "BIIB", "AZN", "NVS", "SNY", "GSK", "TAK", "MDT", "BSX", "EW",
    "SYK", "ZBH", "ISRG", "DXCM", "BDX", "LH", "DGX", "CRL", "IQV", "ILMN", "EXAS", "GH",
    "TXG", "PACB", "SRPT", "BMRN", "ALNY", "IDXX", "ZTS", "CTLT", "TDOC", "OSCR", "CLOV",
    "ALHC", "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "SPGI", "CME",
    "ICE", "MCO", "MSCI", "FDS", "CBOE", "STT", "NTRS", "BK", "COF", "DFS", "ALLY", "SYF",
    "FITB", "PNC", "USB", "TFC", "CFG", "KEY", "HBAN", "RF", "MTB", "V", "MA", "FI", "GPN",
    "AFRM", "SOFI", "HOOD", "LC", "UPST", "MQ", "BFH", "BRK", "AON", "MMC", "CB", "TRV",
    "PGR", "ALL", "MET", "PRU", "AFL", "KKR", "APO", "BX", "CG", "ARES",
    "WMT", "PG", "KO", "COST", "PEP", "MCD", "NKE", "HD", "TGT", "LOW", "TJX", "DG", "DLTR",
    "ROST", "SBUX", "CMG", "YUM", "DPZ", "WEN", "QSR", "CL", "KMB", "CLX", "CHD", "EL",
    "UL", "MDLZ", "GIS", "K", "CPB", "HSY", "MNST", "KDP", "STZ", "TAP", "BF.B", "DEO",
    "F", "GM", "TM", "HMC", "RIVN", "LCID", "AZO", "ORLY", "AAP", "KMX", "CVNA",
    "MAR", "HLT", "H", "EXPE", "BKNG", "TRIP", "RCL", "CCL", "NCLH", "DIS",
    "WYNN", "LVS", "MGM", "CZR", "PENN", "LULU", "UAA", "VFC", "SKX", "CROX", "TPR", "RL",
    "PVH", "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "PXD", "DVN", "OXY",
    "HES", "FANG", "CTRA", "APA", "BKR", "HAL", "NOV", "HP", "NBR", "KMI", "WMB", "EPD",
    "MPLX", "NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "WEC", "PEG", "ED", "FE", "DTE",
    "LNT", "CMS", "ENPH", "SEDG", "FSLR", "SPWR", "RUN", "BE", "PLUG", "FCEL", "CLNE",
    "CAT", "BA", "UNP", "HON", "UPS", "FDX", "GE", "LMT", "RTX", "NOC", "GD", "DE", "MMM",
    "EMR", "ROK", "PH", "ETN", "CMI", "ITW", "SWK", "CSX", "NSC", "JBHT", "CHRW", "EXPD",
    "XPO", "ODFL", "LSTR", "R", "WM", "RSG", "WCN", "CWST", "CARR", "TT", "JCI", "LII",
    "FAST", "GWW", "MSM", "PNR", "IEX", "DOV", "FTV", "ROP", "HII", "LHX", "TDG",
    "LIN", "SHW", "PLD", "AMT", "EQIX", "NEM", "FCX", "NUE", "STLD", "CLF", "DOW", "DD",
    "LYB", "EMN", "CE", "APD", "PPG", "ALB", "LTHM", "MLM", "VMC", "EXP", "SUM", "SPG",
    "WELL", "VTR", "DLR", "CCI", "CBRE", "JLL", "CSGP", "Z",
])


def extract_tickers_from_query(query: str) -> set[str]:
    """Extract known ticker symbols from a query string (e.g. 'Apple AAPL' -> AAPL)."""
    if not query or not query.strip():
        return set()
    # Split on spaces and punctuation; take tokens that are known tickers
    tokens = re.findall(r"\b([A-Z]{2,5})\b", query.upper())
    return {t for t in tokens if t in KNOWN_TICKERS}


def get_unique_tickers_from_headlines(csv_path: str) -> list[str]:
    """Extract all unique tickers mentioned in the headlines CSV query column."""
    tickers = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q = row.get("query", "")
                tickers.update(extract_tickers_from_query(q))
    except Exception as e:
        logger.exception("Failed to read %s: %s", csv_path, e)
        return []
    result = sorted(tickers)
    logger.info("Extracted %d unique tickers from %s", len(result), csv_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build big options CSV from headlines tickers"
    )
    parser.add_argument(
        "--headlines",
        type=str,
        default="newsapi_headlines.csv",
        help="Headlines CSV path (default: newsapi_headlines.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="options_all_stocks.csv",
        help="Output CSV path (default: options_all_stocks.csv)",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default="",
        help="Override: comma-separated tickers (skips extraction from headlines)",
    )
    parser.add_argument("--r", type=float, default=0.045, help="Risk-free rate")
    parser.add_argument("--expirations", type=int, default=3, help="Max option expirations per ticker")
    parser.add_argument("--top_per_ticker", type=int, default=50, help="Top N options per ticker by |score|")
    args = parser.parse_args()

    if args.tickers.strip():
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        if not os.path.isfile(args.headlines):
            logger.error("Headlines file not found: %s. Run scrape_newsapi_diverse.py first.", args.headlines)
            return 1
        tickers = get_unique_tickers_from_headlines(args.headlines)
        if not tickers:
            logger.error("No tickers extracted from headlines. Add more diverse company queries.")
            return 1

    # Load headlines for sentiment (if file exists)
    headlines = []
    if os.path.isfile(args.headlines):
        try:
            with open(args.headlines, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    headlines.append({
                        "title": row.get("title", ""),
                        "source": row.get("source", ""),
                        "publishedAt": row.get("publishedAt", ""),
                        "url": row.get("url", ""),
                    })
        except Exception as e:
            logger.warning("Could not load headlines for sentiment: %s. Using neutral.", e)

    sentiment_mean = 0.0
    if headlines:
        from news_sentiment import score_headlines
        res = score_headlines(headlines, model_preference="auto")
        sentiment_mean = res.get("sentiment_mean", 0.0)
        logger.info("Sentiment mean: %.4f", sentiment_mean)

    from market_data import get_spot, get_options_chain
    from scoring import compute_scores

    OUTPUT_COLS = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "midPrice", "score", "impliedVolatility"]

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

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    unique_tickers = len(set(r["ticker"] for r in all_rows))
    logger.info("Wrote %s (%d rows, %d tickers)", args.output, len(all_rows), unique_tickers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
