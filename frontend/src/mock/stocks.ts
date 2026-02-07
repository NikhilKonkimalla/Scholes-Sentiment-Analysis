export interface Stock {
  ticker: string;
  name: string;
  sectorId: string;
  currentPrice: number;
  dayChangePercent: number;
}

export interface PricePoint {
  date: string;
  price: number;
}

export interface OHLCPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface StockOption {
  type: 'call' | 'put';
  strike: number;
  optionPrice: number;
  confidence: number; // 0-100
}

// Stocks per sector (sectorId -> stocks)
export const MOCK_STOCKS_BY_SECTOR: Record<string, Stock[]> = {
  technology: [
    { ticker: 'AAPL', name: 'Apple Inc.', sectorId: 'technology', currentPrice: 192.50, dayChangePercent: 1.2 },
    { ticker: 'MSFT', name: 'Microsoft Corp.', sectorId: 'technology', currentPrice: 415.30, dayChangePercent: -0.5 },
    { ticker: 'GOOGL', name: 'Alphabet Inc.', sectorId: 'technology', currentPrice: 148.75, dayChangePercent: 0.8 },
    { ticker: 'AMZN', name: 'Amazon.com Inc.', sectorId: 'technology', currentPrice: 182.00, dayChangePercent: 1.5 },
    { ticker: 'NVDA', name: 'NVIDIA Corp.', sectorId: 'technology', currentPrice: 118.20, dayChangePercent: -2.1 },
    { ticker: 'META', name: 'Meta Platforms', sectorId: 'technology', currentPrice: 472.00, dayChangePercent: 0.3 },
  ],
  health: [
    { ticker: 'JNJ', name: 'Johnson & Johnson', sectorId: 'health', currentPrice: 158.40, dayChangePercent: 0.4 },
    { ticker: 'UNH', name: 'UnitedHealth', sectorId: 'health', currentPrice: 525.00, dayChangePercent: -0.2 },
    { ticker: 'PFE', name: 'Pfizer Inc.', sectorId: 'health', currentPrice: 28.50, dayChangePercent: 1.1 },
  ],
  finance: [
    { ticker: 'JPM', name: 'JPMorgan Chase', sectorId: 'finance', currentPrice: 205.00, dayChangePercent: 0.9 },
    { ticker: 'V', name: 'Visa Inc.', sectorId: 'finance', currentPrice: 275.20, dayChangePercent: -0.3 },
    { ticker: 'BAC', name: 'Bank of America', sectorId: 'finance', currentPrice: 38.75, dayChangePercent: 0.6 },
  ],
  energy: [
    { ticker: 'XOM', name: 'Exxon Mobil', sectorId: 'energy', currentPrice: 118.00, dayChangePercent: -0.8 },
    { ticker: 'CVX', name: 'Chevron', sectorId: 'energy', currentPrice: 162.50, dayChangePercent: 0.5 },
  ],
  consumer: [
    { ticker: 'TSLA', name: 'Tesla Inc.', sectorId: 'consumer', currentPrice: 252.80, dayChangePercent: 2.0 },
    { ticker: 'HD', name: 'Home Depot', sectorId: 'consumer', currentPrice: 385.00, dayChangePercent: -0.1 },
  ],
  industrials: [
    { ticker: 'CAT', name: 'Caterpillar', sectorId: 'industrials', currentPrice: 358.00, dayChangePercent: 0.7 },
    { ticker: 'BA', name: 'Boeing', sectorId: 'industrials', currentPrice: 185.20, dayChangePercent: -1.2 },
  ],
  utilities: [
    { ticker: 'NEE', name: 'NextEra Energy', sectorId: 'utilities', currentPrice: 72.50, dayChangePercent: 0.2 },
  ],
  materials: [
    { ticker: 'LIN', name: 'Linde plc', sectorId: 'materials', currentPrice: 425.00, dayChangePercent: 0.4 },
  ],
};

// Flatten for lookup by ticker
export function getStockByTicker(ticker: string): Stock | undefined {
  const upper = ticker.toUpperCase();
  for (const stocks of Object.values(MOCK_STOCKS_BY_SECTOR)) {
    const found = stocks.find((s) => s.ticker.toUpperCase() === upper);
    if (found) return found;
  }
  return undefined;
}

// Generate 30 days of mock prices for a ticker
export function generateMockPrices(_ticker: string, basePrice: number): PricePoint[] {
  const points: PricePoint[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const variation = (Math.random() - 0.5) * basePrice * 0.02;
    const prev = points.length ? points[points.length - 1].price : basePrice;
    points.push({
      date: d.toISOString().slice(0, 10),
      price: Math.round((prev + variation) * 100) / 100,
    });
  }
  return points;
}

// Generate 30 days of mock OHLC for candlestick charts
export function generateMockOHLC(_ticker: string, basePrice: number): OHLCPoint[] {
  const points: OHLCPoint[] = [];
  const now = new Date();
  let open = basePrice;
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const volatility = basePrice * 0.015;
    const change = (Math.random() - 0.5) * 2 * volatility;
    const close = Math.round((open + change) * 100) / 100;
    const high = Math.round((Math.max(open, close) + Math.random() * volatility * 0.5) * 100) / 100;
    const low = Math.round((Math.min(open, close) - Math.random() * volatility * 0.5) * 100) / 100;
    points.push({
      date: d.toISOString().slice(0, 10),
      open,
      high: Math.max(high, open, close),
      low: Math.min(low, open, close),
      close,
    });
    open = close;
  }
  return points;
}

// Mock options per stock
export const MOCK_STOCK_OPTIONS: Record<string, StockOption[]> = {
  AAPL: [
    { type: 'call', strike: 190, optionPrice: 8.50, confidence: 78 },
    { type: 'call', strike: 195, optionPrice: 5.20, confidence: 65 },
    { type: 'put', strike: 185, optionPrice: 4.10, confidence: 72 },
    { type: 'put', strike: 190, optionPrice: 6.80, confidence: 55 },
  ],
  MSFT: [
    { type: 'call', strike: 410, optionPrice: 12.00, confidence: 82 },
    { type: 'put', strike: 400, optionPrice: 9.50, confidence: 68 },
  ],
};

export function getOptionsForTicker(ticker: string): StockOption[] {
  const key = ticker.toUpperCase();
  return MOCK_STOCK_OPTIONS[key] ?? [
    { type: 'call', strike: 100, optionPrice: 3.50, confidence: 50 },
    { type: 'put', strike: 95, optionPrice: 2.80, confidence: 45 },
  ];
}
