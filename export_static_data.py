"""
Export the site's data as static JSON so the frontend can be hosted with no backend.

Every file is the literal response of the matching API route, produced through Flask's
test client, so the hosted (static) site and the local (API) site cannot drift apart:

  data/meta.json                 /api/health (+ export stats)
  data/tickers.json              /api/tickers
  data/top-options.json          /api/options/top?limit=N
  data/options/<TICKER>.json     /api/stocks/<TICKER>/options
  data/quote/<TICKER>.json       /api/stocks/<TICKER>/quote        (page tickers only)
  data/history/<TICKER>.json     /api/stocks/<TICKER>/history      (page tickers only)
  data/sentiment/<TICKER>.json   /api/stocks/<TICKER>/ai-summary   (page tickers only)

"Page tickers" are the ones the site links to: the frontend's sector map, extra tickers
and carousel, plus every ticker in the top-options list. Quotes, history and sentiment
call Yahoo live, so they are limited to those rather than all ~500 symbols.

Usage:
  python export_static_data.py                 # data.csv -> frontend/public/data
  python export_static_data.py --skip-live     # options only, no Yahoo calls
"""
import argparse
import json
import logging
import math
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("export_static_data")

# Ticker symbols become filenames, so only accept symbol-shaped strings.
TICKER_RE = re.compile(r"^[A-Z0-9.\-^]{1,12}$")


def ui_tickers(frontend_src: Path) -> set[str]:
    """Tickers the frontend links to directly: sector map, extra tickers, carousel."""
    found: set[str] = set()
    stocks_ts = frontend_src / "mock" / "stocks.ts"
    if stocks_ts.exists():
        text = stocks_ts.read_text(encoding="utf-8")
        block = re.search(r"MOCK_STOCKS_BY_SECTOR[^=]*=\s*\{(.*?)\n\};", text, re.S)
        if block:
            found.update(re.findall(r"ticker:\s*'([A-Z.]+)'", block.group(1)))
        block = re.search(r"EXTRA_TICKER_SECTORS[^=]*=\s*\{(.*?)\n\};", text, re.S)
        if block:
            found.update(re.findall(r"\b([A-Z.]+):\s*'[a-z]+'", block.group(1)))
    carousel = frontend_src / "components" / "HeroChartCarousel.tsx"
    if carousel.exists():
        block = re.search(r"CAROUSEL_TICKERS\s*=\s*\[([^\]]*)\]", carousel.read_text(encoding="utf-8"))
        if block:
            found.update(re.findall(r"'([A-Z.]+)'", block.group(1)))
    return found


def _clean(obj):
    """Replace NaN/inf with None: they are not valid JSON and browsers reject them."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def export(
    csv_path,
    out_dir,
    *,
    top_limit: int = 200,
    page_top: int = 100,
    live: bool = True,
    delay: float = 0.25,
    frontend_src=ROOT / "frontend" / "src",
) -> dict:
    """Write the static data tree. Returns counts of what was exported."""
    import api_server

    csv_path = Path(csv_path).resolve()
    out = Path(out_dir).resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)
    # The output directory is wiped and rewritten; refuse anything that is not
    # obviously a previous export, so a mistyped --out cannot delete real files.
    if out.exists() and any(out.iterdir()) and not (out / "meta.json").exists():
        raise RuntimeError(
            f"Refusing to clear {out}: it is not empty and has no meta.json from a previous export."
        )

    saved_path, saved_rows = api_server.CSV_PATH, api_server._options_by_ticker
    api_server.CSV_PATH = str(csv_path)
    try:
        api_server.load_csv()
        client = api_server.app.test_client()

        def fetch(url: str):
            resp = client.get(url)
            return _clean(resp.get_json()) if resp.status_code == 200 else None

        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        tickers = [t for t in (fetch("/api/tickers") or {}).get("tickers", []) if TICKER_RE.match(t)]
        _write(out / "tickers.json", {"tickers": tickers})
        for t in tickers:
            _write(out / "options" / f"{t}.json", fetch(f"/api/stocks/{t}/options") or {"options": []})

        top = fetch(f"/api/options/top?limit={top_limit}") or {"options": [], "total": 0}
        # The home page links every row to /stocks/<ticker>, so the list needs the same
        # symbol check as the per-ticker files, or a malformed ticker becomes a bad link.
        top["options"] = [o for o in top.get("options", []) if TICKER_RE.match(o.get("ticker", ""))]
        _write(out / "top-options.json", top)

        page = ui_tickers(Path(frontend_src)) if frontend_src else set()
        page.update(o["ticker"] for o in top.get("options", [])[:page_top])
        page_tickers = sorted(t for t in page if TICKER_RE.match(t))

        stats = {
            "optionFiles": len(tickers),
            "pageTickers": len(page_tickers),
            "quotes": 0,
            "history": 0,
            "sentiment": 0,
        }

        if live:
            for i, t in enumerate(page_tickers, 1):
                quote = fetch(f"/api/stocks/{t}/quote")
                if quote:
                    _write(out / "quote" / f"{t}.json", quote)
                    stats["quotes"] += 1
                history = fetch(f"/api/stocks/{t}/history?period=1mo")
                if history and history.get("prices"):
                    _write(out / "history" / f"{t}.json", history)
                    stats["history"] += 1
                sentiment = fetch(f"/api/stocks/{t}/ai-summary")
                if sentiment:
                    _write(out / "sentiment" / f"{t}.json", sentiment)
                    stats["sentiment"] += 1 if sentiment.get("available") else 0
                logger.info("[%d/%d] %s quote=%s history=%s sentiment=%s", i, len(page_tickers), t,
                            bool(quote), bool(history and history.get("prices")),
                            bool(sentiment and sentiment.get("available")))
                time.sleep(delay)

        meta = fetch("/api/health") or {"status": "ok"}
        meta["exportedAt"] = datetime.now(timezone.utc).isoformat()
        meta["export"] = stats
        _write(out / "meta.json", meta)
        return stats
    finally:
        api_server.CSV_PATH, api_server._options_by_ticker = saved_path, saved_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export site data as static JSON for backend-free hosting")
    parser.add_argument("--csv", default=str(ROOT / "data.csv"), help="Options CSV (default: data.csv)")
    parser.add_argument("--out", default=str(ROOT / "frontend" / "public" / "data"),
                        help="Output directory (default: frontend/public/data)")
    parser.add_argument("--top", type=int, default=200, help="Contracts in top-options.json (default 200)")
    parser.add_argument("--page-top", type=int, default=100,
                        help="Also snapshot quote/history/sentiment for tickers in the top N contracts")
    parser.add_argument("--skip-live", action="store_true",
                        help="Skip quotes, history and sentiment (no Yahoo calls)")
    parser.add_argument("--delay", type=float, default=0.25, help="Seconds between tickers when fetching live data")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    stats = export(args.csv, args.out, top_limit=args.top, page_top=args.page_top,
                   live=not args.skip_live, delay=args.delay)
    print(json.dumps(stats))
    if stats["optionFiles"] == 0:
        logger.error("No live options were exported; refusing to publish an empty site.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
