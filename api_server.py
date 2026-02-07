"""
Flask API server that serves options (and scores) from output_multi_ticker.csv.
Used by the frontend for confidence/suggestions. No live pipeline—CSV only.
Run: python api_server.py   (default: http://localhost:5000)
"""
import csv
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"])

# Path to multi-ticker output CSV (project root)
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.csv")

# In-memory cache: ticker -> list of row dicts
_options_by_ticker: dict[str, list[dict]] = {}


def _option_type_from_contract(symbol: str) -> str:
    """Infer call vs put from contract symbol (e.g. ...C00700000 = call, ...P00667000 = put)."""
    if not symbol:
        return "call"
    s = str(symbol).upper()
    return "call" if "C0" in s else "put"


def _score_to_confidence(score: float) -> int:
    """Map opportunity score (roughly -100..100) to confidence 0-100."""
    try:
        v = float(score)
        c = 50 + v / 2
        return max(0, min(100, int(round(c))))
    except (TypeError, ValueError):
        return 50


def load_csv() -> None:
    """Load output_multi_ticker.csv and index by ticker."""
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
        logger.info("Loaded %d tickers, %d total options from %s",
                    len(_options_by_ticker), sum(len(v) for v in _options_by_ticker.values()), CSV_PATH)
    except Exception as e:
        logger.exception("Failed to load CSV: %s", e)


def _float_or(val, default: float = 0) -> float:
    try:
        return float(val) if val != "" else default
    except (TypeError, ValueError):
        return default


@app.route("/api/stocks/<ticker>/options", methods=["GET"])
def get_stock_options(ticker: str):
    """
    Return options for the ticker from output_multi_ticker.csv.
    Each option: ticker, type, expiration, contractSymbol, strike, price, bid,
    midPrice, score, impliedVolatility, confidence (derived from score).
    """
    ticker = ticker.strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker required"}), 400
    rows = _options_by_ticker.get(ticker, [])
    options = []
    for row in rows:
        try:
            strike = _float_or(row.get("strike"), 0)
            price = _float_or(row.get("price"), 0)
            bid = _float_or(row.get("bid"), 0)
            mid = row.get("midPrice") or row.get("price") or 0
            mid = _float_or(mid, 0)
            score = _float_or(row.get("score"), 0)
            iv = _float_or(row.get("impliedVolatility"), 0)
            opt_type = _option_type_from_contract(row.get("contractSymbol", ""))
            confidence = _score_to_confidence(score)
            options.append({
                "ticker": row.get("ticker", ticker).strip().upper(),
                "type": opt_type,
                "expiration": (row.get("expiration") or "").strip(),
                "contractSymbol": (row.get("contractSymbol") or "").strip(),
                "strike": round(strike, 2),
                "price": round(price, 2),
                "bid": round(bid, 2),
                "midPrice": round(mid, 2),
                "score": round(score, 2),
                "impliedVolatility": round(iv, 4),
                "confidence": confidence,
            })
        except (TypeError, ValueError):
            continue
    return jsonify({"options": options})


@app.route("/api/tickers", methods=["GET"])
def get_tickers():
    """Return list of tickers we have options data for (from output_multi_ticker.csv)."""
    return jsonify({"tickers": sorted(_options_by_ticker.keys())})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "tickers_loaded": len(_options_by_ticker)})


@app.before_request
def ensure_loaded():
    if not _options_by_ticker and os.path.isfile(CSV_PATH):
        load_csv()


if __name__ == "__main__":
    load_csv()
    app.run(host="0.0.0.0", port=5000, debug=False)
