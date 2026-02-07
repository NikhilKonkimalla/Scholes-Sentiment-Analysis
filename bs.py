"""
Black-Scholes option pricing.
"""
import math
from typing import Literal

import numpy as np
from scipy.stats import norm

OptionType = Literal["call", "put"]


def bs_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType,
) -> float:
    """
    Black-Scholes option price.
    S: spot, K: strike, T: time to expiry (years), r: risk-free rate, sigma: volatility.
    Returns NaN for invalid inputs (T<=0, sigma<=0, S<=0, K<=0).
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return float("nan")
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    if option_type == "call":
        return float(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))
    else:
        return float(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))


def _self_test() -> None:
    """Assert known approximate Black-Scholes values."""
    # Example: S=100, K=100, T=1, r=0.05, sigma=0.2 -> call ~10.45, put ~1.12
    c = bs_price(100.0, 100.0, 1.0, 0.05, 0.2, "call")
    p = bs_price(100.0, 100.0, 1.0, 0.05, 0.2, "put")
    assert 10.0 <= c <= 11.0, f"call price {c} out of expected range"
    assert 1.0 <= p <= 1.5, f"put price {p} out of expected range"
    # Edge cases return NaN
    assert math.isnan(bs_price(100, 100, 0, 0.05, 0.2, "call"))
    assert math.isnan(bs_price(100, 100, 1, 0.05, 0, "call"))
    assert math.isnan(bs_price(0, 100, 1, 0.05, 0.2, "call"))


if __name__ == "__main__":
    _self_test()
    print("BS self-test passed.")
