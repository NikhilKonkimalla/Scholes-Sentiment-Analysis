"""
Flask API server: options from data.csv (or output_multi_ticker.csv), stock history/quote from yfinance.
Run: python api_server.py   (default: http://localhost:5000)

Environment overrides:
  CSV_PATH      path to the options CSV (default: data.csv next to this file)
  CORS_ORIGINS  comma-separated allowed browser origins, or "*" (default: local Vite dev servers)
  PORT          port to bind (default: 5000)

Expired contracts are filtered out of responses by default; pass ?include_expired=true
to see them. A stale CSV would otherwise surface long-dead options as live suggestions.

Note: on macOS, AirPlay Receiver occupies port 5000 and answers requests with 403.
Either turn it off in System Settings > General > AirDrop & Handoff, or set PORT.
"""
import csv
import json
import logging
import os
import re
from datetime import datetime, timezone

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from market_data import get_history, get_quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Allowed browser origins. The default only covers local development; a deployed
# frontend must be added via CORS_ORIGINS, otherwise the browser blocks every call
# and the UI silently falls back to mock data.
_DEFAULT_ORIGINS = [
    "http://localhost:5173", "http://localhost:5174",
    "http://127.0.0.1:5173", "http://127.0.0.1:5174",
]
_origins_env = os.environ.get("CORS_ORIGINS", "").strip()
if _origins_env == "*":
    CORS_ORIGINS: "list[str] | str" = "*"
else:
    CORS_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()] or _DEFAULT_ORIGINS
CORS(app, origins=CORS_ORIGINS)

# Path to the options CSV (project root). Override with CSV_PATH.
CSV_PATH = os.environ.get("CSV_PATH", "").strip() or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data.csv"
)

# In-memory cache: ticker -> list of row dicts
_options_by_ticker: dict[str, list[dict]] = {}

# OCC contract symbols look like AAPL260213P00052000: ticker, 6-digit date,
# C or P, then an 8-digit strike.
_OPTION_TYPE_RE = re.compile(r"\d{6}([CP])\d{8}$")


def _option_type_from_contract(symbol: str) -> str:
    """
    Infer call vs put from an OCC contract symbol (e.g. AAPL260213P00052000 = put).
    Matches the type letter by position; a bare "C0" substring search would misread
    any ticker that itself contains "C0".
    """
    if not symbol:
        return "call"
    s = str(symbol).upper()
    m = _OPTION_TYPE_RE.search(s)
    if m:
        return "call" if m.group(1) == "C" else "put"
    logger.debug("Unrecognized contract symbol shape: %s", s)
    return "call" if "C0" in s else "put"


