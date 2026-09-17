"""
Tests for the risk/liquidity signal carried alongside the opportunity score.

A contract can score highly on mispricing while being untradeable (no volume, wide
spread). These columns were computed by scoring.py but dropped from the CSV, which
left the API unable to qualify a confidence-100 badge.
"""
import csv
from datetime import datetime, timedelta, timezone

import pytest

import api_server

NOW = datetime.now(timezone.utc)
FUTURE = (NOW + timedelta(days=30)).isoformat()

HEADER = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "ask",
          "midPrice", "score", "impliedVolatility", "volume", "openInterest",
          "theoPrice", "liquidityScore", "spreadPenalty", "riskFlag"]
ROWS = [
    # liquid, not flagged
    ["AAPL", FUTURE, "AAPL261016C00250000", "250.0", "5.0", "4.95", "5.05",
     "5.0", "80.0", "0.25", "1500", "9000", "4.60", "9.35", "0.02", "False"],
    # high score but flagged: no volume, wide spread
    ["PENNY", FUTURE, "PENNY261016C00001000", "1.0", "0.30", "0.10", "0.60",
     "0.35", "99.0", "1.80", "0", "3", "0.05", "1.39", "1.43", "True"],
]

# A CSV written before the risk columns existed.
LEGACY_HEADER = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid",
                 "midPrice", "score", "impliedVolatility"]
LEGACY_ROWS = [
    ["AAPL", FUTURE, "AAPL261016C00250000", "250.0", "5.0", "4.95", "5.0", "80.0", "0.25"],
]


def _client(tmp_path, monkeypatch, header, rows):
    csv_path = tmp_path / "options.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    monkeypatch.setattr(api_server, "CSV_PATH", str(csv_path))
    api_server.load_csv()
    return api_server.app.test_client()


@pytest.fixture
def client(tmp_path, monkeypatch):
    return _client(tmp_path, monkeypatch, HEADER, ROWS)


@pytest.fixture
def legacy_client(tmp_path, monkeypatch):
    return _client(tmp_path, monkeypatch, LEGACY_HEADER, LEGACY_ROWS)


def test_risk_fields_are_exposed(client):
    opts = {o["ticker"]: o for o in client.get("/api/options/top").get_json()["options"]}
    flagged = opts["PENNY"]
    assert flagged["riskFlag"] is True
    assert flagged["volume"] == 0
    assert flagged["openInterest"] == 3
    assert flagged["spreadPenalty"] == pytest.approx(1.43)
    assert flagged["theoPrice"] == pytest.approx(0.05)
    assert flagged["ask"] == pytest.approx(0.60)

    clean = opts["AAPL"]
    assert clean["riskFlag"] is False
    assert clean["volume"] == 1500


def test_flagged_contracts_are_marked_not_hidden(client):
    """A high score must never be shown without its caveat — but not silently dropped."""
    body = client.get("/api/options/top").get_json()
    assert body["options"][0]["ticker"] == "PENNY"
    assert body["options"][0]["riskFlag"] is True
    assert body["riskFlagged"] == 1


def test_exclude_risky_drops_them_on_request(client):
    body = client.get("/api/options/top?exclude_risky=true").get_json()
    assert [o["ticker"] for o in body["options"]] == ["AAPL"]
    assert body["total"] == 1


def test_exclude_risky_on_per_ticker_options(client):
    assert len(client.get("/api/stocks/PENNY/options").get_json()["options"]) == 1
    assert client.get("/api/stocks/PENNY/options?exclude_risky=true").get_json()["options"] == []


def test_missing_risk_columns_read_as_unknown_not_safe(legacy_client):
    """
    A CSV predating these columns must yield null, so the UI omits the badge rather
    than asserting the contract is fine.
    """
    opt = legacy_client.get("/api/options/top").get_json()["options"][0]
    assert opt["riskFlag"] is None
    assert opt["volume"] is None
    assert opt["openInterest"] is None
    assert opt["theoPrice"] is None
    assert opt["spreadPenalty"] is None


def test_unknown_risk_is_not_dropped_by_exclude_risky(legacy_client):
    """exclude_risky drops known-bad contracts, not merely unknown ones."""
    body = legacy_client.get("/api/options/top?exclude_risky=true").get_json()
    assert len(body["options"]) == 1


def test_zero_volume_is_distinct_from_missing(client):
    """0 is a real, meaningful value for volume; it must not read as 'no data'."""
    opts = {o["ticker"]: o for o in client.get("/api/options/top").get_json()["options"]}
    assert opts["PENNY"]["volume"] == 0
    assert opts["PENNY"]["volume"] is not None


def test_nan_cells_become_null_not_invalid_json(tmp_path, monkeypatch):
    """jsonify would emit a bare NaN literal, which is not valid JSON."""
    rows = [list(ROWS[0])]
    rows[0][HEADER.index("theoPrice")] = "nan"
    c = _client(tmp_path, monkeypatch, HEADER, rows)
    raw = c.get("/api/options/top").get_data(as_text=True)
    assert "NaN" not in raw
    assert c.get("/api/options/top").get_json()["options"][0]["theoPrice"] is None


def test_bool_parsing_accepts_common_spellings():
    assert api_server._bool_or_none("True") is True
    assert api_server._bool_or_none("false") is False
    assert api_server._bool_or_none("1") is True
    assert api_server._bool_or_none("0") is False
    assert api_server._bool_or_none("") is None
    assert api_server._bool_or_none("maybe") is None
