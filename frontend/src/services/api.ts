/**
 * API service. Options come from backend (output_multi_ticker.csv) when the API
 * server is running; otherwise mock data is used. Sectors, stocks, prices, OHLC,
 * and ai-summary remain mock for now.
 */

import type { Sector } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import { MOCK_SECTORS } from '../mock/sectors';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, generateMockPrices, generateMockOHLC, getOptionsForTicker } from '../mock/stocks';

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

export async function fetchSectors(): Promise<Sector[]> {
  await delay();
  return Promise.resolve([...MOCK_SECTORS]);
}

export async function fetchSectorStocks(sectorId: string): Promise<Stock[]> {
  await delay();
  const stocks = MOCK_STOCKS_BY_SECTOR[sectorId] ?? [];
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

export async function fetchStockAiSummary(ticker: string): Promise<string> {
  await delay();
  const mockSummary = `Based on recent volatility, earnings sentiment, and options flow, ${ticker} shows moderate bullish bias over the next 30 days. Implied volatility is near the 20-day average. Key levels: support near the recent low, resistance at the prior high. Risk/reward favors selective call spreads over naked calls.`;
  return Promise.resolve(mockSummary);
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