def _parse_expiration(value: str):
    """Parse an expiration cell into an aware UTC datetime, or None if unparseable."""
    s = (value or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _is_expired(row: dict, now: datetime) -> bool:
    """
    True when the row's expiration is in the past. Rows with an unparseable or
    missing expiration are treated as NOT expired, so bad data is surfaced rather
    than silently dropped.
    """
    dt = _parse_expiration(row.get("expiration", ""))
    return dt is not None and dt < now


def _wants_expired() -> bool:
    """Whether the caller asked to include expired contracts (?include_expired=true)."""
    return request.args.get("include_expired", "").strip().lower() in {"1", "true", "yes"}


def _excludes_risky() -> bool:
    """Whether the caller asked to drop risk-flagged contracts (?exclude_risky=true)."""
    return request.args.get("exclude_risky", "").strip().lower() in {"1", "true", "yes"}


def _data_as_of() -> str | None:
    """
    When the options snapshot was generated, as an ISO timestamp.

    Prefers the sidecar data_meta.json written by pipeline_multi_ticker.py. File
    mtimes are only a fallback because they are unreliable in deployment: a fresh
    git checkout stamps every file with the deploy time, which would report stale
    data as brand new.
    """
    meta_path = os.path.join(os.path.dirname(os.path.abspath(CSV_PATH)), "data_meta.json")
    try:
        if os.path.isfile(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                generated = json.load(f).get("generatedAt")
            if generated:
                return str(generated)
    except (OSError, ValueError) as e:
        logger.debug("Could not read %s: %s", meta_path, e)
    try:
        return datetime.fromtimestamp(os.path.getmtime(CSV_PATH), tz=timezone.utc).isoformat()
    except OSError:
        return None


def _score_to_confidence(score: float) -> int:
    """Map opportunity score (roughly -100..100) to confidence 0-100."""
    try:
        v = float(score)
        c = 50 + v / 2
        return max(0, min(100, int(round(c))))
    except (TypeError, ValueError):
        return 50


def load_csv() -> None:
    """Load CSV (data.csv or output_multi_ticker.csv) and index by ticker."""
    global _options_by_ticker
    _options_by_ticker = {}
    if not os.path.isfile(CSV_PATH):
        logger.warning("CSV not found: %s", CSV_PATH)
        return
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = (row.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                _options_by_ticker.setdefault(ticker, []).append(row)
        total = sum(len(v) for v in _options_by_ticker.values())
        now = datetime.now(timezone.utc)
        expired = sum(
            1 for rows in _options_by_ticker.values() for r in rows if _is_expired(r, now)
        )
        logger.info("Loaded %d tickers, %d total options from %s",
                    len(_options_by_ticker), total, CSV_PATH)
        if expired:
            logger.warning(
                "%d of %d options in %s are already expired and are filtered from "
                "responses; regenerate the CSV with pipeline_multi_ticker.py",
                expired, total, os.path.basename(CSV_PATH),
            )
    except Exception as e:
        logger.exception("Failed to load CSV: %s", e)


def _float_or(val, default: float = 0) -> float:
    try:
        return float(val) if val != "" else default
    except (TypeError, ValueError):
        return default


def _float_or_none(val) -> float | None:
    """
    Parse an optional numeric cell. None means "not in the data" — distinct from 0,
    which for volume or open interest is a real and meaningful value.
    """
    if val is None or str(val).strip() == "":
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN is not valid JSON


def _bool_or_none(val) -> bool | None:
    """Parse an optional boolean cell written by csv.DictWriter ("True"/"False")."""
    s = str(val).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None


def _row_to_option(row: dict, fallback_ticker: str = "") -> dict | None:
    """
    Map one CSV row to the option shape the frontend consumes. None if unusable.

    Risk fields are optional: a CSV generated before they were added simply yields
    null, and the UI omits the badge rather than claiming a contract is safe.
    """
    try:
        strike = _float_or(row.get("strike"), 0)
        price = _float_or(row.get("price"), 0)
        bid = _float_or(row.get("bid"), 0)
        mid = _float_or(row.get("midPrice") or row.get("price") or 0, 0)
        score = _float_or(row.get("score"), 0)
        iv = _float_or(row.get("impliedVolatility"), 0)
        ask = _float_or_none(row.get("ask"))
        spread_penalty = _float_or_none(row.get("spreadPenalty"))
        return {
            "ticker": (row.get("ticker") or fallback_ticker).strip().upper(),
            "type": _option_type_from_contract(row.get("contractSymbol", "")),
            "expiration": (row.get("expiration") or "").strip(),
            "contractSymbol": (row.get("contractSymbol") or "").strip(),
            "strike": round(strike, 2),
            "price": round(price, 2),
            "bid": round(bid, 2),
            "ask": round(ask, 2) if ask is not None else None,
            "midPrice": round(mid, 2),
            "score": round(score, 2),
            "impliedVolatility": round(iv, 4),
            "confidence": _score_to_confidence(score),
            # Risk / liquidity signal
            "riskFlag": _bool_or_none(row.get("riskFlag")),
            "volume": _float_or_none(row.get("volume")),
            "openInterest": _float_or_none(row.get("openInterest")),
            "theoPrice": _float_or_none(row.get("theoPrice")),
            "liquidityScore": _float_or_none(row.get("liquidityScore")),
            "spreadPenalty": round(spread_penalty, 4) if spread_penalty is not None else None,
        }
    except (TypeError, ValueError):
        return None


@app.route("/api/stocks/<ticker>/options", methods=["GET"])
def get_stock_options(ticker: str):
    """
    Return options for the ticker from the loaded CSV.
    Expired contracts are omitted unless ?include_expired=true.
    Risk-flagged contracts are included but marked; ?exclude_risky=true drops them.
    """
    ticker = ticker.strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400
    rows = _options_by_ticker.get(ticker, [])
    include_expired = _wants_expired()
    exclude_risky = _excludes_risky()
    now = datetime.now(timezone.utc)
    options = []
    for row in rows:
        if not include_expired and _is_expired(row, now):
            continue
        opt = _row_to_option(row, ticker)
        if opt is None:
            continue
        if exclude_risky and opt["riskFlag"] is True:
            continue
        options.append(opt)
    return jsonify({"options": options})


@app.route("/api/options/top", methods=["GET"])
def get_top_options():
    """
    Highest-conviction options across every ticker, ranked by |score|.

    Backs the home page, which previously showed a hardcoded table of invented
    positions. Risk-flagged contracts are returned (marked) rather than hidden, so
    a high score is never shown without its caveat; ?exclude_risky=true drops them.
    Query: limit (default 25, max 200), type=call|put, include_expired, exclude_risky.
    """
    try:
        limit = int(request.args.get("limit", "25"))
    except ValueError:
        limit = 25
    limit = max(1, min(limit, 200))

    want_type = request.args.get("type", "").strip().lower()
    if want_type not in {"call", "put"}:
        want_type = ""

    include_expired = _wants_expired()
    exclude_risky = _excludes_risky()
    now = datetime.now(timezone.utc)

    options = []
    for ticker, rows in _options_by_ticker.items():
        for row in rows:
            if not include_expired and _is_expired(row, now):
                continue
            opt = _row_to_option(row, ticker)
            if opt is None:
                continue
            if want_type and opt["type"] != want_type:
                continue
            if exclude_risky and opt["riskFlag"] is True:
                continue
            options.append(opt)

    options.sort(key=lambda o: abs(o["score"]), reverse=True)
    page = options[:limit]
    return jsonify({
        "options": page,
        "total": len(options),
        "riskFlagged": sum(1 for o in options if o["riskFlag"] is True),
        "dataAsOf": _data_as_of(),
    })


@app.route("/api/tickers", methods=["GET"])
def get_tickers():
    """
    Tickers we have options data for. Tickers whose options have all expired are
    omitted unless ?include_expired=true, so the UI does not offer dead symbols.
    """
    if _wants_expired():
        return jsonify({"tickers": sorted(_options_by_ticker.keys())})
    now = datetime.now(timezone.utc)
    live = [
        t for t, rows in _options_by_ticker.items()
        if any(not _is_expired(r, now) for r in rows)
    ]
    return jsonify({"tickers": sorted(live)})


@app.route("/api/stocks/<ticker>/history", methods=["GET"])
def get_stock_history(ticker: str):
    """
    Return historical OHLC for the ticker from Yahoo Finance.
    Query: period=1mo (default), 5d, 1mo, 3mo, 6mo, 1y.
    Response: { prices: [{ date, price }], ohlc: [{ date, open, high, low, close }] }
    """
    ticker = ticker.strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400
    period = request.args.get("period", "1mo").strip() or "1mo"
    try:
        df = get_history(ticker, period=period)
        if df is None or df.empty:
            return jsonify({"prices": [], "ohlc": []})
        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else (df.columns[0] if len(df.columns) else None)
        if date_col is not None:
            df["_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
        else:
            df["_date"] = [str(x)[:10] for x in df.index]
        prices = []
        ohlc = []
        for _, row in df.iterrows():
            d = str(row.get("_date", ""))[:10]
            if not d or d.startswith("nat") or d == "nan":
                continue
            try:
                open_ = float(row.get("open", 0))
                high = float(row.get("high", 0))
                low = float(row.get("low", 0))
                close = float(row.get("close", 0))
            except (TypeError, ValueError):
                continue
            prices.append({"date": d, "price": round(close, 2)})
            ohlc.append({"date": d, "open": round(open_, 2), "high": round(high, 2), "low": round(low, 2), "close": round(close, 2)})
        return jsonify({"prices": prices, "ohlc": ohlc})
    except Exception as e:
        logger.exception("History failed for %s: %s", ticker, e)
        return jsonify({"prices": [], "ohlc": []})


@app.route("/api/stocks/<ticker>/quote", methods=["GET"])
def get_stock_quote(ticker: str):
    """Return current price and day change from Yahoo Finance. { currentPrice, dayChangePercent }"""
    ticker = ticker.strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400
    try:
        q = get_quote(ticker)
        if q is None:
            return jsonify({"error": "Quote unavailable"}), 404
        return jsonify(q)
    except Exception as e:
        logger.exception("Quote failed for %s: %s", ticker, e)
        return jsonify({"error": "Quote failed"}), 500


# Per-ticker sentiment is cached: scoring hits Yahoo for headlines, and Yahoo
# rate-limits hard once a handful of page views fan out across tickers.
_AI_SUMMARY_TTL_SECONDS = float(os.environ.get("AI_SUMMARY_TTL_SECONDS", "900"))
_ai_summary_cache: dict[str, tuple[datetime, dict]] = {}


def _describe_sentiment(mean: float, count: int, pos: int, neg: int, neu: int) -> str:
    """
    Plain description of what the sentiment model actually measured.

    Deliberately descriptive and never prescriptive. This replaces hand-written
    per-ticker trade advice, so it must not reintroduce any: it reports the numbers
    and nothing more.
    """
    if mean >= 0.35:
        label = "strongly positive"
    elif mean >= 0.10:
        label = "positive"
    elif mean > -0.10:
        label = "roughly neutral"
    elif mean > -0.35:
        label = "negative"
    else:
        label = "strongly negative"
    noun = "headline" if count == 1 else "headlines"
    return (
        f"News sentiment across {count} recent {noun} is {label} (mean {mean:+.2f}). "
        f"{pos} positive, {neg} negative, {neu} neutral."
    )


def _sentiment_unavailable(ticker: str, reason: str) -> dict:
    """Payload shape for 'we have no usable sentiment', so the UI can say so plainly."""
    return {
        "ticker": ticker,
        "available": False,
        "reason": reason,
        "summary": "",
        "sentimentMean": None,
        "sentimentStd": None,
        "headlineCount": 0,
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "model": None,
        "articles": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@app.route("/api/stocks/<ticker>/ai-summary", methods=["GET"])
def get_stock_ai_summary(ticker: str):
    """
    Real per-ticker news sentiment: recent Yahoo headlines scored with FinBERT
    (falling back to VADER), summarised descriptively. Replaces the hand-written
    mock commentary the frontend used to display as "Evaluation".
    """
    ticker = ticker.strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    now = datetime.now(timezone.utc)
    cached = _ai_summary_cache.get(ticker)
    if cached and (now - cached[0]).total_seconds() < _AI_SUMMARY_TTL_SECONDS:
        return jsonify(cached[1])

    # Imported lazily so nltk (and any FinBERT extras) stay off the import path for
    # every other endpoint — this keeps cold starts and slim deploys unaffected.
    from news_sentiment import fetch_headlines_yahoo, score_headlines

    try:
        headlines = fetch_headlines_yahoo(ticker, n=25)
        result = score_headlines(headlines, model_preference="auto")
    except Exception as e:
        logger.exception("ai-summary failed for %s: %s", ticker, e)
        return jsonify(_sentiment_unavailable(ticker, "Sentiment scoring failed."))

    scored = result.get("headline_scores") or []
    if result.get("warning") or not scored:
        payload = _sentiment_unavailable(
            ticker, result.get("warning") or "No headlines available for this ticker."
        )
        # Cache the negative too, so a ticker with no news does not re-hit Yahoo
        # on every page view.
        _ai_summary_cache[ticker] = (now, payload)
        return jsonify(payload)

    pos = sum(1 for h in scored if h["score"] > 0.05)
    neg = sum(1 for h in scored if h["score"] < -0.05)
    neu = len(scored) - pos - neg
    mean = float(result.get("sentiment_mean", 0.0))

    payload = {
        "ticker": ticker,
        "available": True,
        "reason": "",
        "summary": _describe_sentiment(mean, len(scored), pos, neg, neu),
        "sentimentMean": round(mean, 4),
        "sentimentStd": round(float(result.get("sentiment_std", 0.0)), 4),
        "headlineCount": len(scored),
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "model": result.get("model"),
        "articles": [
            {
                "title": h.get("title", ""),
                "url": h.get("url", ""),
                "source": h.get("source", ""),
                "score": h.get("score", 0.0),
            }
            for h in scored[:8]
            if h.get("title")
        ],
        "generatedAt": now.isoformat(),
    }
    _ai_summary_cache[ticker] = (now, payload)
    return jsonify(payload)


@app.route("/api/health", methods=["GET"])
def health():
    now = datetime.now(timezone.utc)
    total = sum(len(v) for v in _options_by_ticker.values())
    live = sum(
        1 for rows in _options_by_ticker.values() for r in rows if not _is_expired(r, now)
    )
    return jsonify({
        "status": "ok",
        "tickers_loaded": len(_options_by_ticker),
        "options_total": total,
        "options_live": live,
        "dataAsOf": _data_as_of(),
    })


@app.before_request
def ensure_loaded():
    if not _options_by_ticker and os.path.isfile(CSV_PATH):
        load_csv()


if __name__ == "__main__":
    load_csv()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
