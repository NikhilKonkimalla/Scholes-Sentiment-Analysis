#!/usr/bin/env python3
"""
RSS-based social/news sentiment pipeline.
Uses only RSS feeds (no APIs, no auth). Fetches, scores sentiment, extracts
tickers, stores in SQLite, and prints rolling aggregates.
Run: python rss_sentiment.py
"""

import re
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from urllib.request import urlopen, Request
import feedparser

# -----------------------------------------------------------------------------
# CONFIGURATION: RSS feed URLs
# -----------------------------------------------------------------------------
# Reddit subreddit RSS (append .rss to subreddit URL)
# StockTwits and financial news RSS (public feeds, no auth)
DEFAULT_FEEDS = [
    "https://www.reddit.com/r/stocks/.rss",
    "https://www.reddit.com/r/wallstreetbets/.rss",
    "https://www.reddit.com/r/investing/.rss",
    "https://stocktwits.com/symbol/SPY.rss",  # example symbol feed
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://feeds.bloomberg.com/markets/news.rss",
]

# User-Agent for polite RSS fetching (some servers block default Python)
USER_AGENT = "Mozilla/5.0 (compatible; RSS-Sentiment-Bot/1.0)"

# -----------------------------------------------------------------------------
# SENTIMENT LEXICON (lightweight, rule-based)
# -----------------------------------------------------------------------------
# Finance-specific and general positive/negative terms. Score contribution
# is normalized so final score stays in [-1, 1].
POSITIVE_WORDS = {
    "bullish", "moon", "mooning", "rally", "rallies", "rallying", "buy", "long",
    "breakout", "breakouts", "surge", "surges", "soar", "soaring", "gain", "gains",
    "profit", "profits", "win", "winning", "growth", "strong", "recovery",
    "optimistic", "bull", "bulls", "green", "call", "calls", "undervalued",
    "breakthrough", "beat", "beats", "beating", "outperform", "upgrade", "upgraded",
}
NEGATIVE_WORDS = {
    "bearish", "dump", "dumps", "dumping", "crash", "crashes", "crashing",
    "sell", "short", "shorts", "collapse", "collapse", "plunge", "plunges",
    "drop", "drops", "fall", "falls", "loss", "losses", "bear", "bears",
    "red", "put", "puts", "overvalued", "recession", "fear", "panic",
    "miss", "misses", "missing", "downgrade", "downgraded", "weak", "weakness",
}

# -----------------------------------------------------------------------------
# DATABASE
# -----------------------------------------------------------------------------
DB_PATH = "rss_sentiment.db"


def get_connection():
    """Return a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def init_db(conn):
    """
    Create tables if they do not exist.
    - items: raw RSS items with timestamp, source, title, sentiment, tickers
    - We use ISO timestamp strings for easy rolling window queries.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            sentiment REAL NOT NULL,
            tickers TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_items_ts ON items(ts);
        CREATE INDEX IF NOT EXISTS idx_items_tickers ON items(tickers);
    """)
    conn.commit()


def fetch_rss(url, timeout=15):
    """
    Fetch and parse an RSS/Atom feed. Returns feedparser dict or None on failure.
    """
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        return feedparser.parse(data)
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def extract_text(entry):
    """
    Extract title and summary/description from a feed entry; combine into one string.
    """
    parts = []
    if getattr(entry, "title", None):
        parts.append(entry.title)
    if getattr(entry, "summary", None):
        parts.append(entry.summary)
    if getattr(entry, "description", None):
        parts.append(entry.description)
    text = " ".join(parts)
    # Strip HTML tags crudely for sentiment (keep words)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_sentiment(text):
    """
    Lightweight lexicon-based sentiment. Returns a score in [-1, 1].
    Uses finance slang and general positive/negative words; normalizes by
    total token count to avoid huge swings.
    """
    if not text:
        return 0.0
    text_lower = text.lower()
    words = re.findall(r"\b[a-z]+\b", text_lower)
    if not words:
        return 0.0
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    # Normalize: (pos - neg) / total, then clamp to [-1, 1]
    raw = (pos_count - neg_count) / len(words)
    return max(-1.0, min(1.0, raw * 5.0))  # scale so a few words can move score


def extract_tickers(text):
    """
    Extract cashtags like $AAPL, $TSLA. Returns list of uppercase ticker symbols.
    """
    if not text:
        return []
    matches = re.findall(r"\$([A-Z]{1,5})\b", text, re.IGNORECASE)
    return list(dict.fromkeys([m.upper() for m in matches]))


def store_item(conn, source, title, sentiment, tickers):
    """Insert one processed item into the database."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tickers_str = ",".join(tickers) if tickers else ""
    conn.execute(
        "INSERT INTO items (ts, source, title, sentiment, tickers) VALUES (?, ?, ?, ?, ?)",
        (ts, source, title, sentiment, tickers_str),
    )


