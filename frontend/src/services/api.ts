/**
 * API service. Options come from backend (output_multi_ticker.csv) when the API
 * server is running; otherwise mock data is used. Sectors, stocks, prices, OHLC,
 * and ai-summary remain mock for now.
 */

import type { Sector } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import type { AiEvaluation } from '../mock/aiEvaluations';
import { MOCK_SECTORS } from '../mock/sectors';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, generateMockPrices, generateMockOHLC, getOptionsForTicker } from '../mock/stocks';
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
 * Stocks in a sector. If tickersWithData is provided (from backend), only returns stocks
 * we have options data for; otherwise returns all mock stocks in that sector.
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
  }
  return Promise.resolve([...stocks]);
}

export async function fetchStockPrices(ticker: string, _range: string = '1m'): Promise<PricePoint[]> {
  await delay();
  const stock = getStockByTicker(ticker);
  const base = stock?.currentPrice ?? 100;
  return Promise.resolve(generateMockPrices(ticker, base));
}

export async function fetchStockOHLC(ticker: string, _range: string = '1m'): Promise<OHLCPoint[]> {
  await delay();
  const stock = getStockByTicker(ticker);
  const base = stock?.currentPrice ?? 100;
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

export async function fetchStock(ticker: string): Promise<Stock | null> {
  await delay();
  const s = getStockByTicker(ticker);
  return Promise.resolve(s ?? null);
}
