# Scholes Analysis Pipeline

Python pipeline that combines live underlying + options data (yfinance), Black-Scholes theoretical pricing, news sentiment (NewsAPI.ai + FinBERT / VADER), and an opportunity score blending mispricing and sentiment. A React frontend and a Flask API serve the results in a browser.

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

   | File | Contents |
   |------|----------|
   | `requirements.txt` | Core — everything needed to run the pipelines and the API server |
   | `requirements-ml.txt` | Optional FinBERT extras (`torch` + `transformers`, ~2.5 GB) |
   | `requirements-dev.txt` | `pytest` + `ruff` for tests and linting |

   The heavy ML packages are deliberately **not** in the core file: without them,
   sentiment scoring falls back to VADER automatically and every pipeline still runs.
   This also keeps the install small enough for free hosting tiers. For FinBERT:

   ```bash
   pip install -r requirements.txt -r requirements-ml.txt
   ```

### FinBERT vs VADER

FinBERT is used automatically whenever `transformers` + `torch` are importable;
otherwise sentiment silently falls back to VADER. Every response and every
`sentiment_{ticker}.json` records which one ran, in the `model` field — check it rather
than assuming.

FinBERT is markedly better on financial phrasing. On the same five headlines:

| Headline | FinBERT | VADER |
|----------|--------:|------:|
| "Apple beats earnings expectations, raises full-year guidance" | **+0.94** | 0.00 |
| "Company faces massive lawsuit and issues profit warning" | **−0.97** | −0.10 |
| "Shares plunge after disappointing quarterly revenue miss" | **−0.97** | −0.38 |
| "The board of directors will meet on Tuesday" | 0.00 | 0.00 |

VADER's general-purpose lexicon scores the first headline a flat 0.00 — it has no idea
that "beats expectations" is good news. That is the case for installing the extras.

Costs and caveats:

- **Disk**: ~1.2 GB for the virtualenv, plus ~1.0 GB of cached weights in
  `~/.cache/huggingface`.
- **Latency**: the first `ai-summary` call per process pays the model load — roughly
  3.7 s, against ~0.8 s for VADER. Subsequent calls hit the in-process cache
  (sub-millisecond). On serverless this cost recurs on every cold start.
- **Not infallible**: FinBERT scored "Analysts upgrade the stock following record cloud
  growth" as *negative* — though only just (negative 0.541 vs positive 0.415), and both
  halves of that sentence score positive on their own. Treat individual scores as noisy;
  the aggregate mean is the useful signal.
- **Pinned revision**: the model loads from `revision="main"`. See the comment in
  `news_sentiment._get_finbert()` for why.

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
- `--headlines`: Number of headlines to fetch (default: 100; NewsAPI.ai allows up to 100 per search).
- `--model`: Sentiment model: `auto` (FinBERT with VADER fallback) or `vader`.
- `--sentiment-weight`: 1.0 (default) scores on sentiment direction alone; 0.0 scores on
  mispricing alone (underpriced = Buy); values in between blend the two.
