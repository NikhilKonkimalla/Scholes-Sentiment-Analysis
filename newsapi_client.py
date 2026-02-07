"""
NewsAPI.ai (Event Registry) client: fetch headlines, cache to CSV, and test standalone.

Run directly to test and inspect headlines:
    python newsapi_client.py --query "SPY OR S&P 500" --n 20
    python newsapi_client.py --sectors --no-cache   # Fetch across tech, health, finance, etc.
    python newsapi_client.py --queries "AAPL,JPM,XOM" --no-cache
"""
import argparse
import csv
import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Local CSV cache for NewsAPI headlines (minimizes API credits)
CACHE_PATH = Path(__file__).resolve().parent / "newsapi_headlines.csv"

# Companies/queries across main sectors (for --sectors flag). 400 queries = 400 tokens = ~40k articles.
SECTOR_QUERIES = [
    # Technology (60)
    "Apple AAPL", "Microsoft MSFT", "Google Alphabet GOOGL", "NVIDIA NVDA", "Meta META", "Amazon AMZN", "Tesla TSLA",
    "Adobe ADBE", "Salesforce CRM", "Oracle ORCL", "Cisco CSCO", "IBM IBM", "Intel INTC", "AMD AMD", "Qualcomm QCOM",
    "Broadcom AVGO", "Texas Instruments TXN", "Netflix NFLX", "PayPal PYPL", "Square Block SQ", "Spotify SPOT",
    "Uber UBER", "Airbnb ABNB", "Zoom ZM", "Slack Salesforce", "ServiceNow NOW", "Workday WDAY", "Snowflake SNOW",
    "Datadog DDOG", "CrowdStrike CRWD", "Palo Alto PANW", "Fortinet FTNT", "Zscaler ZS", "Cloudflare NET",
    "Shopify SHOP", "Etsy ETSY", "MercadoLibre MELI", "Sea Limited SE", "Grab GRAB", "DoorDash DASH",
    "Taiwan Semiconductor TSM", "ASML ASML", "Samsung electronics", "Micron MU", "Western Digital WDC", "Seagate STX",
    "Applied Materials AMAT", "Lam Research LRCX", "Synopsys SNPS", "Cadence CDNS", "Ansys ANSS",
    "Atlassian TEAM", "DocuSign DOCU", "Twilio TWLO", "Okta OKTA", "Splunk", "Elastic ESTC",
    "Alibaba BABA", "Tencent", "JD.com JD", "Baidu BIDU", "Sony SONY",
    # Healthcare (70)
    "Johnson Johnson JNJ", "UnitedHealth UNH", "Pfizer PFE", "Merck MRK", "Eli Lilly LLY", "AbbVie ABBV",
    "Bristol Myers BMY", "Amgen AMGN", "Gilead GILD", "Thermo Fisher TMO", "Abbott ABT", "Danaher DHR",
    "Moderna MRNA", "Regeneron REGN", "Vertex VRTX", "Biogen BIIB", "Gilead Sciences", "AstraZeneca AZN",
    "Novartis NVS", "Roche", "Sanofi SNY", "GlaxoSmithKline GSK", "Takeda TAK", "Bayer",
    "Medtronic MDT", "Boston Scientific BSX", "Edwards Lifesciences EW", "Stryker SYK", "Zimmer Biomet ZBH",
    "Intuitive Surgical ISRG", "Dexcom DXCM", "Abbott diabetes", "Becton Dickinson BDX", "Siemens Healthineers",
    "UnitedHealth Group", "Anthem Elevance ELV", "Cigna CI", "Humana HUM", "CVS Health CVS", "McKesson MCK",
    "AmerisourceBergen ABC", "Cardinal Health CAH", "HCA Healthcare HCA", "Tenet THC", "Universal Health UHS",
    "Laboratory Corp LH", "Quest Diagnostics DGX", "Charles River CRL", "IQVIA IQV", "Illumina ILMN",
    "Exact Sciences EXAS", "Guardant Health GH", "Invitae", "10x Genomics TXG", "Pacific Biosciences PACB",
    "CRISPR Therapeutics", "Bluebird Bio", "Sarepta SRPT", "BioMarin BMRN", "Alnylam ALNY",
    "IDEXX IDXX", "Zoetis ZTS", "Veterinary diagnostics", "Catalent CTLT", "Lonza",
    "Teladoc TDOC", "Oscar Health OSCR", "Clover Health CLOV", "Alignment Healthcare ALHC",
    "Pharmacy benefit managers", "Medicare Medicaid", "Drug pricing", "FDA approval", "clinical trials",
    # Finance (70)
    "JPMorgan JPM", "Bank of America BAC", "Goldman Sachs GS", "Morgan Stanley MS", "Wells Fargo WFC", "Citigroup C",
    "American Express AXP", "BlackRock BLK", "Charles Schwab SCHW", "S&P Global SPGI", "CME Group CME",
    "Intercontinental Exchange ICE", "Moody's MCO", "MSCI MSCI", "FactSet FDS", "CBOE CBOE",
    "State Street STT", "Northern Trust NTRS", "BNY Mellon BK", "Capital One COF", "Discover DFS",
    "Ally Financial ALLY", "Synchrony SYF", "Fifth Third FITB", "PNC PNC", "US Bancorp USB", "Truist TFC",
    "Citizens Financial CFG", "KeyCorp KEY", "Huntington HBAN", "Regions RF", "M&T Bank MTB",
    "First Republic", "SVB Silicon Valley Bank", "Signature Bank", "Kreisler Borg",
    "Visa V", "Mastercard MA", "PayPal payments", "Square payments", "Fiserv FI", "Global Payments GPN",
    "Adyen", "Stripe", "Block Inc", "Affirm AFRM", "SoFi SOFI", "Robinhood HOOD",
    "LendingClub LC", "Upstart UPST", "Marqeta MQ", "Bread Financial BFH",
    "Berkshire Hathaway BRK", "Aon AON", "Marsh McLennan MMC", "Chubb CB", "Travelers TRV",
    "Progressive PGR", "Allstate ALL", "MetLife MET", "Prudential PRU", "Aflac AFL",
    "KKR KKR", "Apollo APO", "Blackstone BX", "Carlyle CG", "Ares ARES",
    "Federal Reserve", "interest rates", "bank earnings", "credit card debt", "mortgage rates",
    "Treasury bonds", "yield curve", "inflation CPI", "GDP economy", "jobs report unemployment",
    # Consumer (70)
    "Walmart WMT", "Procter Gamble PG", "Coca-Cola KO", "Costco COST", "PepsiCo PEP", "McDonald's MCD", "Nike NKE", "Home Depot HD",
    "Target TGT", "Lowe's LOW", "TJX TJX", "Dollar General DG", "Dollar Tree DLTR", "Ross Stores ROST",
    "Starbucks SBUX", "Chipotle CMG", "Yum Brands YUM", "Domino's DPZ", "Wendy's WEN", "Restaurant Brands QSR",
    "Colgate-Palmolive CL", "Kimberly-Clark KMB", "Clorox CLX", "Church Dwight CHD", "Estee Lauder EL",
    "L'Oréal", "Unilever UL", "Mondelez MDLZ", "General Mills GIS", "Kellogg K", "Campbell CPB",
    "Hershey HSY", "Monster Beverage MNST", "Keurig Dr Pepper KDP", "Constellation Brands STZ",
    "Molson Coors TAP", "Brown-Forman BF.B", "Diageo DEO", "Pernod Ricard",
    "Ford F", "General Motors GM", "Stellantis", "Toyota TM", "Honda HMC", "Rivian RIVN", "Lucid LCID",
    "AutoZone AZO", "O'Reilly ORLY", "Advance Auto Parts AAP", "CarMax KMX", "Carvana CVNA",
    "Marriott MAR", "Hilton HLT", "Hyatt H", "Expedia EXPE", "Booking Holdings BKNG", "Tripadvisor TRIP",
    "Royal Caribbean RCL", "Carnival CCL", "Norwegian Cruise NCLH", "Disney Parks DIS",
    "Wynn WYNN", "Las Vegas Sands LVS", "MGM MGM", "Caesars CZR", "Penn Entertainment PENN",
    "Lululemon LULU", "Under Armour UAA", "VF Corp VFC", "Skechers SKX", "Crocs CROX",
    "Tapestry TPR", "Capri Holdings", "Ralph Lauren RL", "PVH PVH",
    "consumer spending", "retail sales", "holiday shopping", "inflation consumer",
    # Energy (50)
    "Exxon Mobil XOM", "Chevron CVX", "ConocoPhillips COP", "Schlumberger SLB", "EOG Resources EOG",
    "Marathon Petroleum MPC", "Valero VLO", "Phillips 66 PSX", "Pioneer Natural PXD", "Devon Energy DVN",
    "Occidental OXY", "Hess HES", "Diamondback FANG", "Coterra CTRA", "APA Corp APA",
    "Baker Hughes BKR", "Halliburton HAL", "NOV NOV", "Helmerich Payne HP", "Nabors NBR",
    "Cheniere LNG", "Kinder Morgan KMI", "Williams WMB", "Enterprise Products EPD", "MPLX MPLX",
    "NextEra Energy NEE", "Duke Energy DUK", "Southern Company SO", "Dominion D", "American Electric AEP",
    "Exelon EXC", "Xcel Energy XEL", "WEC Energy WEC", "Public Service Enterprise PEG", "Consolidated Edison ED",
    "FirstEnergy FE", "DTE Energy DTE", "Alliant Energy LNT", "CMS Energy CMS",
    "Enphase ENPH", "SolarEdge SEDG", "First Solar FSLR", "SunPower SPWR", "Sunrun RUN",
    "Bloom Energy BE", "Plug Power PLUG", "FuelCell FCEL", "Clean Energy CLNE",
    "oil prices", "natural gas prices", "OPEC", "energy transition", "renewable energy",
    "electric vehicles EV", "lithium battery", "nuclear power",
    # Industrials (50)
    "Caterpillar CAT", "Boeing BA", "Union Pacific UNP", "Honeywell HON", "UPS", "FedEx FDX",
    "GE Aerospace GE", "Lockheed Martin LMT", "Raytheon RTX", "Northrop Grumman NOC", "General Dynamics GD",
    "Deere DE", "3M MMM", "Emerson EMR", "Rockwell Automation ROK", "Parker Hannifin PH",
    "Eaton ETN", "Cummins CMI", "Illinois Tool Works ITW", "Stanley Black Decker SWK",
    "CSX CSX", "Norfolk Southern NSC", "Kansas City Southern", "JB Hunt JBHT", "CH Robinson CHRW",
    "Expeditors EXPD", "XPO XPO", "Old Dominion ODFL", "Landstar LSTR", "Ryder R",
    "Waste Management WM", "Republic Services RSG", "Waste Connections WCN", "Casella CWST",
    "Carrier CARR", "Trane Technologies TT", "Johnson Controls JCI", "Lennox LII",
    "Fastenal FAST", "Grainger GWW", "MSC Industrial MSM", "W.W. Grainger",
    "Pentair PNR", "IDEX IEX", "Dover DOV", "Fortive FTV", "Roper ROP",
    "Huntington Ingalls HII", "L3Harris LHX", "BAE Systems", "TransDigm TDG",
    "agriculture equipment", "defense spending", "logistics freight", "manufacturing PMI",
    # Materials & Real Estate (30)
    "Linde LIN", "Sherwin-Williams SHW", "Prologis PLD", "American Tower AMT", "Equinix EQIX",
    "Newmont NEM", "Freeport-McMoRan FCX", "Nucor NUE", "Steel Dynamics STLD", "Cleveland-Cliffs CLF",
    "Dow DOW", "DuPont DD", "LyondellBasell LYB", "Eastman EMN", "Celanese CE",
    "Air Products APD", "PPG PPG", "Albemarle ALB", "Livent LTHM", "SQM",
    "Martin Marietta MLM", "Vulcan Materials VMC", "Eagle Materials EXP", "Summit Materials SUM",
    "Simon Property SPG", "Welltower WELL", "Ventas VTR", "Digital Realty DLR", "Crown Castle CCI",
    "CBRE CBRE", "Jones Lang LaSalle JLL", "Costar CSGP", "Zillow Z",
    "housing market", "commercial real estate", "copper gold metals",
]

