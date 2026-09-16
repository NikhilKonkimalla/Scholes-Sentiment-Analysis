"""
News headlines fetch (NewsAPI and Yahoo Finance) and sentiment scoring (FinBERT with VADER fallback).
"""
import logging
from datetime import datetime, timezone
from typing import Any

from newsapi_client import fetch_headlines as fetch_headlines_newsapi

logger = logging.getLogger(__name__)

# FinBERT / VADER availability
_finbert_pipeline = None
_vader_analyzer = None


def _get_finbert() -> Any:
    """Lazy-load FinBERT pipeline; return None if unavailable."""
    global _finbert_pipeline
    if _finbert_pipeline is not None:
        return _finbert_pipeline
    try:
        from transformers import pipeline
        # Pin the revision. Left unpinned, transformers resolves weights by probing the
        # Hub and will reach for safetensors published on an unmerged community pull
        # request (refs/pr/29) rather than the maintainer's branch — a PR can be
        # force-pushed or closed, so the weights you get are not reproducible.
        # Trade-off: "main" currently ships pytorch_model.bin (a torch.load pickle)
        # rather than safetensors. Provenance is chosen over container format here;
        # switch the revision to a pinned commit SHA if you want safetensors instead.
        _finbert_pipeline = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            revision="main",
            truncation=True,
            max_length=512,
        )
        return _finbert_pipeline
    except Exception as e:
        logger.warning("FinBERT unavailable, will use VADER: %s", e)
        return None


def _get_vader() -> Any:
    """Lazy-load VADER; return None if unavailable."""
    global _vader_analyzer
    if _vader_analyzer is not None:
        return _vader_analyzer
    try:
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        _vader_analyzer = SentimentIntensityAnalyzer()
        return _vader_analyzer
    except Exception as e:
        logger.warning("VADER unavailable: %s", e)
        return None


def _yahoo_url(content: dict) -> str:
    """Pick the best available link from a Yahoo news item (keys vary; some are null)."""
    for key in ("canonicalUrl", "clickThroughUrl"):
        val = content.get(key)
        if isinstance(val, dict) and val.get("url"):
            return str(val["url"])
        if isinstance(val, str) and val:
            return val
    return str(content.get("previewUrl") or content.get("link") or content.get("url") or "")


def _normalize_yahoo_item(a: dict) -> dict:
    """
    Normalize one yfinance news item to {"title", "source", "publishedAt", "url"}.

    Current yfinance returns {"id", "content": {...}} with the real fields nested
    under "content"; older versions returned a flat dict. Read from "content" when
    present and fall back to the flat keys, so both shapes work.
    """
    content = a.get("content") if isinstance(a.get("content"), dict) else a

    title = content.get("title") or content.get("headline") or ""

    source = content.get("provider") or content.get("source")
    if isinstance(source, dict):
        source = source.get("displayName") or source.get("name") or ""
    source = source or ""

    pub = (
        content.get("pubDate")
        or content.get("displayTime")
        or content.get("providerPublishTime")
        or content.get("publishTime")
        or content.get("publishedAt")
        or content.get("published")
    )
    if pub is not None and hasattr(pub, "isoformat"):
        published_at = pub.isoformat()
    elif isinstance(pub, (int, float)):
        try:
            published_at = datetime.fromtimestamp(int(pub), tz=timezone.utc).isoformat()
        except (OSError, ValueError):
            published_at = str(pub)
    else:
        published_at = str(pub) if pub is not None else ""

    return {
        "title": str(title).strip(),
        "source": str(source).strip(),
        "publishedAt": published_at,
        "url": _yahoo_url(content),
    }


