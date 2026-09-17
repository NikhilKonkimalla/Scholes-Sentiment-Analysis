"""
FinBERT path tests.

Skipped entirely unless transformers + torch are installed (they live in the optional
requirements-ml.txt), so the suite still runs on a core-only install. The first run
downloads ~420 MB of model weights.
"""
import pytest

transformers = pytest.importorskip("transformers", reason="requirements-ml.txt not installed")
pytest.importorskip("torch", reason="requirements-ml.txt not installed")

from news_sentiment import _get_finbert, score_headlines  # noqa: E402


@pytest.fixture(scope="module")
def finbert():
    pipe = _get_finbert()
    if pipe is None:
        pytest.skip("FinBERT weights unavailable (offline?)")
    return pipe


def test_pipeline_returns_the_shape_score_finbert_expects(finbert):
    """
    _score_finbert reads res["label"] / res["score"]. transformers 5 kept this shape,
    but it is the contract the whole FinBERT path depends on, so pin it down.
    """
    out = finbert(["Profits surge as the company beats earnings expectations"], truncation=True)
    assert isinstance(out, list) and out
    assert set(out[0]) >= {"label", "score"}
    assert out[0]["label"].lower() in {"positive", "negative", "neutral"}
    assert 0.0 <= out[0]["score"] <= 1.0


def test_label_mapping_is_not_inverted(finbert):
    """A clearly positive headline must not come back negative, and vice versa."""
    pos = score_headlines(
        [{"title": "Profits surge as the company beats earnings expectations"}],
        model_preference="auto",
    )
    neg = score_headlines(
        [{"title": "Shares collapse after the company issues a severe profit warning"}],
        model_preference="auto",
    )
    assert pos["model"] == "finbert"
    assert neg["model"] == "finbert"
    assert pos["sentiment_mean"] > 0.5, f"positive headline scored {pos['sentiment_mean']}"
    assert neg["sentiment_mean"] < -0.5, f"negative headline scored {neg['sentiment_mean']}"


def test_auto_prefers_finbert_when_available():
    result = score_headlines(
        [{"title": "Revenue grew sharply this quarter"}], model_preference="auto"
    )
    assert result["model"] == "finbert"


def test_explicit_vader_still_bypasses_finbert():
    result = score_headlines(
        [{"title": "Revenue grew sharply this quarter"}], model_preference="vader"
    )
    assert result["model"] == "vader"


def test_neutral_headlines_score_zero(finbert):
    result = score_headlines(
        [{"title": "The board of directors will meet on Tuesday"}], model_preference="auto"
    )
    # FinBERT's third class maps to exactly 0.0 in _score_finbert.
    assert result["sentiment_mean"] == 0.0


def test_scores_stay_in_range(finbert):
    result = score_headlines(
        [
            {"title": "Profits surge as the company beats earnings expectations"},
            {"title": "Shares collapse after a severe profit warning"},
            {"title": "The board of directors will meet on Tuesday"},
        ],
        model_preference="auto",
    )
    assert result["sentiment_count"] == 3
    for h in result["headline_scores"]:
        assert -1.0 <= h["score"] <= 1.0
