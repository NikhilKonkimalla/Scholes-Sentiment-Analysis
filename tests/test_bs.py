"""Tests for the Black-Scholes pricer."""
import math

import pytest

from bs import bs_price


def test_known_call_and_put_values():
    # S=100, K=100, T=1, r=0.05, sigma=0.2 -> call ~10.45, put ~5.57
    assert bs_price(100.0, 100.0, 1.0, 0.05, 0.2, "call") == pytest.approx(10.45, abs=0.01)
    assert bs_price(100.0, 100.0, 1.0, 0.05, 0.2, "put") == pytest.approx(5.57, abs=0.01)


def test_put_call_parity():
    S, K, T, r, sigma = 100.0, 95.0, 0.5, 0.045, 0.25
    call = bs_price(S, K, T, r, sigma, "call")
    put = bs_price(S, K, T, r, sigma, "put")
    assert call - put == pytest.approx(S - K * math.exp(-r * T), abs=1e-6)


@pytest.mark.parametrize(
    "S,K,T,sigma",
    [(100, 100, 0, 0.2), (100, 100, 1, 0), (0, 100, 1, 0.2), (100, 0, 1, 0.2)],
)
def test_invalid_inputs_return_nan(S, K, T, sigma):
    assert math.isnan(bs_price(S, K, T, 0.05, sigma, "call"))


def test_deep_out_of_the_money_call_is_near_zero():
    assert bs_price(100.0, 500.0, 0.003, 0.045, 0.1, "call") < 0.01
