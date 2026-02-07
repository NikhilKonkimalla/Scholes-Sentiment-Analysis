# Scholes Analysis Pipeline

Backend-only Python pipeline that combines live underlying + options data (yfinance), Black-Scholes theoretical pricing, news sentiment (NewsAPI.ai + FinBERT / VADER), and an opportunity score blending mispricing and sentiment.

## Setup

1. Create a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **News** (choose one):

   - **Yahoo Finance** (default): No API key. Headlines are fetched by ticker via yfinance. Use `--news_source yahoo`.
   - **NewsAPI.ai**: Get a free key at [https://newsapi.ai](https://newsapi.ai) and set `NEWS_API_KEY`; use `--news_source newsapi` and optionally `--news_query "SPY OR S&P 500"`.

   ```bash
   export NEWS_API_KEY="your_api_key_here"   # only for --news_source newsapi
   ```

4. (Optional) First run will download NLTK data (e.g. VADER lexicon) and possibly FinBERT weights if you use the default sentiment model.

## Run

Default (SPY, 6 expirations, auto sentiment model):

```bash
python pipeline.py
```

With options:

```bash
# Yahoo Finance news (default; no API key)
python pipeline.py --ticker SPY --expirations 6 --r 0.045 --headlines 20 --model auto

# NewsAPI (set NEWS_API_KEY)
python pipeline.py --ticker SPY --news_source newsapi --news_query "SPY OR S&P 500" --headlines 20
```

- `--ticker`: Underlying symbol (default: SPY).
- `--expirations`: Max option expirations to fetch (default: 6).
- `--r`: Risk-free rate for Black-Scholes (default: 0.045).
- `--news_source`: `yahoo` (ticker-based, no key) or `newsapi` (uses `--news_query` and `NEWS_API_KEY`). Default: yahoo.
- `--news_query`: NewsAPI search query when `--news_source=newsapi` (default: "SPY OR S&P 500").
- `--headlines`: Number of headlines to fetch (default: 20).
- `--model`: Sentiment model: `auto` (FinBERT with VADER fallback) or `vader`.

## Frontend and options from CSV

The frontend can show **options with confidence/suggestions** from a pre-built multi-ticker CSV (`output_multi_ticker.csv`, e.g. from `pipeline_multi_ticker.py`).

1. **Generate the CSV** (if needed):
   ```bash
   python pipeline_multi_ticker.py --headlines_csv newsapi_headlines_500.csv --output output_multi_ticker.csv
   ```

2. **Start the API server** (reads `output_multi_ticker.csv` from the project root):
   ```bash
   pip install flask flask-cors
   python api_server.py
   ```
   Server runs at http://localhost:5000.

3. **Start the frontend**:
   ```bash
   cd frontend && npm install && npm run dev
   ```
   Open http://localhost:5173 → Sectors → pick a stock. Options for that ticker are loaded from the CSV; **confidence** is derived from the score column. If the API server is not running, the frontend falls back to mock options.

## Outputs

- **CSV**: `output_{ticker}.csv` — full options chain with theoretical price, pricing gap, liquidity, spread penalty, alignment, opportunity score, and risk flag.
- **JSON**: `sentiment_{ticker}.json` — sentiment summary (mean, std, count), per-headline scores, top positive/negative headlines.
- **Console**: Top 15 opportunities by absolute opportunity score.

## Module overview

| File | Role |
|------|------|
| `pipeline.py` | CLI entrypoint: orchestration, CSV/JSON write, top-15 print |
| `market_data.py` | `get_spot()`, `get_options_chain()` via yfinance |
| `bs.py` | Black-Scholes pricing and self-test |
| `news_sentiment.py` | News: `fetch_headlines_newsapi()`, `fetch_headlines_yahoo()`, unified `fetch_headlines(source=...)`; FinBERT/VADER `score_headlines()` |
| `scoring.py` | Opportunity score (theo, gap, liquidity, spread, alignment, risk flag) |

## Limitations

- **Rate limits**: NewsAPI.ai free tier has 2,000 credits. Yahoo Finance (yfinance) is not an official API and can be throttled or change; ticker news may occasionally be generic.
- **Sentiment**: FinBERT requires `transformers` and `torch`; if unavailable or failing, the pipeline falls back to VADER without crashing.
- **Data quality**: Options data (IV, volume, open interest) and news sentiment are used as-is; no guarantee of completeness or accuracy.
- **No UI**: CLI and file outputs only; no dashboard or web interface.
- **Expiration time**: Option expiration is treated as 16:00 US/Eastern (or 20:00 UTC fallback) for time-to-expiry; actual settlement may differ by product.

## Black-Scholes self-test

Run the BS module self-test:

```bash
python -m bs
```

Expected: `BS self-test passed.`
