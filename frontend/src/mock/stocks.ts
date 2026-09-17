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
  ticker: string;
  type: 'call' | 'put';
  expiration: string;
  contractSymbol: string;
  strike: number;
  price: number;
  bid: number;
  midPrice: number;
  score: number;
  impliedVolatility: number;
  /** @deprecated Use midPrice. Kept for backward compat. */
  optionPrice?: number;
  /** 0-100, derived from score. Kept for backward compat. */
  confidence?: number;

  // Risk / liquidity signal. All nullable: null means the backing CSV predates these
  // columns, which must render as "unknown" — never as "safe".
  ask?: number | null;
  /** True when the contract is wide-spread, illiquid, or has no usable theoretical price. */
  riskFlag?: boolean | null;
  volume?: number | null;
  openInterest?: number | null;
  /** Black-Scholes fair value, for comparison against midPrice. */
  theoPrice?: number | null;
  liquidityScore?: number | null;
  /** Bid/ask spread as a multiple of mid price; higher is worse. */
  spreadPenalty?: number | null;
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
    { ticker: 'UNH', name: 'UnitedHealth Group', sectorId: 'health', currentPrice: 270.00, dayChangePercent: -0.2 },
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

/** Extra tickers (from API, not in mock) mapped to existing sectors. Order = priority for capping. */
export const EXTRA_TICKERS_ORDER: string[] = [
  'AMD', 'INTC', 'QCOM', 'ORCL', 'ADBE', 'ABBV', 'GILD', 'AMGN', 'GS', 'MS', 'AXP',
  'NKE', 'SBUX', 'MCD', 'GE', 'HON', 'UPS', 'FCX', 'AA', 'DUK', 'COP', 'SLB',
];

/**
 * Cap on extra tickers shown. Derived from the list above so the two cannot drift:
 * a hardcoded 20 against 22 entries silently dropped COP and SLB from the UI.
 */
export const EXTRA_TICKERS_CAP = EXTRA_TICKERS_ORDER.length;

export const EXTRA_TICKER_SECTORS: Record<string, string> = {
  AMD: 'technology', INTC: 'technology', QCOM: 'technology', ORCL: 'technology', ADBE: 'technology',
  ABBV: 'health', GILD: 'health', AMGN: 'health',
  GS: 'finance', MS: 'finance', AXP: 'finance',
  NKE: 'consumer', SBUX: 'consumer', MCD: 'consumer',
  GE: 'industrials', HON: 'industrials', UPS: 'industrials',
  FCX: 'materials', AA: 'materials',
  DUK: 'utilities',
  COP: 'energy', SLB: 'energy',
};

/** Full company names for tickers (used when API returns ticker as name). */
export const TICKER_FULL_NAMES: Record<string, string> = {
  AAPL: 'Apple Inc.',
  SPY: 'SPDR S&P 500 ETF',
  NVDA: 'NVIDIA Corp.',
  TSLA: 'Tesla Inc.',
  AMD: 'Advanced Micro Devices',
  INTC: 'Intel Corp.',
  QCOM: 'Qualcomm Inc.',
  ORCL: 'Oracle Corp.',
  ADBE: 'Adobe Inc.',
  ABBV: 'AbbVie Inc.',
  GILD: 'Gilead Sciences',
  AMGN: 'Amgen Inc.',
  GS: 'Goldman Sachs Group',
  MS: 'Morgan Stanley',
  AXP: 'American Express',
  NKE: 'Nike Inc.',
  SBUX: 'Starbucks Corp.',
  MCD: "McDonald's Corp.",
  GE: 'GE Aerospace',
  HON: 'Honeywell International',
  UPS: 'United Parcel Service',
  FCX: 'Freeport-McMoRan Inc.',
  AA: 'Alcoa Corp.',
  DUK: 'Duke Energy',
  COP: 'ConocoPhillips',
  SLB: 'SLB (Schlumberger)',
};

/** Display name for a ticker: from mock stock, then TICKER_FULL_NAMES, else ticker. */
export function getTickerFullName(ticker: string): string {
  const upper = ticker.toUpperCase();
  const mock = getStockByTicker(ticker);
  if (mock?.name && mock.name !== upper && mock.name !== ticker) return mock.name;
  return TICKER_FULL_NAMES[upper] ?? ticker;
}

// Flatten for lookup by ticker
export function getStockByTicker(ticker: string): Stock | undefined {
  const upper = ticker.toUpperCase();
  for (const stocks of Object.values(MOCK_STOCKS_BY_SECTOR)) {
    const found = stocks.find((s) => s.ticker.toUpperCase() === upper);
    if (found) return found;
  }
  return undefined;
}

// NOTE: generateMockPrices() and generateMockOHLC() used to live here. They produced a
// `Math.random()` walk that the chart rendered with nothing marking it as synthetic, so
// a visitor with the backend down saw a plausible-looking price history that was pure
// noise. Price data now has no fallback: unavailable renders an empty state instead.

// Mock options per stock
function mockOpt(t: string, type: 'call' | 'put', strike: number, price: number, bid: number, midPrice: number, score: number, iv: number, exp = '2026-03-21T21:00:00+00:00'): StockOption {
  const sym = type === 'call' ? `${t}260321C${String(strike * 1000).padStart(8, '0')}` : `${t}260321P${String(strike * 1000).padStart(8, '0')}`;
  const conf = Math.round(Math.max(0, Math.min(100, 50 + score / 2)));
  return {
    ticker: t,
    type,
    expiration: exp,
    contractSymbol: sym,
    strike,
    price,
    bid,
    midPrice,
    score,
    impliedVolatility: iv,
    optionPrice: midPrice,
    confidence: conf,
  };
}

export const MOCK_STOCK_OPTIONS: Record<string, StockOption[]> = {
  AAPL: [
    mockOpt('AAPL', 'call', 190, 8.55, 8.50, 8.50, 56, 0.22),
    mockOpt('AAPL', 'call', 195, 5.25, 5.20, 5.20, 43, 0.20),
    mockOpt('AAPL', 'put', 185, 4.12, 4.10, 4.10, 44, 0.21),
    mockOpt('AAPL', 'put', 190, 6.85, 6.80, 6.80, 23, 0.19),
  ],
  MSFT: [
    mockOpt('MSFT', 'call', 410, 12.05, 12.00, 12.00, 64, 0.18),
    mockOpt('MSFT', 'put', 400, 9.52, 9.50, 9.50, 36, 0.17),
  ],
};

export function getOptionsForTicker(ticker: string): StockOption[] {
  const key = ticker.toUpperCase();
  return MOCK_STOCK_OPTIONS[key] ?? [
    mockOpt(ticker, 'call', 100, 3.55, 3.50, 3.50, 0, 0.25),
    mockOpt(ticker, 'put', 95, 2.82, 2.80, 2.80, -10, 0.24),
  ];
}
