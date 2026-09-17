"""
Tests for market_data's price readers (offline: yfinance is stubbed).

yfinance can end a history frame with a row for the current session whose prices are all
NaN. Reading "the last row" then returned NaN, which blanked every quote on the hosted
site and made the pipeline skip every ticker as having no spot price.
"""
import math

import pandas as pd
import pytest

import market_data

NAN = float("nan")


def _frame(closes):
    idx = pd.date_range("2026-09-10", periods=len(closes), freq="D", tz="America/New_York")
    return pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes, "Volume": [1] * len(closes)},
        index=idx,
    )


@pytest.fixture
def stub_history(monkeypatch):
    """Make yf.Ticker(...).history(...) return a chosen frame."""
    def install(frame):
        class FakeTicker:
            def __init__(self, _symbol):
                pass

            def history(self, period="1mo"):
                return frame

        monkeypatch.setattr(market_data.yf, "Ticker", FakeTicker)
    return install


def test_quote_ignores_trailing_empty_session_row(stub_history):
    stub_history(_frame([100.0, 110.0, NAN]))
    q = market_data.get_quote("AAPL")
    assert q == {"currentPrice": 110.0, "dayChangePercent": 10.0}


def test_spot_ignores_trailing_empty_session_row(stub_history):
    stub_history(_frame([100.0, 110.0, NAN]))
    assert market_data.get_spot("AAPL") == 110.0


def test_history_drops_rows_with_no_close(stub_history):
    stub_history(_frame([100.0, NAN, 110.0, NAN]))
    h = market_data.get_history("AAPL")
    assert len(h) == 2
    assert not h["close"].isna().any()


def test_quote_with_a_single_valid_close(stub_history):
    stub_history(_frame([NAN, 105.0, NAN]))
    assert market_data.get_quote("AAPL") == {"currentPrice": 105.0, "dayChangePercent": 0.0}


def test_quote_is_none_when_nothing_is_valid(stub_history):
    stub_history(_frame([NAN, NAN]))
    assert market_data.get_quote("AAPL") is None


def test_spot_is_nan_when_nothing_is_valid(stub_history):
    stub_history(_frame([NAN, NAN]))
    assert math.isnan(market_data.get_spot("AAPL"))


def test_empty_history_is_handled(stub_history):
    stub_history(pd.DataFrame())
    assert market_data.get_quote("AAPL") is None
    assert math.isnan(market_data.get_spot("AAPL"))
    assert market_data.get_history("AAPL").empty


def test_quote_route_reports_unavailable_rather_than_null_price(stub_history):
    """The API (and so the static export) must not publish a quote with a null price."""
    import api_server

    stub_history(_frame([NAN, NAN]))
    resp = api_server.app.test_client().get("/api/stocks/AAPL/quote")
    assert resp.status_code == 404
