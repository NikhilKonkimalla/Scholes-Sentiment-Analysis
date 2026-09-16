"""
Tests for export_static_data.py, which produces the JSON the hosted site reads.

Offline: live=False skips quotes, history and sentiment, so no Yahoo calls are made.
"""
import csv
import json
from datetime import datetime, timedelta, timezone

import pytest

import api_server
import export_static_data as exporter

NOW = datetime.now(timezone.utc)
FUTURE = (NOW + timedelta(days=30)).isoformat()
PAST = (NOW - timedelta(days=30)).isoformat()

HEADER = ["ticker", "expiration", "contractSymbol", "strike", "price", "bid", "ask",
          "midPrice", "score", "impliedVolatility", "volume", "openInterest",
          "theoPrice", "liquidityScore", "spreadPenalty", "riskFlag"]
ROWS = [
    ["AAPL", FUTURE, "AAPL261016C00250000", "250.0", "5.0", "4.9", "5.1", "5.0", "40.0", "0.25",
     "100", "900", "4.8", "6.9", "0.04", "False"],
    ["MSFT", FUTURE, "MSFT261016P00400000", "400.0", "3.0", "2.9", "3.1", "3.0", "-90.0", "0.22",
     "50", "400", "3.3", "6.0", "0.07", "False"],
    ["BF.B", FUTURE, "BF.B261016C00040000", "40.0", "1.0", "0.9", "1.1", "1.0", "10.0", "0.30",
     "5", "20", "0.9", "3.3", "0.2", "False"],
    ["OLDCO", PAST, "OLDCO260101C00100000", "100.0", "1.0", "0.9", "1.1", "1.0", "99.0", "0.30",
     "0", "0", "", "", "", "True"],
    ["bad/../x", FUTURE, "X", "1.0", "1.0", "0.9", "1.1", "1.0", "1.0", "0.1",
     "0", "0", "", "", "", "True"],
]


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "data.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(ROWS)
    return path


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_writes_the_expected_tree(csv_path, tmp_path):
    out = tmp_path / "site" / "data"
    stats = exporter.export(csv_path, out, live=False, frontend_src=None)

    assert (out / "meta.json").is_file()
    assert (out / "tickers.json").is_file()
    assert (out / "top-options.json").is_file()
    assert (out / "options" / "AAPL.json").is_file()
    assert stats["optionFiles"] == 3


def test_expired_contracts_and_tickers_are_left_out(csv_path, tmp_path):
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)

    tickers = _load(out / "tickers.json")["tickers"]
    assert "OLDCO" not in tickers
    assert not (out / "options" / "OLDCO.json").exists()
    top = _load(out / "top-options.json")["options"]
    assert "OLDCO" not in {o["ticker"] for o in top}


def test_top_options_are_ranked_by_absolute_score(csv_path, tmp_path):
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)
    top = _load(out / "top-options.json")["options"]
    assert [o["ticker"] for o in top] == ["MSFT", "AAPL", "BF.B"]


def test_files_match_the_api_responses(csv_path, tmp_path, monkeypatch):
    """Static mode must return exactly what API mode returns."""
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)

    monkeypatch.setattr(api_server, "CSV_PATH", str(csv_path))
    api_server.load_csv()
    client = api_server.app.test_client()
    assert _load(out / "options" / "AAPL.json") == client.get("/api/stocks/AAPL/options").get_json()


def test_symbols_with_dots_are_kept_and_unsafe_names_rejected(csv_path, tmp_path):
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)
    assert (out / "options" / "BF.B.json").is_file()
    written = {p.name for p in (out / "options").iterdir()}
    assert not any("/" in n or ".." in n.replace("BF.B", "") for n in written)
    assert "BAD/../X" not in _load(out / "tickers.json")["tickers"]


def test_meta_carries_snapshot_date_and_export_stats(csv_path, tmp_path):
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)
    meta = _load(out / "meta.json")
    assert meta["status"] == "ok"
    assert meta["dataAsOf"]
    assert meta["exportedAt"]
    assert meta["export"]["optionFiles"] == 3


def test_output_is_strict_json(csv_path, tmp_path):
    """NaN/Infinity are not valid JSON and would break the browser's parser."""
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)
    for path in out.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "NaN" not in text and "Infinity" not in text, path


def test_rerun_replaces_a_previous_export(csv_path, tmp_path):
    out = tmp_path / "data"
    exporter.export(csv_path, out, live=False, frontend_src=None)
    (out / "options" / "STALE.json").write_text("{}", encoding="utf-8")
    exporter.export(csv_path, out, live=False, frontend_src=None)
    assert not (out / "options" / "STALE.json").exists()


def test_refuses_to_wipe_a_directory_that_is_not_an_export(csv_path, tmp_path):
    """A mistyped --out must not delete someone's files."""
    out = tmp_path / "important"
    out.mkdir()
    (out / "notes.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(RuntimeError):
        exporter.export(csv_path, out, live=False, frontend_src=None)
    assert (out / "notes.txt").read_text(encoding="utf-8") == "keep me"


def test_does_not_leak_state_into_api_server(csv_path, tmp_path):
    before = api_server.CSV_PATH
    exporter.export(csv_path, tmp_path / "data", live=False, frontend_src=None)
    assert before == api_server.CSV_PATH


def test_ui_tickers_are_read_from_the_frontend():
    tickers = exporter.ui_tickers(exporter.ROOT / "frontend" / "src")
    # Sector map, extra tickers, and carousel respectively.
    assert tickers >= {"AAPL", "SLB", "SPY"}
