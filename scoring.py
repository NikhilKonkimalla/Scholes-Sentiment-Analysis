"""
Opportunity scoring: blend BS mispricing and news sentiment.
"""
import logging


import numpy as np
import pandas as pd

from bs import bs_price

logger = logging.getLogger(__name__)


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

    sentiment_weight: 0-1. When 1.0 (default), alignment is sentiment-only: bearish
    -> favor puts (Buy), avoid calls (Avoid). When <1, mispricing can soften that.
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

    # alignment: sentiment only (default). Bearish -> favor puts (+1), disfavor calls (-1)
    call_put_sign = np.where(df["option_type"] == "call", 1, -1)
    sentiment_sign = np.sign(sentiment_mean) if sentiment_mean != 0 else 0
    df["alignment"] = sentiment_sign * call_put_sign

    # opportunity_score_raw
    abs_gap_pct = np.abs(df["pricing_gap_pct"])
    liq_factor = 1 + 0.25 * df["liquidity_score"]
    spread_factor = np.exp(-df["spread_penalty"])
    df["opportunity_score_raw"] = (
        df["alignment"].astype(float) * abs_gap_pct * liq_factor * spread_factor
    )

    # Normalize to [-100, 100]: tanh scaling
    raw = df["opportunity_score_raw"].values
    if np.any(np.isfinite(raw)) and np.nanmax(np.abs(raw)) > 0:
        scale = np.nanmax(np.abs(raw)) * 1.5
        scale = max(scale, 1e-6)
        df["opportunity_score"] = np.clip(
            np.tanh(raw / scale) * 100, -100, 100
        )
    else:
        df["opportunity_score"] = 0.0

    # risk_flag: spread_penalty > 1.0 OR (volume + openInterest) < 10
    vol_oi = vol.astype(float) + oi.astype(float)
    df["risk_flag"] = (df["spread_penalty"] > 1.0) | (vol_oi < 10)

    return df
