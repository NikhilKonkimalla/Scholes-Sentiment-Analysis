/**
 * API service. Currently returns mock data with simulated delay.
 * Replace fetch calls with real backend when ready:
 *   GET /api/sectors
 *   GET /api/sectors/:sectorId/stocks
 *   GET /api/stocks/:ticker/prices?range=1m
 *   GET /api/stocks/:ticker/ai-summary
 *   GET /api/stocks/:ticker/options
 */

import type { Sector } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import { MOCK_SECTORS } from '../mock/sectors';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, generateMockPrices, generateMockOHLC, getOptionsForTicker } from '../mock/stocks';

const MOCK_DELAY_MS = 400;

function delay(ms: number = MOCK_DELAY_MS): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
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
  await delay();
  return Promise.resolve([...getOptionsForTicker(ticker)]);
}

export async function fetchStock(ticker: string): Promise<Stock | null> {
  await delay();
  const s = getStockByTicker(ticker);
  return Promise.resolve(s ?? null);
}
