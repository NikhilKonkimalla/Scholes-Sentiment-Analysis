"""
Multi-ticker pipeline: run options scoring across many tickers, output combined CSV.
Uses headlines from CSV, computes sentiment (FinBERT), fetches options for each ticker.
Output: ticker, expiration, contractSymbol, strike, price, bid, midPrice, score, impliedVolatility

Usage:
  python pipeline_multi_ticker.py --headlines_csv newsapi_headlines.csv --output output_multi_ticker.csv
  python pipeline_multi_ticker.py --headlines_csv newsapi_headlines.csv --fast   # Much faster
"""
import argparse
import csv
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from market_data import get_spot, get_options_chain
from news_sentiment import score_headlines
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
    "COST", "PEP", "MCD", "NKE", "SBUX", "CMG", "V", "MA", "BLK",
    "CVX", "COP", "GE", "LMT", "RTX", "HON", "UPS", "FDX",
]

OUTPUT_COLS = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "midPrice", "score", "impliedVolatility"]

# Tickers to extract from headlines query column (matches YAHOO_TICKERS)
KNOWN_TICKERS = frozenset([
    "SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "AMD", "QCOM", "AVGO", "TXN", "NFLX",
    "PYPL", "SQ", "SPOT", "UBER", "ABNB", "ZM", "NOW", "WDAY", "SNOW", "DDOG", "CRWD",
    "PANW", "FTNT", "ZS", "NET", "SHOP", "ETSY", "MELI", "SE", "DASH", "OKTA", "DOCU",
    "TEAM", "TWLO", "ESTC", "PLTR", "COIN", "HOOD", "SOFI", "AFRM", "ROKU",
    "TSM", "ASML", "MU", "WDC", "STX", "AMAT", "LRCX", "SNPS", "CDNS", "MRVL", "ON",
    "BABA", "JD", "BIDU", "PDD", "NIO", "XPEV", "LI",
    "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "BMY", "AMGN", "GILD", "TMO", "ABT",
    "DHR", "MRNA", "REGN", "VRTX", "BIIB", "AZN", "NVS", "SNY", "GSK", "MDT", "BSX",
    "EW", "SYK", "ZBH", "ISRG", "DXCM", "BDX", "LH", "DGX", "CVS", "HCA", "ELV",
    "IQV", "ILMN", "EXAS", "ALNY", "BMRN", "SRPT", "IDXX", "ZTS",
    "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "V", "MA", "FI",
    "COF", "DFS", "BK", "BRK", "KKR", "BX", "APO", "CG", "CB", "TRV", "PGR", "MET", "PRU",
    "AON", "MMC", "ICE", "CME", "SPGI", "MCO", "MSCI",
    "WMT", "PG", "KO", "COST", "PEP", "MCD", "NKE", "HD", "TGT", "LOW", "TJX",
    "SBUX", "CMG", "YUM", "DPZ", "LULU", "ROST", "DG", "DLTR",
    "F", "GM", "TM", "HMC", "RIVN", "LCID", "LYFT",
    "DIS", "BKNG", "EXPE", "MAR", "HLT", "RCL", "CCL", "LVS", "MGM", "WYNN",
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "OXY", "PXD", "DVN", "HAL", "BKR",
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "SRE", "WEC",
    "CAT", "BA", "UNP", "HON", "UPS", "FDX", "GE", "LMT", "RTX", "NOC", "GD",
    "DE", "MMM", "EMR", "ROK", "PH", "ETN", "ITW", "CSX", "NSC", "WM", "RSG",
    "XPO", "ODFL", "JBHT", "CHRW", "CARR", "TT", "JCI", "LHX", "TDG", "HII",
    "LIN", "SHW", "PLD", "AMT", "EQIX", "NEM", "FCX", "NUE", "STLD", "DOW", "DD",
    "APD", "PPG", "ALB", "VMC", "MLM", "SPG", "WELL", "DLR", "CCI", "CBRE",
    "EA", "TTWO", "RBLX", "U", "ZG", "MTCH", "WBD", "PARA",
    "LMT", "RTX", "NOC", "GD", "HII", "LHX", "TDG", "HON", "TXT",
    "ANF", "GPS", "AEO", "BBY", "ORLY", "AZO", "KMX", "CVNA", "DKS",
    "MDB", "HUBS", "VEEV", "WK", "TYL", "FIS", "GDDY",
    "BHVN", "EXEL", "INCY", "ALL", "AFL", "CINF", "L", "AIG", "HIG", "AIZ", "WRB",
    "USB", "PNC", "TFC", "FITB", "KEY", "HBAN", "CFG", "RF",
    "K", "GIS", "CPB", "HSY", "KDP", "MNST", "STZ", "BF.B", "TAP", "DEO",
    "FAST", "GWW", "MSM", "SWK", "CMI", "PCAR", "DOV", "IEX", "PNR", "FTV",
    "PSA", "AVB", "EQR", "UDR", "VTR", "O", "ARE",
    "ENPH", "SEDG", "FSLR", "RUN", "PLUG", "BE", "CHPT", "BLDP",
    "SAP", "SIEGY", "STM", "NVO", "SONY", "PM", "MO", "T", "VZ", "CMCSA", "CHTR", "TMUS",
    "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "SAVE", "HA",
    "HGV", "HLT", "MAR", "WH", "CHH", "H",
    "PWR", "FLR", "MTZ", "APG",
    "CE", "EMN", "FMC", "LYB", "WLK", "RPM", "MOS", "CF",
    "AA", "CLF", "X", "SCCO", "TECK", "RGLD", "FNV", "GOLD", "IFF",
    "IP", "PKG", "WRK", "SEE", "AMCR",
    "RHI", "KFRC", "KFY", "PAYX",
    "AMG", "IVZ", "TROW", "BEN", "LAZ", "PJT", "STEP",
    "WHR", "NVR", "LEN", "DHI", "PHM", "TOL", "KBH", "MTH",
    "WING", "SHAK", "CAVA", "BJRI", "BLMN",
    "CZR", "PENN", "BYD",
    "KMI", "EPD", "MPLX", "WMB", "OKE", "PAA", "ET",
    "NOV", "HP", "PTEN", "RIG", "VAL", "FANG",
    "ED", "AEE", "ES", "PEG", "EIX", "FE", "CNP",
    "BPMC", "RARE", "NTRA", "TECH", "HOLX", "MTD", "WAT", "A",
    "HUM", "CI", "CNC", "MOH", "MCK", "ABC", "CAH",
    "IWM", "DIA", "XLF", "XLK", "XLE", "XLV", "XLI", "XLY",
    "GEN", "BILL", "SMAR", "DOMO", "DOCN", "CFLT", "PATH",
    "GPN", "FISV", "WEX", "FLT", "EVO",
    "BHP", "RIO", "GLNCY", "SAN", "DB", "UBS", "BP", "SHEL", "TTE", "SNP", "PTR", "CEO", "NSANY",
    "AKAM", "FFIV", "VRSN", "ANSS", "ANET", "CIEN", "JNPR", "HPE", "NTAP", "MPWR", "SWKS", "QRVO", "MCHP",
    "DXC", "EPAM", "IT", "CTSH", "ACN", "INFY", "WIT", "HCL",
    "ULTA", "POOL", "RH", "WSM", "ETH", "HBI", "VFC",
    "CL", "EL", "SJM", "LW", "SMPL", "LANC", "SYY",
    "LDOS", "SW", "RBC", "SNA", "TTC", "XYL", "WSO", "GNRC",
    "ROP", "OTIS", "IR", "WAB", "HUBB", "HAS", "MAT", "AN",
    "LAD", "PAG", "SAH", "ABG", "CARG", "TDG", "WWD", "HWM", "ATI", "CENX", "KALU", "CMC",
    "VST", "NRG", "CWEN", "ORA", "BEPC", "BEP", "NEP",
    "KR", "BG", "ADM", "TSN", "SIG", "BOOT", "BKE", "SFRGY",
])


