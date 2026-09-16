/**
 * Data access for the UI. Two modes, chosen at build time:
 *
 *   api     (default) calls the Flask backend, api_server.py. Used in development.
 *   static  reads JSON exported by export_static_data.py from `<base>/data/`. Used for
 *           hosting with no backend; build with VITE_DATA_MODE=static.
 *
 * The static files are the literal API responses, so both modes return the same shapes.
 *
 * Price history and quotes have no synthetic fallback: they used to return a
 * `Math.random()` walk that rendered as a plausible chart, which is worse than no chart.
 */

import type { Sector } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import type { AiEvaluation } from '../mock/aiEvaluations';
import { MOCK_SECTORS } from '../mock/sectors';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, getTickerFullName, getOptionsForTicker, EXTRA_TICKERS_CAP, EXTRA_TICKER_SECTORS, EXTRA_TICKERS_ORDER } from '../mock/stocks';
import { getAiEvaluation } from '../mock/aiEvaluations';

type ViteEnv = { VITE_API_URL?: string; VITE_DATA_MODE?: string; DEV?: boolean; BASE_URL?: string };
const viteEnv: ViteEnv =
  (typeof import.meta !== 'undefined' ? (import.meta as { env?: ViteEnv }).env : undefined) ?? {};

/** True when the site was built to read static JSON instead of calling the backend. */
export const IS_STATIC = viteEnv.VITE_DATA_MODE === 'static';

/**
 * API base URL (api mode). Set VITE_API_URL to point at a deployed backend. Falls back to
 * the local Flask server during `vite dev`, and to same-origin in a production build.
 */
const API_BASE = viteEnv.VITE_API_URL || (viteEnv.DEV ? 'http://localhost:5000' : '');

/** Root of the exported JSON (static mode), respecting the deploy base path. */
const STATIC_ROOT = `${(viteEnv.BASE_URL ?? '/').replace(/\/?$/, '/')}data`;

const MOCK_DELAY_MS = 400;

function delay(ms: number = MOCK_DELAY_MS): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { method: 'GET' });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Fetch an API route in api mode, or its exported file in static mode. */
function load<T>(apiPath: string, staticFile: string): Promise<T | null> {
  return IS_STATIC ? fetchJson<T>(`${STATIC_ROOT}/${staticFile}`) : fetchJson<T>(`${API_BASE}${apiPath}`);
}

function tickerFile(dir: string, ticker: string): string {
  return `${dir}/${encodeURIComponent(ticker.toUpperCase())}.json`;
}

function tickerPath(ticker: string): string {
  return encodeURIComponent(ticker);
}

/**
 * Whether a contract is still before expiration. The API filters expired contracts, but a
 * static snapshot ages in place between refreshes, so this is also applied at read time.
 */
function isLive(o: StockOption): boolean {
  const t = Date.parse(o.expiration);
  return Number.isNaN(t) || t >= Date.now();
}

type HealthPayload = {
  status?: string;
  dataAsOf?: string | null;
  tickers_loaded?: number;
  options_live?: number;
};

/** Whether data is reachable: the backend in api mode, the exported snapshot in static mode. */
export async function checkBackendHealth(): Promise<boolean> {
  const data = await load<HealthPayload>('/api/health', 'meta.json');
  return data?.status === 'ok';
}

export interface BackendStatus {
  ok: boolean;
  /** ISO timestamp of when the options snapshot was generated. */
  dataAsOf?: string | null;
  tickersLoaded?: number;
  optionsLive?: number;
}

/** Data status including the snapshot date, for the footer. */
export async function fetchBackendStatus(): Promise<BackendStatus> {
  const data = await load<HealthPayload>('/api/health', 'meta.json');
  if (data?.status !== 'ok') return { ok: false };
  return {
    ok: true,
    dataAsOf: data.dataAsOf ?? null,
    tickersLoaded: data.tickers_loaded,
    optionsLive: data.options_live,
  };
}

/** Tickers we have options data for. Null if unavailable. */
export async function fetchTickersWithData(): Promise<string[] | null> {
  const data = await load<{ tickers?: string[] }>('/api/tickers', 'tickers.json');
  if (data?.tickers?.length) return data.tickers;
  return null;
}

/**
 * Highest-conviction options across every ticker, ranked by |score|.
 * Null when unavailable — the caller shows an empty state rather than inventing rows.
 */
export async function fetchTopOptions(limit: number = 25): Promise<StockOption[] | null> {
  const data = await load<{ options?: StockOption[] }>(
    `/api/options/top?limit=${encodeURIComponent(String(limit))}`,
    'top-options.json'
  );
  if (!data?.options) return null;
  return data.options.filter(isLive).slice(0, limit);
}

export async function fetchSectors(): Promise<Sector[]> {
  if (!IS_STATIC) await delay();
  return [...MOCK_SECTORS];
}

/**
 * Stocks in a sector. If tickersWithData is provided, returns mapped stocks that have
 * data plus up to EXTRA_TICKERS_CAP extra tickers assigned to this sector.
 */
