/**
 * API service. Options come from backend (output_multi_ticker.csv) when the API
 * server is running; otherwise mock data is used. Sectors, stocks, prices, OHLC,
 * and ai-summary remain mock for now.
 */

import type { Sector } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import type { AiEvaluation } from '../mock/aiEvaluations';
import { MOCK_SECTORS } from '../mock/sectors';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, getTickerFullName, generateMockPrices, generateMockOHLC, getOptionsForTicker, EXTRA_TICKERS_CAP, EXTRA_TICKER_SECTORS, EXTRA_TICKERS_ORDER } from '../mock/stocks';
import { getAiEvaluation } from '../mock/aiEvaluations';

const API_BASE =
  (typeof import.meta !== 'undefined' && (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL) ||
  'http://localhost:5000';
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

/** Tickers we have options data for (from output_multi_ticker.csv). Null if backend unavailable. */
export async function fetchTickersWithData(): Promise<string[] | null> {
  const data = await get<{ tickers?: string[] }>('/api/tickers');
  if (data?.tickers?.length) return data.tickers;
  return null;
}

export async function fetchSectors(): Promise<Sector[]> {
  await delay();
  return Promise.resolve([...MOCK_SECTORS]);
}

/**
 * Stocks in a sector. If tickersWithData is provided (from backend), returns mock stocks
 * with data plus up to EXTRA_TICKERS_CAP extra tickers assigned to this sector (from API, not in mock).
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
    // Add extra tickers assigned to this sector (cap 20 total across all sectors)
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

/** Historical prices (close) and OHLC from backend (Yahoo Finance). Falls back to mock if API unavailable. */
export async function fetchStockPrices(ticker: string, range: string = '1m'): Promise<PricePoint[]> {
  const period = rangeToPeriod(range);
  const data = await get<{ prices: { date: string; price: number }[] }>(
    `/api/stocks/${encodeURIComponent(ticker)}/history?period=${encodeURIComponent(period)}`
  );
  if (data?.prices?.length) return data.prices;
  const stock = getStockByTicker(ticker);
  const base = stock?.currentPrice ?? 100;
  await delay();
  return Promise.resolve(generateMockPrices(ticker, base));
}

export async function fetchStockOHLC(ticker: string, range: string = '1m'): Promise<OHLCPoint[]> {
  const period = rangeToPeriod(range);
  const data = await get<{ ohlc: OHLCPoint[] }>(
    `/api/stocks/${encodeURIComponent(ticker)}/history?period=${encodeURIComponent(period)}`
  );
  if (data?.ohlc?.length) return data.ohlc;
  const stock = getStockByTicker(ticker);
  const base = stock?.currentPrice ?? 100;
  await delay();
  return Promise.resolve(generateMockOHLC(ticker, base));
}

/** Per-ticker AI evaluation (summary + related articles). Mock for now; replace with GET /api/stocks/:ticker/ai-summary when available. */
export async function fetchStockAiEvaluation(ticker: string): Promise<AiEvaluation> {
  await delay();
  return Promise.resolve(getAiEvaluation(ticker));
}

export async function fetchStockOptions(ticker: string): Promise<StockOption[]> {
  const data = await get<{ options: StockOption[] }>(`/api/stocks/${encodeURIComponent(ticker)}/options`);
  if (data?.options?.length) return data.options;
  await delay();
  return Promise.resolve([...getOptionsForTicker(ticker)]);
}

/** Stock metadata. Uses backend quote (Yahoo) for price/dayChange when API is up; otherwise mock. */
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
          name: ticker,
          sectorId: 'technology',
          currentPrice: quote.currentPrice,
          dayChangePercent: quote.dayChangePercent ?? 0,
        };
  }
  await delay();
  return Promise.resolve(mock ?? null);
}
