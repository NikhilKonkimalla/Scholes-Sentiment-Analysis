"""
Tests for /api/options/top, which backs the home page.

The home page previously rendered a hardcoded table of invented positions; this
endpoint replaces it with the real scored dataset.
"""
import csv
import json
from datetime import datetime, timedelta, timezone

import pytest

import api_server

NOW = datetime.now(timezone.utc)
FUTURE = (NOW + timedelta(days=30)).isoformat()
PAST = (NOW - timedelta(days=30)).isoformat()

HEADER = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid",
          "midPrice", "score", "impliedVolatility"]
ROWS = [
    ["AAPL", FUTURE, "AAPL261016C00250000", "250.0", "5.0", "4.9", "5.0", "12.0", "0.25"],
    ["MSFT", FUTURE, "MSFT261016P00400000", "400.0", "3.0", "2.9", "3.0", "-91.0", "0.22"],
    ["NVDA", FUTURE, "NVDA261016C00900000", "900.0", "7.0", "6.9", "7.0", "45.0", "0.40"],
    ["OLDCO", PAST, "OLDCO260101C00100000", "100.0", "1.0", "0.9", "1.0", "99.0", "0.30"],
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


def test_ranks_by_absolute_score_across_tickers(client):
    opts = client.get("/api/options/top").get_json()["options"]
    assert [o["ticker"] for o in opts] == ["MSFT", "NVDA", "AAPL"]
    # A large negative score outranks a small positive one.
    assert opts[0]["score"] == -91.0


def test_excludes_expired_by_default(client):
    opts = client.get("/api/options/top").get_json()["options"]
    assert "OLDCO" not in {o["ticker"] for o in opts}
    # ...even though its score is the highest in the file.
    with_expired = client.get("/api/options/top?include_expired=true").get_json()["options"]
    assert with_expired[0]["ticker"] == "OLDCO"


def test_limit_is_respected_and_clamped(client):
    assert len(client.get("/api/options/top?limit=2").get_json()["options"]) == 2
    assert len(client.get("/api/options/top?limit=0").get_json()["options"]) == 1
    body = client.get("/api/options/top?limit=99999").get_json()
    assert len(body["options"]) == 3
    assert client.get("/api/options/top?limit=abc").get_json()["total"] == 3


def test_type_filter(client):
    calls = client.get("/api/options/top?type=call").get_json()["options"]
    puts = client.get("/api/options/top?type=put").get_json()["options"]
    assert {o["type"] for o in calls} == {"call"}
    assert {o["type"] for o in puts} == {"put"}
    assert len(calls) + len(puts) == 3


def test_bogus_type_is_ignored_not_an_error(client):
    assert len(client.get("/api/options/top?type=banana").get_json()["options"]) == 3


def test_total_reflects_all_matches_not_just_the_page(client):
    body = client.get("/api/options/top?limit=1").get_json()
    assert len(body["options"]) == 1
    assert body["total"] == 3


def test_options_carry_the_fields_the_home_table_renders(client):
    opt = client.get("/api/options/top").get_json()["options"][0]
    for field in ("ticker", "type", "expiration", "strike", "midPrice", "score", "confidence"):
        assert field in opt, f"home table needs {field}"


def test_reports_data_as_of(client):
    assert "dataAsOf" in client.get("/api/options/top").get_json()


def test_health_reports_data_as_of(client):
    assert "dataAsOf" in client.get("/api/health").get_json()


def test_data_as_of_prefers_sidecar_over_mtime(tmp_path, monkeypatch):
    """File mtimes are reset by a deploy checkout, so the sidecar wins."""
    csv_path = tmp_path / "options.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(ROWS[:1])
    (tmp_path / "data_meta.json").write_text(
        json.dumps({"generatedAt": "2020-01-02T03:04:05+00:00"}), encoding="utf-8"
    )
    monkeypatch.setattr(api_server, "CSV_PATH", str(csv_path))
    assert api_server._data_as_of() == "2020-01-02T03:04:05+00:00"


def test_data_as_of_falls_back_to_mtime(tmp_path, monkeypatch):
    csv_path = tmp_path / "options.csv"
    csv_path.write_text("ticker\n", encoding="utf-8")
    monkeypatch.setattr(api_server, "CSV_PATH", str(csv_path))
    value = api_server._data_as_of()
    assert value is not None
    assert datetime.fromisoformat(value).year >= 2020


def test_data_as_of_survives_a_corrupt_sidecar(tmp_path, monkeypatch):
    csv_path = tmp_path / "options.csv"
    csv_path.write_text("ticker\n", encoding="utf-8")
    (tmp_path / "data_meta.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(api_server, "CSV_PATH", str(csv_path))
    assert api_server._data_as_of() is not None
