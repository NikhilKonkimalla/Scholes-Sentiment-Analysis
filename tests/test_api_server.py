"""Regression tests for api_server.py (offline: options routes only, no yfinance)."""
import csv
from datetime import datetime, timedelta, timezone

import pytest

import api_server

NOW = datetime.now(timezone.utc)
FUTURE = (NOW + timedelta(days=30)).isoformat()
PAST = (NOW - timedelta(days=30)).isoformat()

HEADER = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid",
          "midPrice", "score", "impliedVolatility"]
ROWS = [
    ["AAPL", FUTURE, "AAPL261016C00250000", "250.0", "5.0", "4.9", "5.0", "40.0", "0.25"],
    ["AAPL", FUTURE, "AAPL261016P00250000", "250.0", "3.0", "2.9", "3.0", "-60.0", "0.22"],
    ["OLDCO", PAST, "OLDCO260101C00100000", "100.0", "1.0", "0.9", "1.0", "20.0", "0.30"],
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    csv_path = tmp_path / "options.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(ROWS)
    monkeypatch.setattr(api_server, "CSV_PATH", str(csv_path))
    api_server.load_csv()
    return api_server.app.test_client()


def test_health_reports_live_vs_total(client):
    body = client.get("/api/health").get_json()
    assert body["status"] == "ok"
    assert body["options_total"] == 3
    assert body["options_live"] == 2


def test_expired_contracts_are_filtered_by_default(client):
    """A stale CSV must not surface long-dead contracts as live suggestions."""
    assert client.get("/api/stocks/OLDCO/options").get_json()["options"] == []
    assert len(client.get("/api/stocks/AAPL/options").get_json()["options"]) == 2


def test_expired_contracts_available_on_request(client):
    body = client.get("/api/stocks/OLDCO/options?include_expired=true").get_json()
    assert len(body["options"]) == 1


def test_tickers_omits_fully_expired_symbols(client):
    assert client.get("/api/tickers").get_json()["tickers"] == ["AAPL"]
    assert client.get("/api/tickers?include_expired=true").get_json()["tickers"] == ["AAPL", "OLDCO"]


def test_ticker_lookup_is_case_insensitive(client):
    assert len(client.get("/api/stocks/aapl/options").get_json()["options"]) == 2


def test_unknown_ticker_returns_empty_list(client):
    assert client.get("/api/stocks/NOSUCH/options").get_json() == {"options": []}


def test_option_type_read_by_position_not_substring():
    """"C0" as a substring misreads any ticker that itself contains "C0"."""
    assert api_server._option_type_from_contract("AAPL260213P00052000") == "put"
    assert api_server._option_type_from_contract("AAPL260213C00052000") == "call"
    assert api_server._option_type_from_contract("XC0260213P00052000") == "put"


def test_confidence_mapping_is_clamped():
    assert api_server._score_to_confidence(0) == 50
    assert api_server._score_to_confidence(100) == 100
    assert api_server._score_to_confidence(-100) == 0
    assert api_server._score_to_confidence(1e9) == 100
    assert api_server._score_to_confidence("nonsense") == 50


def test_unparseable_expiration_is_kept_not_silently_dropped():
    assert api_server._is_expired({"expiration": "garbage"}, NOW) is False
    assert api_server._is_expired({"expiration": ""}, NOW) is False
    assert api_server._is_expired({"expiration": PAST}, NOW) is True


def test_naive_expiration_is_treated_as_utc():
    assert api_server._parse_expiration("2026-01-01").tzinfo is not None


def test_cors_defaults_to_local_dev_origins(client):
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    blocked = client.get("/api/health", headers={"Origin": "https://example.com"})
    assert allowed.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert blocked.headers.get("Access-Control-Allow-Origin") is None
