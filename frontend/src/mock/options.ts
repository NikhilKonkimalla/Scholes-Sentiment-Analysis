export type OptionType = 'call' | 'put';

export interface ActiveOption {
  id: string;
  ticker: string;
  name: string;
  optionType: OptionType;
  boughtAtPrice: number;
  canBuyFor: number;
  strikePrice: number;
  favorable: boolean; // P/L-ish: true = green, false = red
}

export const MOCK_ACTIVE_OPTIONS: ActiveOption[] = [
  { id: '1', ticker: 'AAPL', name: 'Apple Inc.', optionType: 'call', boughtAtPrice: 185.20, canBuyFor: 192.50, strikePrice: 190, favorable: true },
  { id: '2', ticker: 'MSFT', name: 'Microsoft Corp.', optionType: 'put', boughtAtPrice: 378.00, canBuyFor: 415.30, strikePrice: 400, favorable: false },
  { id: '3', ticker: 'GOOGL', name: 'Alphabet Inc.', optionType: 'call', boughtAtPrice: 142.00, canBuyFor: 148.75, strikePrice: 145, favorable: true },
  { id: '4', ticker: 'AMZN', name: 'Amazon.com Inc.', optionType: 'call', boughtAtPrice: 178.50, canBuyFor: 182.00, strikePrice: 180, favorable: true },
  { id: '5', ticker: 'NVDA', name: 'NVIDIA Corp.', optionType: 'put', boughtAtPrice: 128.00, canBuyFor: 118.20, strikePrice: 120, favorable: true },
  { id: '6', ticker: 'META', name: 'Meta Platforms', optionType: 'call', boughtAtPrice: 485.00, canBuyFor: 472.00, strikePrice: 480, favorable: false },
  { id: '7', ticker: 'TSLA', name: 'Tesla Inc.', optionType: 'call', boughtAtPrice: 245.00, canBuyFor: 252.80, strikePrice: 250, favorable: true },
  { id: '8', ticker: 'SPY', name: 'SPDR S&P 500', optionType: 'put', boughtAtPrice: 585.00, canBuyFor: 592.40, strikePrice: 590, favorable: false },
  { id: '9', ticker: 'JPM', name: 'JPMorgan Chase', optionType: 'call', boughtAtPrice: 198.50, canBuyFor: 205.00, strikePrice: 200, favorable: true },
  { id: '10', ticker: 'V', name: 'Visa Inc.', optionType: 'call', boughtAtPrice: 278.00, canBuyFor: 275.20, strikePrice: 280, favorable: false },
];