# Use first 400 queries when --sectors (400 tokens = 40k articles)
SECTOR_QUERIES_400 = SECTOR_QUERIES[:400]


def save_headlines_to_csv(headlines: list[dict], query: str) -> None:
    """Append NewsAPI headlines to local CSV cache. Called after every successful API fetch."""
    if not headlines:
        return
    try:
        write_header = not CACHE_PATH.exists()
        fetched_at = datetime.now(timezone.utc).isoformat()
        with open(CACHE_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["query", "title", "source", "publishedAt", "url", "fetched_at"])
            for h in headlines:
                w.writerow([
                    query,
                    h.get("title", ""),
                    h.get("source", ""),
                    h.get("publishedAt", ""),
                    h.get("url", ""),
                    fetched_at,
                ])
        logger.info("Saved %d headlines to %s", len(headlines), CACHE_PATH)
    except Exception as e:
        logger.warning("Could not save headlines to CSV: %s", e)


def load_headlines_from_csv(query: str, n: int, max_age_hours: float = 24.0) -> list[dict] | None:
    """
    Load cached headlines for the given query if we have recent data.
    Returns list of dicts or None if cache miss.
    """
    if not CACHE_PATH.exists():
        return None
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        rows = []
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("query") != query:
                    continue
                try:
                    ft = row.get("fetched_at", "")
                    if ft:
                        dt = datetime.fromisoformat(ft.replace("Z", "+00:00"))
                        if dt < cutoff:
                            continue
                except (ValueError, TypeError):
                    continue
                rows.append({
                    "title": row.get("title", ""),
                    "source": row.get("source", ""),
                    "publishedAt": row.get("publishedAt", ""),
                    "url": row.get("url", ""),
                })
        if not rows:
            return None
        # Dedupe by url, keep most recent by publishedAt
        seen = set()
        unique = []
        for r in reversed(rows):
            u = r.get("url") or r.get("title", "")
            if u and u not in seen:
                seen.add(u)
                unique.append(r)
        unique.reverse()
        return unique[:n]
    except Exception as e:
        logger.warning("Could not load headlines from CSV: %s", e)
        return None