- `--no-rss` / `--rss-weight`: disable or weight the RSS/social sentiment blend.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q          # offline; no network or API keys required
ruff check .
```

## Frontend and options from CSV

The frontend shows **options with confidence/suggestions** from a pre-built multi-ticker CSV.

1. **Generate the CSV.** Options data goes stale quickly — once every contract in the
   file has expired the API serves nothing, so regenerate before relying on it:
   ```bash
   python pipeline_multi_ticker.py --headlines_csv newsapi_headlines_500.csv --output data.csv
   ```
   Pass `--tickers AAPL,MSFT,...` to control coverage and `--expirations N` for depth.

2. **Start the API server** (reads `data.csv` from the project root by default):
   ```bash
   pip install -r requirements.txt
   python api_server.py
   ```
   Server runs at http://localhost:5000.

   Environment overrides:

   | Variable | Purpose |
   |----------|---------|
   | `CSV_PATH` | Options CSV to serve (default: `data.csv`; e.g. `output_multi_ticker.csv`) |
   | `CORS_ORIGINS` | Comma-separated allowed browser origins, or `*`. Required once the frontend is deployed |
   | `PORT` | Port to bind (default: 5000) |
   | `AI_SUMMARY_TTL_SECONDS` | How long per-ticker sentiment is cached (default: 900) |

   Endpoints:

   | Endpoint | Source |
   |----------|--------|
   | `GET /api/tickers` | Loaded CSV |
   | `GET /api/stocks/:ticker/options` | Loaded CSV |
   | `GET /api/options/top?limit=25&type=call` | Loaded CSV, ranked by \|score\| across all tickers |
   | `GET /api/stocks/:ticker/quote` | Yahoo Finance (live) |
   | `GET /api/stocks/:ticker/history?period=1mo` | Yahoo Finance (live) |
   | `GET /api/stocks/:ticker/ai-summary` | Recent Yahoo headlines scored by FinBERT/VADER |
   | `GET /api/health` | Status, ticker count, live vs total options, snapshot date |

   **Snapshot date.** `pipeline_multi_ticker.py` writes a `data_meta.json` sidecar next
   to its output CSV, and `/api/health` reports it as `dataAsOf` so the UI can show
   "Data as of <date>" in the footer (and flag it once it is more than 30 days old).
   The sidecar exists because file mtimes are unreliable in deployment — a fresh git
   checkout stamps every file with the deploy time, which would report stale data as new.
   If the sidecar is missing, the server falls back to the CSV's mtime.

   **No invented market data.** Price history and quotes have no mock fallback: when the
   backend is unreachable the chart renders an explicit "Price history unavailable" state
   and the price reads "price unavailable", rather than a synthetic random walk or a stale
   hardcoded number. Surfaces that do still fall back (the per-ticker options table, the
   sentiment panel) label themselves in the UI.

   `ai-summary` returns a **descriptive** reading of real headlines — the mean sentiment,
   the positive/negative/neutral split, which model scored it, and the scored headlines
   themselves with links. It deliberately states no opinion and makes no recommendation.
   Results are cached per ticker (see `AI_SUMMARY_TTL_SECONDS`) because Yahoo rate-limits
   quickly once page views fan out across tickers. When no headlines are available the
   response is `{"available": false, "reason": ...}` and the UI says so rather than
   inventing commentary.

   > **macOS:** AirPlay Receiver occupies port 5000 and replies `403`. Either disable it in
   > System Settings → General → AirDrop & Handoff, or run with `PORT=5055 python api_server.py`.

   **Expired contracts are filtered out of every response by default**, and tickers whose
   options have all expired are omitted from `/api/tickers`, so a stale CSV cannot surface
   dead options as live suggestions. Add `?include_expired=true` to any options or tickers
   request to see them anyway. `/api/health` reports `options_total` vs `options_live`.

3. **Start the frontend**:
   ```bash
   cd frontend && npm install && npm run dev
   ```
   Open http://localhost:5173 → Sectors → pick a stock. Options for that ticker are loaded from the CSV; **confidence** is derived from the score column. If the API server is not running, the frontend falls back to mock options.

   For a deployed build, point the frontend at the backend with `VITE_API_URL`:
   ```bash
   VITE_API_URL=https://your-api.example.com npm run build
   ```
   Left unset, a production build calls the same origin it is served from (so a host that
   proxies `/api` to the backend works as-is).

## Hosting (GitHub Pages, no backend)

The public site is fully static. `export_static_data.py` writes every API response the
frontend needs to `frontend/public/data/` as JSON, and a frontend built with
`VITE_DATA_MODE=static` reads those files instead of calling `api_server.py`.

`.github/workflows/refresh-and-deploy.yml` rebuilds and deploys it:

- **Five times per US trading day** it re-runs `pipeline_multi_ticker.py` for fresh options
  data. If Yahoo rate-limits the run and fewer than 80% of tickers come back, it keeps the
  committed `data.csv` rather than publishing a thinner site.
- On **every push to `main`** it redeploys using the committed snapshot.
- It can be run **manually** from the Actions tab.

One-time setup: push to GitHub, then in the repository go to
**Settings → Pages → Build and deployment → Source: GitHub Actions**. Scheduled runs only
fire from the default branch. The site is served at
`https://<owner>.github.io/<repo>/`; for a custom domain, set the repository variable
`SITE_BASE=/`.

To preview the static build locally:

```bash
python export_static_data.py            # add --skip-live to avoid Yahoo calls
cd frontend
VITE_DATA_MODE=static npm run build -- --base=/Scholes-Sentiment-Analysis/
npx vite preview --base=/Scholes-Sentiment-Analysis/
```

## Outputs

- **CSV**: `output_{ticker}.csv` — full options chain with theoretical price, pricing gap, liquidity, spread penalty, alignment, opportunity score, and risk flag.
- **JSON**: `sentiment_{ticker}.json` — sentiment summary (mean, std, count), per-headline scores, top positive/negative headlines.
- **Console**: Top 15 opportunities by absolute opportunity score.

## Module overview

