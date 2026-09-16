"""
Tests for the /api/stocks/<ticker>/ai-summary endpoint.

Offline: news fetching and scoring are stubbed, so no network or model is needed.
"""
import pytest

import api_server
import news_sentiment


@pytest.fixture
def client(monkeypatch):
    api_server._ai_summary_cache.clear()
    return api_server.app.test_client()


def _headlines(n=3):
    return [{"title": f"Headline {i}", "source": "Reuters", "publishedAt": "", "url": f"https://e.com/{i}"}
            for i in range(n)]


def _scored(mean, scores):
    return {
        "sentiment_mean": mean,
        "sentiment_std": 0.3,
        "sentiment_count": len(scores),
        "model": "vader",
        "headline_scores": [
            {"title": f"Headline {i}", "score": s, "source": "Reuters", "publishedAt": "",
             "url": f"https://e.com/{i}"}
            for i, s in enumerate(scores)
        ],
        "top_positive": [],
        "top_negative": [],
    }


def _stub(monkeypatch, headlines, result):
    monkeypatch.setattr(news_sentiment, "fetch_headlines_yahoo", lambda t, n=25: headlines)
    monkeypatch.setattr(news_sentiment, "score_headlines", lambda h, model_preference="auto": result)


def test_returns_real_sentiment(client, monkeypatch):
    _stub(monkeypatch, _headlines(4), _scored(-0.25, [-0.8, -0.4, 0.5, -0.3]))
    body = client.get("/api/stocks/AAPL/ai-summary").get_json()

    assert body["available"] is True
    assert body["ticker"] == "AAPL"
    assert body["sentimentMean"] == -0.25
    assert body["headlineCount"] == 4
    assert body["positive"] == 1
    assert body["negative"] == 3
    assert body["neutral"] == 0
    assert body["model"] == "vader"
    assert len(body["articles"]) == 4
    assert body["articles"][0]["url"].startswith("https://")


def test_summary_is_descriptive_never_advice(client, monkeypatch):
    """
    The whole point of this endpoint is replacing hand-written trade advice, so the
    generated text must not reintroduce any.
    """
    _stub(monkeypatch, _headlines(3), _scored(-0.5, [-0.8, -0.4, -0.3]))
    summary = client.get("/api/stocks/AAPL/ai-summary").get_json()["summary"].lower()

    assert "negative" in summary
    assert "mean" in summary
    for banned in ("we favor", "recommend", "should buy", "should sell", "hold", "avoid"):
        assert banned not in summary, f"summary reintroduced advice: {banned!r}"


@pytest.mark.parametrize(
    "mean,expected",
    [(0.5, "strongly positive"), (0.2, "positive"), (0.0, "roughly neutral"),
     (-0.2, "negative"), (-0.5, "strongly negative")],
)
def test_sentiment_labels(mean, expected):
    assert expected in api_server._describe_sentiment(mean, 5, 2, 2, 1)


def test_no_headlines_reports_unavailable(client, monkeypatch):
    _stub(monkeypatch, [], {"sentiment_mean": 0.0, "headline_scores": [],
                            "warning": "No headlines provided (missing API key or empty fetch)."})
    body = client.get("/api/stocks/NONEWS/ai-summary").get_json()
    assert body["available"] is False
    assert body["reason"]
    assert body["articles"] == []


def test_titleless_headlines_report_unavailable(client, monkeypatch):
    """The old silent failure mode: empty titles scoring a confident 0.0."""
    _stub(monkeypatch, _headlines(2),
          {"sentiment_mean": 0.0, "headline_scores": [], "warning": "All headlines had empty titles..."})
    assert client.get("/api/stocks/AAPL/ai-summary").get_json()["available"] is False


def test_scoring_failure_degrades_gracefully(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("yahoo exploded")
    monkeypatch.setattr(news_sentiment, "fetch_headlines_yahoo", boom)
    body = client.get("/api/stocks/AAPL/ai-summary").get_json()
    assert body["available"] is False
    assert "failed" in body["reason"].lower()


def test_result_is_cached_so_yahoo_is_not_re_hit(client, monkeypatch):
    calls = []

    def counting_fetch(t, n=25):
        calls.append(t)
        return _headlines(2)

    monkeypatch.setattr(news_sentiment, "fetch_headlines_yahoo", counting_fetch)
    monkeypatch.setattr(news_sentiment, "score_headlines",
                        lambda h, model_preference="auto": _scored(0.1, [0.2, 0.0]))

    client.get("/api/stocks/AAPL/ai-summary")
    client.get("/api/stocks/AAPL/ai-summary")
    client.get("/api/stocks/AAPL/ai-summary")
    assert len(calls) == 1, "sentiment should be cached, not refetched per request"


def test_unavailable_results_are_cached_too(client, monkeypatch):
    calls = []

    def counting_fetch(t, n=25):
        calls.append(t)
        return []

    monkeypatch.setattr(news_sentiment, "fetch_headlines_yahoo", counting_fetch)
    monkeypatch.setattr(news_sentiment, "score_headlines",
                        lambda h, model_preference="auto": {"headline_scores": [], "warning": "none"})
    client.get("/api/stocks/QUIET/ai-summary")
    client.get("/api/stocks/QUIET/ai-summary")
    assert len(calls) == 1, "a ticker with no news should not re-hit Yahoo every view"


def test_cache_is_per_ticker(client, monkeypatch):
    seen = []
    monkeypatch.setattr(news_sentiment, "fetch_headlines_yahoo",
                        lambda t, n=25: (seen.append(t), _headlines(1))[1])
    monkeypatch.setattr(news_sentiment, "score_headlines",
                        lambda h, model_preference="auto": _scored(0.1, [0.1]))
    client.get("/api/stocks/AAPL/ai-summary")
    client.get("/api/stocks/MSFT/ai-summary")
    assert seen == ["AAPL", "MSFT"]


def test_score_headlines_reports_which_model_ran():
    """'auto' silently falls back to VADER; callers need to know which ran."""
    result = news_sentiment.score_headlines(
        [{"title": "Stocks rally on strong earnings beat"}], model_preference="vader"
    )
    assert result.get("model") in {"vader", None}
    empty = news_sentiment.score_headlines([], model_preference="vader")
    assert empty.get("model") is None