export async function fetchSectorStocks(
  sectorId: string,
  tickersWithData?: string[] | null
): Promise<Stock[]> {
  if (!IS_STATIC) await delay();
  let stocks = MOCK_STOCKS_BY_SECTOR[sectorId] ?? [];
  if (tickersWithData != null && tickersWithData.length > 0) {
    const set = new Set(tickersWithData.map((t) => t.toUpperCase()));
    stocks = stocks.filter((s) => set.has(s.ticker.toUpperCase()));
    const apiOnly = tickersWithData.filter((t) => !getStockByTicker(t));
    const inMap = apiOnly.filter((t) => EXTRA_TICKER_SECTORS[t.toUpperCase()]);
    const ordered = [...inMap].sort((a, b) => {
      const i = EXTRA_TICKERS_ORDER.indexOf(a.toUpperCase());
      const j = EXTRA_TICKERS_ORDER.indexOf(b.toUpperCase());
      if (i < 0 && j < 0) return 0;
      if (i < 0) return 1;
      if (j < 0) return -1;
      return i - j;
    });
    const capped = ordered.slice(0, EXTRA_TICKERS_CAP);
    const forSector = capped.filter((t) => (EXTRA_TICKER_SECTORS[t.toUpperCase()] ?? '') === sectorId);
    for (const t of forSector) {
      stocks.push({
        ticker: t.toUpperCase(),
        name: getTickerFullName(t),
        sectorId,
        // 0 means "price unavailable" — the UI renders an em dash, not $0.00.
        currentPrice: 0,
        dayChangePercent: 0,
      });
    }
  }
  return [...stocks];
}

/** Map range to yfinance period. */
function rangeToPeriod(range: string): string {
  if (range === '5d') return '5d';
  if (range === '3m' || range === '3mo') return '3mo';
  if (range === '6m' || range === '6mo') return '6mo';
  if (range === '1y') return '1y';
  return '1mo';
}

type HistoryPayload = { prices?: PricePoint[]; ohlc?: OHLCPoint[] };

function loadHistory(ticker: string, range: string): Promise<HistoryPayload | null> {
  const period = rangeToPeriod(range);
  // The static export snapshots one month of history per ticker.
  return load<HistoryPayload>(
    `/api/stocks/${tickerPath(ticker)}/history?period=${encodeURIComponent(period)}`,
    tickerFile('history', ticker)
  );
}

/** Historical closes. Empty array when unavailable — never synthetic prices. */
export async function fetchStockPrices(ticker: string, range: string = '1m'): Promise<PricePoint[]> {
  return (await loadHistory(ticker, range))?.prices ?? [];
}

/** Historical OHLC. Empty array when unavailable — never synthetic. */
export async function fetchStockOHLC(ticker: string, range: string = '1m'): Promise<OHLCPoint[]> {
  return (await loadHistory(ticker, range))?.ohlc ?? [];
}

type SentimentPayload = {
  available?: boolean;
  reason?: string;
  summary?: string;
  sentimentMean?: number | null;
  sentimentStd?: number | null;
  headlineCount?: number;
  positive?: number;
  negative?: number;
  neutral?: number;
  model?: string | null;
  generatedAt?: string;
  articles?: { title: string; url: string; source?: string; score?: number }[];
};

/**
 * Per-ticker news sentiment: real recent headlines scored by FinBERT (or VADER).
 * In api mode, falls back to the placeholder only when the backend is unreachable,
 * tagged `source: 'mock'` so the UI can say so.
 */
export async function fetchStockAiEvaluation(ticker: string): Promise<AiEvaluation> {
  const data = await load<SentimentPayload>(
    `/api/stocks/${tickerPath(ticker)}/ai-summary`,
    tickerFile('sentiment', ticker)
  );

  if (data && typeof data.available === 'boolean') {
    return {
      source: 'live',
      available: data.available,
      reason: data.reason ?? '',
      summary: data.summary ?? '',
      articles: data.articles ?? [],
      sentimentMean: data.sentimentMean ?? null,
      sentimentStd: data.sentimentStd ?? null,
      headlineCount: data.headlineCount ?? 0,
      positive: data.positive ?? 0,
      negative: data.negative ?? 0,
      neutral: data.neutral ?? 0,
      model: data.model ?? null,
      generatedAt: data.generatedAt,
    };
  }

  if (IS_STATIC) {
    return {
      summary: '',
      articles: [],
      source: 'live',
      available: false,
      reason: 'No sentiment snapshot for this ticker.',
    };
  }

  await delay();
  return { ...getAiEvaluation(ticker), source: 'mock', available: false };
}

export async function fetchStockOptions(ticker: string): Promise<StockOption[]> {
  const data = await load<{ options?: StockOption[] }>(
    `/api/stocks/${tickerPath(ticker)}/options`,
    tickerFile('options', ticker)
  );
  if (IS_STATIC) return (data?.options ?? []).filter(isLive);
  if (data?.options?.length) return data.options;
  await delay();
  return [...getOptionsForTicker(ticker)];
}

/**
 * Stock metadata with the quote's price/day change. Without a quote, the name and sector
 * still come from the static map but the price is 0 = unavailable, rather than passing a
 * stale hardcoded number off as the current price.
 */
export async function fetchStock(ticker: string): Promise<Stock | null> {
  const quote = await load<{ currentPrice?: number; dayChangePercent?: number }>(
    `/api/stocks/${tickerPath(ticker)}/quote`,
    tickerFile('quote', ticker)
  );
  const mock = getStockByTicker(ticker);
  if (quote && typeof quote.currentPrice === 'number') {
    return mock
      ? { ...mock, currentPrice: quote.currentPrice, dayChangePercent: quote.dayChangePercent ?? 0 }
      : {
          ticker: ticker.toUpperCase(),
          name: getTickerFullName(ticker),
          sectorId: 'technology',
          currentPrice: quote.currentPrice,
          dayChangePercent: quote.dayChangePercent ?? 0,
        };
  }
  if (!IS_STATIC) await delay();
  if (mock) return { ...mock, currentPrice: 0, dayChangePercent: 0 };
  return {
    ticker: ticker.toUpperCase(),
    name: getTickerFullName(ticker),
    sectorId: 'technology',
    currentPrice: 0,
    dayChangePercent: 0,
  };
}