| File | Role |
|------|------|
| `pipeline.py` | CLI entrypoint: orchestration, CSV/JSON write, top-15 print |
| `pipeline_multi_ticker.py` | Same scoring across many tickers into one combined CSV |
| `market_data.py` | `get_spot()`, `get_history()`, `get_quote()`, `get_options_chain()` via yfinance |
| `bs.py` | Black-Scholes pricing and self-test |
| `news_sentiment.py` | News: `fetch_headlines_newsapi()`, `fetch_headlines_yahoo()`, unified `fetch_headlines(source=...)`; FinBERT/VADER `score_headlines()` |
| `newsapi_client.py` | NewsAPI.ai (Event Registry) client with CSV caching |
| `rss_sentiment.py` | RSS/social sentiment into SQLite; per-ticker and rolling aggregates |
| `scoring.py` | Opportunity score (theo, gap, liquidity, spread, alignment, risk flag) |
| `api_server.py` | Flask API serving options from CSV plus live quote/history |
| `update_scores.py` | Recompute `score` in an existing options CSV |
| `tests/` | Offline regression tests (`pytest -q`) |

## Scoring notes

All three knobs below are module constants in `scoring.py`; tune them to taste.

- `opportunity_score` is normalized with a **fixed** tanh scale (`SCORE_SCALE`), so a
  score means the same thing for every ticker and every run and values are comparable
  across tickers. (A batch-relative scale would pin the best option in every batch to
  the same number.)
- `alignment` blends sentiment direction with mispricing direction according to
  `--sentiment-weight`.
- Contracts whose Black-Scholes value is below `MIN_THEO_PRICE` (default 0.05) are
  **excluded from scoring** and flagged in `risk_flag`. Deep out-of-the-money contracts
  near expiry price at ~1e-8, which turns `pricing_gap_pct` into a division artifact of
  tens of thousands of percent; without this guard they crowd out every real signal.
- The gap feeding the score is clipped to `MAX_ABS_GAP_PCT` (default 2.0 = 200%). The
  `pricing_gap_pct` column itself is left unclipped for inspection.

### The risk signal

A contract can score highly on mispricing while being untradeable, so `risk_flag`
travels with the score rather than being discarded. It is true when the bid/ask spread
exceeds the mid price, when `volume + openInterest` is under 10, or when the
theoretical price is too near zero to derive a meaningful gap from.

The output CSV carries `riskFlag` alongside the inputs it is derived from — `ask`,
`volume`, `openInterest`, `theoPrice`, `liquidityScore`, `spreadPenalty` — so the UI can
explain *why* a contract is flagged instead of just asserting it.

Flagged contracts are **marked, not hidden**: a high score is never shown without its
caveat, but nothing is silently removed from the ranking. Pass `?exclude_risky=true` to
`/api/options/top` or `/api/stocks/:ticker/options` to drop them, and use the "Hide
flagged" toggle on the home page for the same effect in the UI.

These columns are optional. A CSV generated before they existed yields `null`, which the
UI renders as unknown — never as "safe".

**Expect a high flag rate overall, and almost none at the top.** In the current snapshot
86% of all contracts are flagged, but 0 of the top 50 by |score| are:

| Rank window | Flagged |
|-------------|--------:|
| top 50      | 0.0% |
| top 100     | 0.0% |
| top 250     | 16.8% |
| all 12,425  | 86.1% |

That is the scoring working as intended rather than a defect. `spread_factor` is
`exp(-spread_penalty)`, so a contract with no usable quote scores `exp(-5) ≈ 0.0067` and
sinks to the bottom of the ranking on its own. The badge is therefore rare on the home
page (which shows the top 50) and common in the per-ticker tables, which list every
contract held for that symbol.

One caveat about the raw inputs: roughly 57% of rows arrive from Yahoo with no bid/ask at
all. `scoring.py` charges those the maximum spread penalty, which is reasonable for
ranking but means "no quote" and "very wide quote" land on the same number. The UI
distinguishes them from `bid`/`ask` directly, so a contract nobody is quoting is
described as "no bid/ask quote available" rather than a fictitious "500% spread".
Both snapshots measured so far were taken outside US market hours, so how much of that
57% is an after-hours artifact is not yet established.

## Limitations

- **Rate limits**: NewsAPI.ai free tier has 2,000 credits. Yahoo Finance (yfinance) is not an official API and can be throttled or change; ticker news may occasionally be generic. Reddit RSS feeds frequently return HTTP 429; those fetches are skipped with a warning.
- **Sentiment**: FinBERT requires `transformers` and `torch`; if unavailable or failing, the pipeline falls back to VADER without crashing.
- **Data quality**: Options data (IV, volume, open interest) and news sentiment are used as-is; no guarantee of completeness or accuracy. Illiquid or deep-ITM contracts can carry stale quotes, which show up as large apparent mispricings — check `risk_flag`.
- **Expiration time**: Option expiration is treated as 16:00 US/Eastern (or 20:00 UTC fallback) for time-to-expiry; actual settlement may differ by product.
- **Cloud hosting**: Yahoo Finance often rate-limits datacenter IPs, so live quote/history endpoints can be flakier when deployed than when run locally.

## Black-Scholes self-test

Run the BS module self-test:

```bash
python -m bs
```

Expected: `BS self-test passed.`