def run_pipeline(feed_urls):
    """
    For each feed URL: fetch, parse, extract text, score sentiment, extract
    tickers, then store each item in SQLite.
    """
    conn = get_connection()
    init_db(conn)
    try:
        for url in feed_urls:
            feed = fetch_rss(url)
            if not feed or not feed.entries:
                continue
            source = feed.feed.get("title", url) or url
            for entry in feed.entries:
                text = extract_text(entry)
                title = (getattr(entry, "title", None) or "")[:500]
                sentiment = score_sentiment(text)
                tickers = extract_tickers(text)
                store_item(conn, source, title, sentiment, tickers)
        conn.commit()
    finally:
        conn.close()


def rolling_sentiment(conn, hours):
    """
    Average sentiment over the last `hours` (from items with any content).
    Returns a single float or None if no data.
    """
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        "SELECT AVG(sentiment) FROM items WHERE ts >= ?", (since,)
    ).fetchone()
    if row and row[0] is not None:
        return round(row[0], 4)
    return None


def per_ticker_sentiment(conn, hours, limit=10):
    """
    For items in the last `hours`, expand tickers and compute average sentiment
    per ticker. Returns two lists: (bullish_list, bearish_list), each of
    (ticker, avg_sentiment), sorted by sentiment desc/asc, top `limit`.
    """
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT sentiment, tickers FROM items WHERE ts >= ? AND tickers != ''",
        (since,),
    ).fetchall()
    # ticker -> list of sentiments
    by_ticker = {}
    for sentiment, tickers_str in rows:
        for t in tickers_str.split(","):
            t = t.strip()
            if not t:
                continue
            by_ticker.setdefault(t, []).append(sentiment)
    # averages
    avg = [(t, sum(s) / len(s)) for t, s in by_ticker.items()]
    avg.sort(key=lambda x: x[1], reverse=True)
    bullish = avg[:limit]
    bearish = avg[-limit:][::-1]
    return bullish, bearish


def get_ticker_sentiment(ticker: str, hours: int = 24) -> Optional[float]:
    """
    Average RSS/social sentiment for the given ticker over the last `hours`.
    Returns a float in [-1, 1] or None if no data. Safe to call if DB is missing.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return None
    try:
        conn = get_connection()
        try:
            since = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            rows = conn.execute(
                "SELECT sentiment, tickers FROM items WHERE ts >= ? AND tickers != ''",
                (since,),
            ).fetchall()
            sentiments = []
            for sentiment, tickers_str in rows:
                for t in tickers_str.split(","):
                    if t.strip().upper() == ticker:
                        sentiments.append(sentiment)
                        break
            if not sentiments:
                return None
            return round(sum(sentiments) / len(sentiments), 4)
        finally:
            conn.close()
    except Exception:
        return None


def get_rolling_sentiment(hours: int = 24) -> Optional[float]:
    """
    Overall (market) RSS/social sentiment over the last `hours`.
    Returns a float in [-1, 1] or None if no data. Safe to call if DB is missing.
    """
    try:
        conn = get_connection()
        try:
            return rolling_sentiment(conn, hours)
        finally:
            conn.close()
    except Exception:
        return None


def print_summary():
    """
    Compute rolling aggregates (1h, 6h, 24h), per-ticker sentiment, then
    print overall market sentiment and top 5 bullish/bearish tickers.
    """
    conn = get_connection()
    try:
        print("\n" + "=" * 60)
        print("RSS SENTIMENT SUMMARY")
        print("=" * 60)

        # Overall market sentiment
        for label, h in [("Last 1h", 1), ("Last 6h", 6), ("Last 24h", 24)]:
            s = rolling_sentiment(conn, h)
            if s is not None:
                print(f"  {label}: {s:+.4f}")
            else:
                print(f"  {label}: (no data)")

        # Per-ticker (last 24h), top 5 bullish and bearish
        bullish, bearish = per_ticker_sentiment(conn, hours=24, limit=5)
        print("\n  Top 5 bullish (24h):")
        for ticker, sent in bullish:
            print(f"    ${ticker}: {sent:+.4f}")
        print("  Top 5 bearish (24h):")
        for ticker, sent in bearish:
            print(f"    ${ticker}: {sent:+.4f}")
        print("=" * 60 + "\n")
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    run_pipeline(DEFAULT_FEEDS)
    print_summary()