def fetch_headlines(
    query: str,
    api_key: str,
    n: int = 100,
    use_cache: bool = True,
    cache_max_age_hours: float = 24.0,
) -> list[dict]:
    """
    Fetch recent headlines from NewsAPI.
    Returns list of dicts: {"title", "source", "publishedAt", "url"}.
    Uses local CSV cache first when available to minimize API credits.
    Saves all headlines to CSV after every API call.
    """
    # Try cache first (saves API credits)
    if use_cache:
        cached = load_headlines_from_csv(query, n, max_age_hours=cache_max_age_hours)
        if cached:
            logger.info("Using %d cached headlines from %s", len(cached), CACHE_PATH)
            return cached

    if not api_key or not api_key.strip():
        logger.warning("No NewsAPI.ai key provided (set NEWS_API_KEY env var)")
        return []

    try:
        from eventregistry import EventRegistry, QueryArticles, RequestArticlesInfo, QueryItems

        er = EventRegistry(apiKey=api_key)
        # Explicitly request 100 articles per API call (NewsAPI.ai: 100 per search = 1 token)
        req_info = RequestArticlesInfo(page=1, count=100, sortBy="date", sortByAsc=False)
        # Parse "A OR B OR C" into QueryItems.OR; add broad fallback to ensure we hit 100 per call
        FALLBACK_TERMS = ("stock market", "business news")  # broad terms to fill when query is thin
        parts = re.split(r"\s+OR\s+", query, flags=re.IGNORECASE)
        if len(parts) > 1:
            orig_terms = [t.strip() for t in parts if t.strip()]
            terms = orig_terms + list(FALLBACK_TERMS) if len(orig_terms) > 1 else [query] + list(FALLBACK_TERMS)
        else:
            terms = [query] + list(FALLBACK_TERMS)
        keywords = QueryItems.OR(terms)
        q = QueryArticles(keywords=keywords, lang="eng", requestedResult=req_info)
        res = er.execQuery(q)
        if "error" in res:
            logger.error("Event Registry error: %s", res["error"])
            return []
        articles = res.get("articles", {}).get("results", []) or []
        total_avail = res.get("articles", {}).get("totalResults", 0)
        logger.info("API returned %d articles (total match: %d) for query: %s", len(articles), total_avail, query)
        # Dedupe by url, take up to n (100) to ensure we hit 100 per API call
        seen_urls: set[str] = set()
        out = []
        for art in articles:
            if len(out) >= n:
                break
            if not art:
                continue
            url = art.get("url") or art.get("uri") or ""
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            title = art.get("title") or ""
            pub = art.get("dateTimePub") or art.get("date") or art.get("time") or ""
            if hasattr(pub, "isoformat"):
                published_at = pub.isoformat()
            else:
                published_at = str(pub) if pub else ""
            src = art.get("source")
            if isinstance(src, dict):
                source = src.get("title") or src.get("uri") or ""
            else:
                source = str(src) if src else ""
            out.append({
                "title": title,
                "source": source,
                "publishedAt": published_at,
                "url": url,
            })

        if len(out) < n:
            logger.warning("Query '%s' returned %d articles (target: %d); broad OR fallback already used", query, len(out), n)

        # Save locally after every API call
        save_headlines_to_csv(out, query)

        return out
    except Exception as e:
        logger.exception("fetch_headlines failed: %s", e)
        return []


