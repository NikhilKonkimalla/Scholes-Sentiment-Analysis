/**
 * API service. Options, quotes, price history and per-ticker news sentiment all come
 * from the backend when it is reachable. Sectors and the sector -> stock mapping are
 * still static.
 *
 * Where a fallback exists it is tagged (e.g. `source: 'mock'`) so the UI can label it.
 * Price history has NO fallback on purpose: it used to return a `Math.random()` walk
 * that rendered as a plausible-looking chart with nothing marking it as fake, which is
 * worse than showing no chart at all. Unavailable now means an empty series.
 */

import type { Sector } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import type { AiEvaluation } from '../mock/aiEvaluations';
import { MOCK_SECTORS } from '../mock/sectors';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, getTickerFullName, getOptionsForTicker, EXTRA_TICKERS_CAP, EXTRA_TICKER_SECTORS, EXTRA_TICKERS_ORDER } from '../mock/stocks';
import { getAiEvaluation } from '../mock/aiEvaluations';

/**
 * API base URL. Set VITE_API_URL at build time to point at a deployed backend.
 * Falls back to the local Flask server during `vite dev`, and to same-origin in a
 * production build so a host that proxies /api to the backend works unchanged.
 */
const viteEnv =
  (typeof import.meta !== 'undefined'
    ? (import.meta as { env?: { VITE_API_URL?: string; DEV?: boolean } }).env
    : undefined) ?? {};
const API_BASE = viteEnv.VITE_API_URL || (viteEnv.DEV ? 'http://localhost:5000' : '');
const MOCK_DELAY_MS = 400;

function delay(ms: number = MOCK_DELAY_MS): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { method: 'GET' });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Call this to see if the options backend (api_server.py) is running. */
export async function checkBackendHealth(): Promise<boolean> {
  const data = await get<{ status?: string }>('/api/health');
  return data != null && data.status === 'ok';
}

export interface BackendStatus {
  ok: boolean;
  /** ISO timestamp of when the options snapshot was generated. */
  dataAsOf?: string | null;
  tickersLoaded?: number;
  optionsLive?: number;
}

/** Backend status including the snapshot date, for the footer. */
export async function fetchBackendStatus(): Promise<BackendStatus> {
  const data = await get<{
    status?: string;
    dataAsOf?: string | null;
    tickers_loaded?: number;
    options_live?: number;
  }>('/api/health');
  if (data?.status !== 'ok') return { ok: false };
  return {
    ok: true,
    dataAsOf: data.dataAsOf ?? null,
    tickersLoaded: data.tickers_loaded,
    optionsLive: data.options_live,
  };
}

/** Tickers we have options data for. Null if backend unavailable. */
export async function fetchTickersWithData(): Promise<string[] | null> {
  const data = await get<{ tickers?: string[] }>('/api/tickers');
  if (data?.tickers?.length) return data.tickers;
  return null;
}

/**
 * Highest-conviction options across every ticker, ranked by |score|.
 * Returns null when the backend is unreachable — the caller shows an empty state
 * rather than inventing rows.
 */
export async function fetchTopOptions(limit: number = 25): Promise<StockOption[] | null> {
  const data = await get<{ options?: StockOption[] }>(
    `/api/options/top?limit=${encodeURIComponent(String(limit))}`
  );
  if (data?.options) return data.options;
  return null;
}

export async function fetchSectors(): Promise<Sector[]> {
  await delay();
  return Promise.resolve([...MOCK_SECTORS]);
}

/**
 * Stocks in a sector. If tickersWithData is provided (from backend), returns mock stocks
 * with data plus up to EXTRA_TICKERS_CAP extra tickers assigned to this sector.
 */
export async function fetchSectorStocks(
  sectorId: string,
  tickersWithData?: string[] | null
): Promise<Stock[]> {
  await delay();
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
  return Promise.resolve([...stocks]);
}

/** Map range to yfinance period. */
function rangeToPeriod(range: string): string {
  if (range === '5d') return '5d';
  if (range === '3m' || range === '3mo') return '3mo';
  if (range === '6m' || range === '6mo') return '6mo';
  if (range === '1y') return '1y';
  return '1mo';
}

/**
 * Historical closes from the backend (Yahoo Finance).
 * Returns an empty array when unavailable — never synthetic prices.
 */
export async function fetchStockPrices(ticker: string, range: string = '1m'): Promise<PricePoint[]> {
  const period = rangeToPeriod(range);
  const data = await get<{ prices: { date: string; price: number }[] }>(
    `/api/stocks/${encodeURIComponent(ticker)}/history?period=${encodeURIComponent(period)}`
  );
  return data?.prices ?? [];
}

/** Historical OHLC from the backend. Empty array when unavailable — never synthetic. */
export async function fetchStockOHLC(ticker: string, range: string = '1m'): Promise<OHLCPoint[]> {
  const period = rangeToPeriod(range);
  const data = await get<{ ohlc: OHLCPoint[] }>(
    `/api/stocks/${encodeURIComponent(ticker)}/history?period=${encodeURIComponent(period)}`
  );
  return data?.ohlc ?? [];
}

/**
 * Per-ticker news sentiment from the backend: real recent headlines scored by
 * FinBERT (or VADER). Falls back to the placeholder only when the API is
 * unreachable, tagged `source: 'mock'` so the UI can say so.
 */
export async function fetchStockAiEvaluation(ticker: string): Promise<AiEvaluation> {
  const data = await get<{
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
  }>(`/api/stocks/${encodeURIComponent(ticker)}/ai-summary`);

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

  await delay();
  return { ...getAiEvaluation(ticker), source: 'mock', available: false };
}

export async function fetchStockOptions(ticker: string): Promise<StockOption[]> {
  const data = await get<{ options: StockOption[] }>(`/api/stocks/${encodeURIComponent(ticker)}/options`);
  if (data?.options?.length) return data.options;
  await delay();
  return Promise.resolve([...getOptionsForTicker(ticker)]);
}

/**
 * Stock metadata. Uses the backend quote (Yahoo) for price/dayChange when the API is
 * up. Without it, the name and sector still come from the static map but the price is
 * reported as 0 = unavailable, rather than passing a stale hardcoded number off as
 * the current price.
 */
export async function fetchStock(ticker: string): Promise<Stock | null> {
  const quote = await get<{ currentPrice: number; dayChangePercent: number }>(
    `/api/stocks/${encodeURIComponent(ticker)}/quote`
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
  await delay();
  if (mock) return { ...mock, currentPrice: 0, dayChangePercent: 0 };
  return {
    ticker: ticker.toUpperCase(),
    name: getTickerFullName(ticker),
    sectorId: 'technology',
    currentPrice: 0,
    dayChangePercent: 0,
  };
}
