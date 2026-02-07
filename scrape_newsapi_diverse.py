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

# Tickers to scrape when using Yahoo - diverse companies across sectors
YAHOO_TICKERS = [
    # ETFs & mega tech
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    # Tech
    "ADBE", "CRM", "ORCL", "CSCO", "IBM", "INTC", "AMD", "QCOM", "AVGO", "TXN", "NFLX",
    "PYPL", "SQ", "SPOT", "UBER", "ABNB", "ZM", "NOW", "WDAY", "SNOW", "DDOG", "CRWD",
    "PANW", "FTNT", "ZS", "NET", "SHOP", "ETSY", "MELI", "SE", "DASH", "OKTA", "DOCU",
    "TEAM", "TWLO", "ESTC", "PLTR", "COIN", "HOOD", "SOFI", "AFRM", "ROKU",
    # Semiconductors
    "TSM", "ASML", "MU", "WDC", "STX", "AMAT", "LRCX", "SNPS", "CDNS", "MRVL", "ON",
    # China tech
    "BABA", "JD", "BIDU", "PDD", "NIO", "XPEV", "LI",
    # Healthcare / Pharma
    "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "BMY", "AMGN", "GILD", "TMO", "ABT",
    "DHR", "MRNA", "REGN", "VRTX", "BIIB", "AZN", "NVS", "SNY", "GSK", "MDT", "BSX",
    "EW", "SYK", "ZBH", "ISRG", "DXCM", "BDX", "LH", "DGX", "CVS", "HCA", "ELV",
    "IQV", "ILMN", "EXAS", "ALNY", "BMRN", "SRPT", "IDXX", "ZTS",
    # Finance
    "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "V", "MA", "FI",
    "COF", "DFS", "BK", "BRK", "KKR", "BX", "APO", "CG", "CB", "TRV", "PGR", "MET", "PRU",
    "AON", "MMC", "ICE", "CME", "SPGI", "MCO", "MSCI",
    # Consumer / Retail
    "WMT", "PG", "KO", "COST", "PEP", "MCD", "NKE", "HD", "TGT", "LOW", "TJX",
    "SBUX", "CMG", "YUM", "DPZ", "LULU", "ROST", "DG", "DLTR",
    # Auto / Transport
    "F", "GM", "TM", "HMC", "RIVN", "LCID", "UBER", "LYFT",
    # Travel / Leisure
    "DIS", "BKNG", "EXPE", "MAR", "HLT", "RCL", "CCL", "LVS", "MGM", "WYNN",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "OXY", "PXD", "DVN", "HAL", "BKR",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "XEL", "SRE", "WEC",
    # Industrials
    "CAT", "BA", "UNP", "HON", "UPS", "FDX", "GE", "LMT", "RTX", "NOC", "GD",
    "DE", "MMM", "EMR", "ROK", "PH", "ETN", "ITW", "CSX", "NSC", "WM", "RSG",
    "XPO", "ODFL", "JBHT", "CHRW", "CARR", "TT", "JCI", "LHX", "TDG", "HII",
    # Materials / Real Estate
    "LIN", "SHW", "PLD", "AMT", "EQIX", "NEM", "FCX", "NUE", "STLD", "DOW", "DD",
    "APD", "PPG", "ALB", "VMC", "MLM", "SPG", "WELL", "DLR", "CCI", "CBRE",
    # Gaming / Media / Entertainment
    "EA", "TTWO", "RBLX", "U", "ZG", "MTCH", "WBD", "PARA",
    # Aerospace / Defense
    "LMT", "RTX", "NOC", "GD", "HII", "LHX", "TDG", "HON", "TXT",
    # Specialty retail / apparel
    "ANF", "GPS", "AEO", "BBY", "ORLY", "AZO", "KMX", "CVNA", "DKS",
    # Software / cloud (more)
    "MDB", "ZM", "TWLO", "HUBS", "VEEV", "WK", "TYL", "FIS", "GDDY",
    # Biotech / pharma (more)
    "BIIB", "VRTX", "BHVN", "ALNY", "REGN", "EXEL", "INCY",
    # Insurance
    "ALL", "AFL", "CINF", "L", "AIG", "HIG", "AIZ", "WRB",
    # Regional banks / diversified
    "USB", "PNC", "TFC", "FITB", "KEY", "HBAN", "CFG", "RF",
    # Food / Bev (more)
    "K", "GIS", "CPB", "HSY", "KDP", "MNST", "STZ", "BF.B", "TAP", "DEO",
    # Industrials (more)
    "FAST", "GWW", "MSM", "SWK", "CMI", "PCAR", "DOV", "IEX", "PNR", "FTV",
    # REITs / real estate (more)
    "PSA", "EQIX", "AVB", "EQR", "UDR", "VTR", "O", "ARE",
    # Clean energy / EV-related
    "ENPH", "SEDG", "FSLR", "RUN", "PLUG", "BE", "CHPT", "BLDP",
    # International
    "SAP", "ASML", "SIEGY", "STM", "NVO",
    # Telecom / media
    "SONY", "PM", "MO", "T", "VZ", "CMCSA", "CHTR", "TMUS",
    # Airlines
    "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "SAVE", "HA",
    # Lodging / hospitality
    "HGV", "HLT", "MAR", "WH", "CHH", "H",
    # Construction / engineering
    "PWR", "FLR", "MTZ", "APG",
    # Chemicals (more)
    "CE", "EMN", "FMC", "LYB", "WLK", "RPM", "MOS", "CF",
    # Metals / mining (more)
    "AA", "CLF", "X", "SCCO", "TECK", "RGLD", "FNV", "GOLD",
    "IFF", "CE", "EMN", "RPM", "CF", "MOS",
    # Packaging / containers
    "IP", "PKG", "WRK", "SEE", "AMCR",
    # Staffing / HR
    "RHI", "KFRC", "KFY", "PAYX",
    # Asset mgmt / brokerages (more)
    "AMG", "IVZ", "TROW", "BEN", "LAZ", "PJT", "STEP",
    # Consumer durables
    "WHR", "NVR", "LEN", "DHI", "PHM", "TOL", "KBH", "MTH",
    # Restaurants (more)
    "WING", "SHAK", "CAVA", "BJRI", "BLMN",
    # Casinos / gaming (more)
    "CZR", "PENN", "BYD",
    # Pipelines / midstream
    "KMI", "EPD", "MPLX", "WMB", "OKE", "PAA", "ET",
    # Oilfield / energy services (more)
    "NOV", "HP", "PTEN", "RIG", "VAL", "FANG",
    # Utilities (more)
    "ED", "AEE", "ES", "PEG", "EIX", "FE", "CNP", "AEP",
    # Biotech / pharma (more)
    "GILD", "AMGN", "BMRN", "BPMC", "RARE", "ALNY",
    "NTRA", "EXAS", "TECH", "HOLX", "MTD", "WAT", "A",
    # Medical / healthcare services (more)
    "HUM", "CI", "CNC", "MOH", "MCK", "ABC", "CAH",
    # ETFs
    "IWM", "DIA", "XLF", "XLK", "XLE", "XLV", "XLI", "XLY",
    # Mid-cap tech (more)
    "GEN", "BILL", "SMAR", "DOMO", "DOCN", "CFLT", "PATH",
    # Payment / fintech (more)
    "GPN", "FISV", "WEX", "FLT", "EVO",
    # International (more)
    "BHP", "RIO", "GLNCY", "SAN", "DB", "UBS",
    "BP", "SHEL", "TTE", "SNP", "PTR", "CEO", "NSANY",
    # More diverse: mid/small cap, specialty
    "AKAM", "FFIV", "VRSN", "ANSS", "CDNS", "ANET", "CIEN", "JNPR",
    "HPE", "NTAP", "WDC", "STX", "MPWR", "SWKS", "QRVO", "MCHP",
    "DXC", "EPAM", "IT", "CTSH", "ACN", "INFY", "WIT", "HCL",
    "ULTA", "POOL", "RH", "WSM", "ETH", "HBI", "VFC",
    "CL", "EL", "CPB", "SJM", "LW", "SMPL", "LANC", "SYY",
    "LHX", "TXT", "LDOS", "HII", "NOC", "GD", "LMT", "RTX",
    "SW", "RBC", "SNA", "TTC", "XYL", "WSO", "ITW", "GNRC",
    "ROP", "OTIS", "CARR", "TT", "IR", "JCI", "WAB", "HUBB",
    "HAS", "MAT", "F", "GM", "RIVN", "LCID", "AN", "KMX",
    "LAD", "PAG", "SAH", "ABG", "CARG", "CVNA",
    "TDG", "WWD", "HWM", "ATI", "CENX", "KALU", "CMC",
    "VST", "NRG", "CWEN", "ORA", "BEPC", "BEP", "NEP",
    "SFRGY", "BG", "ADM", "TSN",
    "DG", "DLTR", "SIG", "BOOT", "BKE",
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