def main() -> int:
    """CLI entrypoint: fetch headlines and print them for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(
        description="NewsAPI.ai client: fetch headlines and test. Set NEWS_API_KEY env var."
    )
    parser.add_argument("--query", type=str, default="SPY OR S&P 500", help="Search query (ignored if --queries is set)")
    parser.add_argument("--queries", type=str, default="",
                        help="Comma-separated queries to run")
    parser.add_argument("--sectors", action="store_true",
                        help="Use predefined queries across main sectors (tech, health, finance, consumer, energy, industrials, etc.)")
    parser.add_argument("--n", type=int, default=100, help="Number of headlines per query (NewsAPI.ai allows up to 100)")
    parser.add_argument("--no-cache", action="store_true", help="Force API fetch (ignore cache)")
    parser.add_argument("--cache-hours", type=float, default=24.0, help="Cache validity in hours")
    args = parser.parse_args()

    api_key = os.environ.get("NEWS_API_KEY", "").strip()
    if not api_key and args.no_cache:
        print("Error: NEWS_API_KEY must be set for API calls. Run: set NEWS_API_KEY=your_key", file=sys.stderr)
        return 1

    # Build list of queries to run
    if args.sectors:
        queries = SECTOR_QUERIES_400
    elif args.queries.strip():
        queries = [q.strip() for q in args.queries.split(",") if q.strip()]
    else:
        queries = [args.query]

    total = 0
    for qi, query in enumerate(queries, 1):
        print(f"\n[{qi}/{len(queries)}] Fetching: {query}")
        headlines = fetch_headlines(
            query=query,
            api_key=api_key,
            n=args.n,
            use_cache=not args.no_cache,
            cache_max_age_hours=args.cache_hours,
        )

        if not headlines:
            print(f"  No headlines returned for '{query}'", file=sys.stderr)
            continue

        total += len(headlines)
        print(f"  Got {len(headlines)} headlines")
        for i, h in enumerate(headlines[:5], 1):  # show first 5
            title = (h.get("title") or "(no title)").replace("\n", " ")[:70]
            source = h.get("source", "")
            print(f"    {i}. [{source}] {title}...")
        if len(headlines) > 5:
            print(f"    ... and {len(headlines) - 5} more")

    print(f"\n--- Total: {total} headlines across {len(queries)} query/queries ---")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
