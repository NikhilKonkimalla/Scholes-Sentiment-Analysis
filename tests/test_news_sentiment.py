"""Regression tests for news_sentiment.py (offline: no network calls)."""
import pytest

from news_sentiment import _get_vader, _normalize_yahoo_item, score_headlines


def test_parses_current_nested_yahoo_schema():
    """
    yfinance moved the real fields under "content". Reading top-level "title" gave
    empty strings for every headline, which silently zeroed out all sentiment.
    """
    item = {
        "id": "abc",
        "content": {
            "title": "Apple beats on earnings",
            "provider": {"displayName": "The Wall Street Journal"},
            "canonicalUrl": {"url": "https://wsj.com/x"},
            "pubDate": "2026-09-16T02:00:00Z",
        },
    }
    out = _normalize_yahoo_item(item)
    assert out["title"] == "Apple beats on earnings"
    assert out["source"] == "The Wall Street Journal"
    assert out["url"] == "https://wsj.com/x"
    assert out["publishedAt"].startswith("2026-09-16")


def test_still_parses_legacy_flat_schema():
    item = {
        "title": "Older format headline",
        "link": "https://example.com/a",
        "provider": {"name": "Reuters"},
        "providerPublishTime": 1700000000,
    }
    out = _normalize_yahoo_item(item)
    assert out["title"] == "Older format headline"
    assert out["source"] == "Reuters"
    assert out["url"] == "https://example.com/a"
    assert out["publishedAt"].startswith("2023-")


def test_falls_back_through_url_keys_when_canonical_is_null():
    item = {"content": {"title": "t", "canonicalUrl": None, "clickThroughUrl": None,
                        "previewUrl": "https://finance.yahoo.com/m/x"}}
    assert _normalize_yahoo_item(item)["url"] == "https://finance.yahoo.com/m/x"


def test_all_titleless_headlines_warn_instead_of_reporting_neutral():
    """The old behaviour reported count=N, mean=0.0 and no warning at all."""
    result = score_headlines([{"title": ""}, {"title": "   "}], model_preference="vader")
    assert result["sentiment_count"] == 0
    assert "warning" in result
    assert "empty titles" in result["warning"]


def test_no_headlines_warns():
    result = score_headlines([], model_preference="vader")
    assert "warning" in result


@pytest.mark.skipif(_get_vader() is None, reason="VADER lexicon unavailable")
def test_titleless_headlines_are_dropped_from_the_average():
    result = score_headlines(
        [{"title": ""}, {"title": "Stocks rally on strong earnings beat"}],
        model_preference="vader",
    )
    assert result["sentiment_count"] == 1
    assert result["sentiment_mean"] != 0.0
