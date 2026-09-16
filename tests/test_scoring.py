"""Regression tests for scoring.py."""
import numpy as np
import pandas as pd
import pytest

from scoring import MAX_ABS_GAP_PCT, MIN_THEO_PRICE, SCORE_SCALE, compute_scores

SPOT = 100.0
R = 0.045


def _chain(**overrides) -> pd.DataFrame:
    """A minimal two-row (call, put) options frame."""
    base = {
        "strike": [100.0, 100.0],
        "time_to_expiry_years": [0.25, 0.25],
        "impliedVolatility": [0.2, 0.2],
        "option_type": ["call", "put"],
        "mid_price": [5.0, 4.0],
        "bid": [4.9, 3.9],
        "ask": [5.1, 4.1],
        "volume": [100, 100],
        "openInterest": [500, 500],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_empty_frame_returns_empty():
    assert compute_scores(pd.DataFrame(), SPOT, R, 0.0).empty


def test_sentiment_weight_actually_changes_the_score():
    """It used to be accepted, documented, and then never read."""
    sentiment_only = compute_scores(_chain(), SPOT, R, -0.5, sentiment_weight=1.0)
    mispricing_only = compute_scores(_chain(), SPOT, R, -0.5, sentiment_weight=0.0)
    assert (
        sentiment_only["opportunity_score"].round(6).tolist()
        != mispricing_only["opportunity_score"].round(6).tolist()
    )


def test_bearish_sentiment_favors_puts_at_full_weight():
    r = compute_scores(_chain(), SPOT, R, -0.5, sentiment_weight=1.0)
    alignment = dict(zip(r["option_type"], r["alignment"], strict=True))
    assert alignment["put"] > 0
    assert alignment["call"] < 0


def test_score_scale_is_absolute_not_batch_relative():
    """
    A batch-relative scale pinned the top option of every batch to tanh(1/1.5)*100
    = 58.2783, making scores incomparable across tickers.
    """
    small = compute_scores(_chain(mid_price=[5.01, 4.0]), SPOT, R, 0.3)
    large = compute_scores(_chain(mid_price=[7.5, 4.0]), SPOT, R, 0.3)
    small_max = float(small["opportunity_score"].abs().max())
    large_max = float(large["opportunity_score"].abs().max())

    assert small_max != pytest.approx(58.2783, abs=1e-3)
    assert large_max != pytest.approx(58.2783, abs=1e-3)
    assert large_max > small_max


def test_negligible_theo_price_is_excluded_not_ranked_top():
    """
    Deep-OTM near-expiry contracts price at ~1e-8, so gap/max(theo, 0.01) explodes to
    tens of thousands of percent and used to dominate every ranking.
    """
    df = _chain(
        strike=[100.0, 758.0],
        time_to_expiry_years=[0.25, 0.0003],
        option_type=["call", "call"],
        mid_price=[5.0, 3.16],
        bid=[4.9, 3.1],
        ask=[5.1, 3.2],
        impliedVolatility=[0.2, 0.10],
    )
    r = compute_scores(df, SPOT, R, 0.3)

    assert r["theo_price"].iloc[1] < MIN_THEO_PRICE
    assert bool(r["unscoreable"].iloc[1])
    assert float(r["opportunity_score"].iloc[1]) == 0.0
    assert bool(r["risk_flag"].iloc[1])
    # The legitimate contract still scores.
    assert float(r["opportunity_score"].iloc[0]) != 0.0


def test_gap_percentage_is_clipped_for_scoring_but_reported_raw():
    r = compute_scores(_chain(mid_price=[30.0, 4.0]), SPOT, R, 0.3)
    assert float(r["pricing_gap_pct"].iloc[0]) > MAX_ABS_GAP_PCT  # raw value preserved
    assert abs(float(r["opportunity_score"].iloc[0])) <= 100.0


def test_scores_stay_within_bounds_and_are_finite():
    r = compute_scores(_chain(), SPOT, R, 0.4)
    scores = r["opportunity_score"].to_numpy(dtype=float)
    assert np.all(np.isfinite(scores))
    assert np.all(np.abs(scores) <= 100.0)


def test_constants_are_sane():
    assert SCORE_SCALE > 0
    assert MIN_THEO_PRICE > 0
    assert MAX_ABS_GAP_PCT > 0