def _extract_tickers_from_headlines_csv(csv_path: str) -> list[str]:
    """Extract unique tickers from the headlines CSV query column."""
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline: headlines CSV → FinBERT sentiment → options scoring → output_multi_ticker.csv"
    )
    parser.add_argument("--headlines_csv", type=str, required=True,
                        help="Headlines CSV (e.g. newsapi_headlines.csv)")
    parser.add_argument("--tickers", type=str, default="",
                        help="Comma-separated tickers (default: SPY,AAPL,MSFT,...)")
    parser.add_argument("--tickers-from-headlines", action="store_true",
                        help="Extract tickers from headlines query column (ignores --tickers)")
    parser.add_argument("--output", type=str, default="output_multi_ticker.csv", help="Output CSV path")
    parser.add_argument("--r", type=float, default=0.045, help="Risk-free rate")
    parser.add_argument("--expirations", type=int, default=3, help="Max option expirations per ticker")
    parser.add_argument("--top_per_ticker", type=int, default=50, help="Top N options per ticker by |score|")
    parser.add_argument("--no-rss", action="store_true", help="Disable RSS/social sentiment (news only)")
    parser.add_argument("--fast", action="store_true", help="Speed mode: sample 500 headlines, 25 opts/ticker, 2 expirations, parallel tickers")
    parser.add_argument("--headlines_sample", type=int, default=0, help="Max headlines for sentiment (0=all, 500 recommended for speed)")
    parser.add_argument("--parallel", type=int, default=0, help="Parallel ticker workers (0=sequential; use 2-3 to avoid Yahoo rate limits)")
    args = parser.parse_args()

    if args.fast:
        args.headlines_sample = args.headlines_sample or 500
        args.top_per_ticker = 25
        args.expirations = 2
        args.no_rss = True
        args.parallel = args.parallel or 3
        logger.info("Fast mode: headlines_sample=500, top_per_ticker=25, expirations=2, parallel=3")

    # Load headlines (include query for per-ticker sentiment)
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

    # Sample headlines for speed; use stratified sample so we get headlines from many tickers
    if args.headlines_sample > 0 and len(headlines) > args.headlines_sample:
        import random
        by_query: dict[str, list[dict]] = {}
        for h in headlines:
            q = h.get("query", "") or "_"
            by_query.setdefault(q, []).append(h)
        sampled: list[dict] = []
        n_groups = len(by_query)
        per_query = max(1, args.headlines_sample // max(1, n_groups))
        for q, group in by_query.items():
            sampled.extend(random.sample(group, min(per_query, len(group))))
        random.shuffle(sampled)
        headlines = sampled[: args.headlines_sample]
        logger.info("Stratified sampled %d headlines from %d query groups", len(headlines), n_groups)
    else:
        logger.info("Loaded %d headlines", len(headlines))

    # Tickers: from headlines query column, or --tickers, or default (needed before per-ticker sentiment)
    if args.tickers_from_headlines:
        tickers = _extract_tickers_from_headlines_csv(args.headlines_csv)
        if not tickers:
            logger.warning("No tickers extracted; falling back to DEFAULT_TICKERS")
            tickers = DEFAULT_TICKERS
        else:
            logger.info("Extracted %d tickers from headlines", len(tickers))
    else:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()] if args.tickers.strip() else DEFAULT_TICKERS

    # News sentiment: score all once, then build per-ticker sentiment from query-matched headlines
    sentiment_result = score_headlines(headlines, model_preference="auto")
    global_sentiment = sentiment_result.get("sentiment_mean", 0.0)
    headline_scores = sentiment_result.get("headline_scores", [])
    logger.info("Global news sentiment mean: %.4f", global_sentiment)

    def _ticker_in_query(ticker: str, query: str) -> bool:
        """True if ticker appears as whole word in query."""
        if not query:
            return False
        words = set(re.findall(r"[A-Z0-9.]+", query.upper()))
        return ticker.upper() in words

    ticker_sentiment_map: dict[str, float] = {}
    if headline_scores and len(headline_scores) == len(headlines):
        for ticker in tickers:
            scores = []
            for h, hs in zip(headlines, headline_scores):
                if _ticker_in_query(ticker, h.get("query", "")):
                    scores.append(hs.get("score", 0.0))
            if scores:
                ticker_sentiment_map[ticker] = float(np.mean(scores))
                logger.debug("%s: %d headlines, sentiment=%.4f", ticker, len(scores), ticker_sentiment_map[ticker])
    logger.info("Per-ticker sentiment for %d tickers (rest use global %.4f)", len(ticker_sentiment_map), global_sentiment)

    def _process_ticker(ticker: str) -> list[dict]:
        """Process one ticker; return list of option rows."""
        rows = []
        try:
            spot = get_spot(ticker)
            if spot != spot or spot <= 0:
                logger.warning("No spot for %s, skipping", ticker)
                return rows
            options_df = get_options_chain(ticker, max_expirations=args.expirations)
            if options_df is None or options_df.empty:
                logger.warning("No options for %s, skipping", ticker)
                return rows
            sentiment_mean = ticker_sentiment_map.get(ticker, global_sentiment)
            if not args.no_rss:
                try:
                    from rss_sentiment import get_ticker_sentiment, get_rolling_sentiment
                    rss_sent = get_ticker_sentiment(ticker, hours=24) or get_rolling_sentiment(24)
                    if rss_sent is not None:
                        sentiment_mean = 0.75 * sentiment_mean + 0.25 * rss_sent
                except ImportError:
                    pass
            scored_df = compute_scores(options_df, spot, args.r, sentiment_mean)
            if "opportunity_score" not in scored_df.columns:
                return rows
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
                if score_val != score_val:  # NaN
                    score_val = 0.0
                rows.append({
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
        return rows

    all_rows = []
    workers = args.parallel
    if workers > 0:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_process_ticker, t): t for t in tickers}
            for fut in as_completed(futures):
                all_rows.extend(fut.result())
    else:
        for ticker in tickers:
            all_rows.extend(_process_ticker(ticker))

    # Write output
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    logger.info("Wrote %s (%d rows, %d tickers)", args.output, len(all_rows), len(set(r["ticker"] for r in all_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
