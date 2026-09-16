"""
Opportunity scoring: blend BS mispricing and news sentiment.
"""
import logging


import numpy as np
import pandas as pd

from bs import bs_price

logger = logging.getLogger(__name__)

# Fixed tanh scale for opportunity_score. Deliberately a constant rather than the
# batch maximum: a batch-relative scale forces the best option in every batch to the
# same value (tanh(1/1.5)*100 = 58.28), which makes scores incomparable across
# tickers and runs. With this scale raw ~0.1 -> ~10 and raw ~0.8 -> ~66.
SCORE_SCALE = 1.0

# Options whose Black-Scholes value rounds to ~0 (deep OTM, effectively expired) make
# pricing_gap_pct explode: gap / max(theo, 0.01) with theo ~1e-8 yields 30,000%+.
# A percentage measured against a near-zero base is a division artifact, not a signal,
# so these rows are excluded from scoring instead of dominating every ranking.
MIN_THEO_PRICE = 0.05

# Ceiling on the percentage gap that may feed the score, so a single extreme row
# cannot saturate the output.
MAX_ABS_GAP_PCT = 2.0


def compute_scores(
    options_df: pd.DataFrame,
    spot: float,
    r: float,
    sentiment_mean: float,
    sentiment_weight: float = 1.0,
) -> pd.DataFrame:
    """
    Add theo_price, pricing_gap, pricing_gap_pct, liquidity_score, spread_penalty,
    alignment, opportunity_score_raw, opportunity_score, risk_flag to options_df.
    Returns a new DataFrame with these columns added.

    sentiment_weight: 0-1. At 1.0 (default) alignment is sentiment-only: bearish
    -> favor puts (Buy), avoid calls (Avoid). At 0.0 it is mispricing-only:
    underpriced (mid below theoretical) -> Buy, overpriced -> Avoid. Values in
    between blend the two.
    """
    if options_df is None or options_df.empty:
        return pd.DataFrame()

    df = options_df.copy()

    # Validate sigma: use impliedVolatility only when 0 < sigma < 5
    sigma = df["impliedVolatility"].fillna(0)
    sigma = np.where((sigma > 0) & (sigma < 5), sigma, float("nan"))

    # Theo price via BS
    theo = np.full(len(df), float("nan"))
    for i in range(len(df)):
        S = spot
        K = df["strike"].iloc[i]
        T = df["time_to_expiry_years"].iloc[i]
        sig = sigma.iloc[i] if hasattr(sigma, "iloc") else sigma[i]
        opt_type = "call" if df["option_type"].iloc[i] == "call" else "put"
        theo[i] = bs_price(S, K, T, r, sig, opt_type)
    df["theo_price"] = theo

    mid = df["mid_price"].fillna(0)
    df["pricing_gap"] = mid - df["theo_price"]
    df["pricing_gap_pct"] = df["pricing_gap"] / np.maximum(df["theo_price"], 0.01)

    # Guard the gap that feeds the score (pricing_gap_pct itself is left raw for
    # inspection). Rows with a negligible theoretical price are unscoreable; the rest
    # are clipped so one extreme contract cannot dominate.
    scoreable = df["theo_price"].fillna(0) >= MIN_THEO_PRICE
    df["unscoreable"] = ~scoreable
    scored_gap_pct = (
        df["pricing_gap_pct"].where(scoreable, 0.0).clip(-MAX_ABS_GAP_PCT, MAX_ABS_GAP_PCT)
    )

    vol = df["volume"].fillna(0)
    oi = df["openInterest"].fillna(0)
    df["liquidity_score"] = np.log1p(vol.astype(float) + oi.astype(float))

    bid = df["bid"].fillna(0)
    ask = df["ask"].fillna(0)
    spread = np.where((bid > 0) & (ask > 0), ask - bid, float("nan"))
    df["spread_penalty"] = np.clip(
        spread / np.maximum(mid.astype(float), 0.01), 0, 5
    )
    df["spread_penalty"] = df["spread_penalty"].fillna(5)  # treat NaN spread as max penalty

    # alignment: blend of sentiment direction and mispricing direction.
    #   sentiment side : bearish -> favor puts (+1), disfavor calls (-1)
    #   mispricing side: underpriced (gap < 0) -> Buy (+1), overpriced -> Avoid (-1)
    w = float(np.clip(sentiment_weight, 0.0, 1.0))
    call_put_sign = np.where(df["option_type"] == "call", 1, -1)
    sentiment_sign = np.sign(sentiment_mean) if sentiment_mean != 0 else 0.0
    sentiment_alignment = sentiment_sign * call_put_sign
    mispricing_alignment = -np.sign(
        np.nan_to_num(df["pricing_gap"].values.astype(float), nan=0.0)
    )
    df["alignment"] = w * sentiment_alignment + (1.0 - w) * mispricing_alignment

    # opportunity_score_raw
    abs_gap_pct = np.abs(scored_gap_pct)
    liq_factor = 1 + 0.25 * df["liquidity_score"]
    spread_factor = np.exp(-df["spread_penalty"])
    df["opportunity_score_raw"] = (
        df["alignment"].astype(float) * abs_gap_pct * liq_factor * spread_factor
    )

    # Normalize to [-100, 100] on a fixed (absolute) scale, so a given score means
    # the same thing in every batch and for every ticker.
    raw = np.nan_to_num(
        df["opportunity_score_raw"].values.astype(float),
        nan=0.0, posinf=0.0, neginf=0.0,
    )
    df["opportunity_score"] = np.clip(np.tanh(raw / SCORE_SCALE) * 100, -100, 100)

    # risk_flag: wide spread, illiquid, or no usable theoretical price
    vol_oi = vol.astype(float) + oi.astype(float)
    df["risk_flag"] = (
        (df["spread_penalty"] > 1.0) | (vol_oi < 10) | df["unscoreable"]
    )

    return df