def fetch_headlines_yahoo(ticker: str, n: int = 20) -> list[dict]:
    """
    Fetch recent headlines for a ticker from Yahoo Finance (yfinance).
    Returns list of dicts: {"title", "source", "publishedAt", "url"}.
    Items with no title are dropped rather than returned as blanks, which would
    silently drag sentiment toward 0. No API key required.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        raw = t.get_news(count=min(n, 50), tab="news")
        if not raw:
            return []
        out = []
        skipped = 0
        for a in raw:
            if not isinstance(a, dict):
                continue
            item = _normalize_yahoo_item(a)
            if not item["title"]:
                skipped += 1
                continue
            out.append(item)
        if skipped:
            logger.warning("%s: dropped %d Yahoo news item(s) with no title", ticker, skipped)
        return out[:n]
    except Exception as e:
        logger.exception("fetch_headlines_yahoo failed for %s: %s", ticker, e)
        return []


def fetch_headlines(
    source: str,
    *,
    query: str = "",
    api_key: str = "",
    ticker: str = "",
    n: int = 20,
    use_cache: bool = True,
    cache_max_age_hours: float = 24.0,
) -> list[dict]:
    """
    Fetch headlines from the chosen source. Same return shape: {"title", "source", "publishedAt", "url"}.

    - source "newsapi": uses query and api_key (NewsAPI). Caches to CSV and uses cache first to save API credits.
    - source "yahoo": uses ticker (Yahoo Finance via yfinance). query and api_key ignored.
    """
    if source == "yahoo":
        ticker_to_use = (ticker or "").strip().upper() or "SPY"
        return fetch_headlines_yahoo(ticker_to_use, n=n)
    return fetch_headlines_newsapi(
        query or "SPY OR S&P 500",
        api_key,
        n=n,
        use_cache=use_cache,
        cache_max_age_hours=cache_max_age_hours,
    )


def _score_finbert(headlines: list[dict], batch_size: int = 32) -> list[float]:
    """Score each headline with FinBERT; return list of scores in [-1, 1]. Batched for speed."""
    pipe = _get_finbert()
    if pipe is None:
        return []
    titles = [(h.get("title") or "").strip()[:512] for h in headlines]
    scores = [0.0] * len(headlines)
    # Process in batches for ~10x speedup
    for i in range(0, len(titles), batch_size):
        batch = titles[i : i + batch_size]
        valid_idx = [j for j, t in enumerate(batch) if t]
        if not valid_idx:
            continue
        valid_titles = [batch[j] for j in valid_idx]
        try:
            results = pipe(valid_titles, batch_size=min(batch_size, len(valid_titles)), truncation=True)
            if not isinstance(results, list):
                results = [results]
            for k, res in enumerate(results):
                if k >= len(valid_idx):
                    break
                head_idx = i + valid_idx[k]
                label = (res.get("label") or "").lower()
                conf = float(res.get("score", 0.5))
                if label == "positive":
                    scores[head_idx] = conf
                elif label == "negative":
                    scores[head_idx] = -conf
        except Exception:
            pass
    return scores


def _score_vader(headlines: list[dict]) -> list[float]:
    """Score each headline with VADER compound; return list in [-1, 1] (compound is already -1..1)."""
    analyzer = _get_vader()
    if analyzer is None:
        return []
    scores = []
    for h in headlines:
        title = (h.get("title") or "").strip()
        if not title:
            scores.append(0.0)
            continue
        try:
            compound = analyzer.polarity_scores(title).get("compound", 0.0)
            scores.append(float(compound))
        except Exception:
            scores.append(0.0)
    return scores


def score_headlines(
    headlines: list[dict],
    model_preference: str = "auto",
) -> dict:
    """
    Compute sentiment per headline. Try FinBERT first unless model_preference=="vader".
    Returns dict with sentiment_mean, sentiment_std, sentiment_count, headline_scores,
    top_positive, top_negative; optional "warning" if no API key / no headlines.
    """
    result = {
        "sentiment_mean": 0.0,
        "sentiment_std": 0.0,
        "sentiment_count": 0,
        "headline_scores": [],
        "top_positive": [],
        "top_negative": [],
    }
    if not headlines:
        result["warning"] = "No headlines provided (missing API key or empty fetch)."
        return result

    # Titleless headlines all score 0.0 and would quietly pull sentiment to neutral,
    # which zeroes out every opportunity score downstream. Drop them and say so.
    usable = [h for h in headlines if (h.get("title") or "").strip()]
    if not usable:
        result["warning"] = (
            "All headlines had empty titles; sentiment is not meaningful "
            "(the news source may have changed its response format)."
        )
        result["sentiment_count"] = 0
        return result
    if len(usable) < len(headlines):
        logger.warning(
            "%d of %d headlines had no title and were ignored",
            len(headlines) - len(usable), len(headlines),
        )
    headlines = usable

    # Record which model actually produced the numbers: "auto" silently falls back
    # to VADER when FinBERT is unavailable, and callers should be able to tell.
    if model_preference == "vader":
        scores = _score_vader(headlines)
        model_used = "vader" if scores else None
    else:
        scores = _score_finbert(headlines)
        model_used = "finbert" if scores else None
        if not scores and model_preference == "auto":
            scores = _score_vader(headlines)
            model_used = "vader" if scores else None
    result["model"] = model_used

    if not scores:
        result["warning"] = "Could not compute sentiment (FinBERT and VADER unavailable)."
        result["sentiment_count"] = len(headlines)
        return result

    import math
    n = len(scores)
    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / n if n else 0
    std = math.sqrt(variance) if variance > 0 else 0.0

    result["sentiment_mean"] = round(mean, 4)
    result["sentiment_std"] = round(std, 4)
    result["sentiment_count"] = n

    headline_scores = []
    for h, sc in zip(headlines, scores, strict=True):
        headline_scores.append({
            "title": h.get("title", ""),
            "score": round(sc, 4),
            "source": h.get("source", ""),
            "publishedAt": h.get("publishedAt", ""),
            "url": h.get("url", ""),
        })
    result["headline_scores"] = headline_scores

    sorted_by_score = sorted(headline_scores, key=lambda x: x["score"], reverse=True)
    result["top_positive"] = sorted_by_score[:3]
    result["top_negative"] = sorted_by_score[-3:][::-1]

    return result
