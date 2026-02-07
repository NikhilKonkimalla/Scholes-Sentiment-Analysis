"""
Market data module: spot price and options chain via yfinance.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import logging
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# US/Eastern market close (16:00) for expiration dates
ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def get_spot(ticker: str) -> float:
    """
    Fetch last close price for the underlying using yfinance.
    Returns last close as float; NaN on failure.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if hist is None or hist.empty:
            logger.warning("No history returned for %s", ticker)
            return float("nan")
        close = hist["Close"].iloc[-1]
        return float(close)
    except Exception as e:
        logger.exception("get_spot failed for %s: %s", ticker, e)
        return float("nan")


def _expiration_to_utc(exp: str) -> Optional[datetime]:
    """
    Convert expiration string (YYYY-MM-DD) to UTC datetime at 16:00 US/Eastern,
    or 20:00 UTC if timezone conversion fails.
    """
    try:
        # Parse date only
        dt_et = datetime.strptime(exp, "%Y-%m-%d").replace(
            hour=16, minute=0, second=0, microsecond=0, tzinfo=ET
        )
        return dt_et.astimezone(UTC)
    except Exception:
        try:
            return datetime.strptime(exp, "%Y-%m-%d").replace(
                hour=20, minute=0, second=0, microsecond=0, tzinfo=UTC
            )
        except Exception:
            return None


def get_options_chain(ticker: str, max_expirations: int = 6) -> pd.DataFrame:
    """
    Fetch options chain for ticker for up to max_expirations expirations.
    Returns a DataFrame with standardized columns and computed mid_price, spread, time_to_expiry_years.
    """
    try:
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            logger.warning("No expirations for %s", ticker)
            return pd.DataFrame()
    except Exception as e:
        logger.exception("Failed to get options for %s: %s", ticker, e)
        return pd.DataFrame()

    expirations = expirations[:max_expirations]
    now_utc = datetime.now(UTC)
    SECONDS_PER_YEAR = 365 * 24 * 3600
    rows: list[pd.DataFrame] = []

    for exp in expirations:
        try:
            chain = t.option_chain(exp)
            calls = chain.calls.copy()
            puts = chain.puts.copy()
            calls["option_type"] = "call"
            puts["option_type"] = "put"
            expiration_utc = _expiration_to_utc(exp)
            if expiration_utc is not None:
                T_sec = max((expiration_utc - now_utc).total_seconds(), 0)
                T_years = T_sec / SECONDS_PER_YEAR
            else:
                T_years = float("nan")

            for df in (calls, puts):
                df["expiration"] = expiration_utc
                df["ticker"] = ticker
                df["time_to_expiry_years"] = T_years

            rows.append(calls)
            rows.append(puts)
        except Exception as e:
            logger.warning("option_chain failed for %s exp %s: %s", ticker, exp, e)
            continue

    if not rows:
        return pd.DataFrame()

    out = pd.concat(rows, ignore_index=True)

    # Standardize columns we care about (create if missing)
    want = [
        "ticker", "expiration", "option_type", "contractSymbol", "strike",
        "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility",
    ]
    for col in want:
        if col not in out.columns:
            out[col] = None if col in ("bid", "ask", "volume", "openInterest", "impliedVolatility") else ""

    # Numeric where needed
    for col in ("strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # mid_price and spread
    bid = out["bid"].fillna(0)
    ask = out["ask"].fillna(0)
    last = out["lastPrice"].fillna(0)
    out["mid_price"] = np.where((bid > 0) & (ask > 0), (bid + ask) / 2, last)
    out["spread"] = np.where((bid > 0) & (ask > 0), ask - bid, float("nan"))

    # Keep standardized set
    keep = [
        "ticker", "expiration", "option_type", "contractSymbol", "strike",
        "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility",
        "mid_price", "spread", "time_to_expiry_years",
    ]
    existing = [c for c in keep if c in out.columns]
    return out[existing].copy()
