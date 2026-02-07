/**
 * Per-ticker AI evaluation copy and related articles (mock).
 * Replace with backend response when /api/stocks/:ticker/ai-summary is available.
 */
export interface AiArticle {
  title: string;
  url: string;
}

export interface AiEvaluation {
  summary: string;
  articles: AiArticle[];
}

const DEFAULT_EVALUATION: AiEvaluation = {
  summary:
    'Based on recent volatility, earnings sentiment, and options flow, this name shows moderate bias over the next 30 days. Implied volatility is near the 20-day average. Risk/reward favors selective spreads over naked options.',
  articles: [
    { title: 'Yahoo Finance — Quote & News', url: 'https://finance.yahoo.com' },
    { title: 'Market news search', url: 'https://www.google.com/search?q=stock+market+news' },
  ],
};

export const MOCK_AI_EVALUATIONS: Record<string, AiEvaluation> = {
  AAPL: {
    summary:
      'Apple remains a quality hold with strong services growth and capital return. Options flow suggests put hedging; IV percentile is near median. Near-term catalysts: product cycle and China demand. Given current sentiment and rich call premium, we favor put-side and defined-risk strategies over naked calls.',
    articles: [
      { title: 'Apple stock quote & news', url: 'https://finance.yahoo.com/quote/AAPL' },
      { title: 'Apple Inc. — Reuters', url: 'https://www.reuters.com/markets/companies/AAPL.O/' },
    ],
  },
  MSFT: {
    summary:
      'Microsoft’s cloud and AI narrative is key; IV is often elevated around earnings. Given current options sentiment we favor put spreads for downside hedge and defined-risk structures. Watch Azure growth and guidance.',
    articles: [
      { title: 'Microsoft stock quote & news', url: 'https://finance.yahoo.com/quote/MSFT' },
      { title: 'Microsoft Corp. — Reuters', url: 'https://www.reuters.com/markets/companies/MSFT.O/' },
    ],
  },
  GOOGL: {
    summary:
      'Alphabet benefits from search resilience and cloud expansion; regulatory overhang keeps volatility elevated. Options sentiment mixed. Favor defined-risk structures; avoid large single-leg earnings plays given IV crush risk.',
    articles: [
      { title: 'Alphabet stock quote & news', url: 'https://finance.yahoo.com/quote/GOOGL' },
      { title: 'Alphabet Inc. — Reuters', url: 'https://www.reuters.com/markets/companies/GOOGL.O/' },
    ],
  },
  AMZN: {
    summary:
      'Amazon’s retail and AWS mix drives both growth and volatility. Options flow often reflects event-driven demand. IV tends to spike into earnings; selling premium in quiet periods or using spreads can improve risk/reward.',
    articles: [
      { title: 'Amazon stock quote & news', url: 'https://finance.yahoo.com/quote/AMZN' },
      { title: 'Amazon.com Inc. — Reuters', url: 'https://www.reuters.com/markets/companies/AMZN.O/' },
    ],
  },
  NVDA: {
    summary:
      'NVIDIA’s AI narrative keeps momentum and IV elevated. Put skew can offer relative value for hedges; we favor put-side and spreads over chasing calls. Monitor data-center and gaming mix.',
    articles: [
      { title: 'NVIDIA stock quote & news', url: 'https://finance.yahoo.com/quote/NVDA' },
      { title: 'NVIDIA Corp. — Reuters', url: 'https://www.reuters.com/markets/companies/NVDA.O/' },
    ],
  },
  META: {
    summary:
      'Meta’s ad and metaverse story drives sentiment; options skew has been mixed. Regulatory and engagement metrics are key. Consider balanced spreads; IV can spike around product and policy headlines.',
    articles: [
      { title: 'Meta stock quote & news', url: 'https://finance.yahoo.com/quote/META' },
      { title: 'Meta Platforms — Reuters', url: 'https://www.reuters.com/markets/companies/META.O/' },
    ],
  },
  SPY: {
    summary:
      'SPY options are liquid and reflect broad market sentiment and volatility. VIX term structure and skew matter more than single-name catalysts. Favor index put spreads for tail hedge or selling premium in elevated VIX environments.',
    articles: [
      { title: 'SPDR S&P 500 ETF quote & news', url: 'https://finance.yahoo.com/quote/SPY' },
      { title: 'S&P 500 index news', url: 'https://www.reuters.com/markets/us/' },
    ],
  },
  JPM: {
    summary:
      'JPMorgan’s scale and rates sensitivity drive both earnings and options flow. Bank-sector sentiment ties to Fed and credit. IV often rises into earnings; defined-risk structures preferred. Watch net interest income and guidance.',
    articles: [
      { title: 'JPMorgan Chase stock quote & news', url: 'https://finance.yahoo.com/quote/JPM' },
      { title: 'JPMorgan Chase — Reuters', url: 'https://www.reuters.com/markets/companies/JPM.N/' },
    ],
  },
  TSLA: {
    summary:
      'Tesla options are highly volatile and sentiment-driven; flow is often directional. IV is usually elevated; earnings and delivery numbers cause large moves. Favor spreads over naked options; avoid outsized single-leg positions.',
    articles: [
      { title: 'Tesla stock quote & news', url: 'https://finance.yahoo.com/quote/TSLA' },
      { title: 'Tesla Inc. — Reuters', url: 'https://www.reuters.com/markets/companies/TSLA.O/' },
    ],
  },
  XOM: {
    summary:
      'Exxon Mobil options reflect oil and macro sentiment. Dividend and buybacks support downside; IV can spike on crude moves. Consider put spreads for hedge or selling premium when IV is high relative to history.',
    articles: [
      { title: 'Exxon Mobil stock quote & news', url: 'https://finance.yahoo.com/quote/XOM' },
      { title: 'Exxon Mobil — Reuters', url: 'https://www.reuters.com/markets/companies/XOM.N/' },
    ],
  },
  JNJ: {
    summary:
      'Johnson & Johnson’s diversified healthcare profile and spin-off story drive options interest. IV is typically moderate. Litigation and pipeline updates can move the stock; defined-risk structures recommended around events.',
    articles: [
      { title: 'Johnson & Johnson stock quote & news', url: 'https://finance.yahoo.com/quote/JNJ' },
      { title: 'Johnson & Johnson — Reuters', url: 'https://www.reuters.com/markets/companies/JNJ.N/' },
    ],
  },
  UNH: {
    summary:
      'UnitedHealth’s managed-care and Optum narrative keeps institutional interest high. Options flow is often balanced; IV rises around earnings and policy news. Favor spreads; watch Medicare and policy headlines.',
    articles: [
      { title: 'UnitedHealth stock quote & news', url: 'https://finance.yahoo.com/quote/UNH' },
      { title: 'UnitedHealth — Reuters', url: 'https://www.reuters.com/markets/companies/UNH.N/' },
    ],
  },
  PFE: {
    summary:
      'Pfizer options reflect pharma and pipeline sentiment; post-COVID demand and patent cliffs are in focus. IV can spike around trial and approval news. Consider spreads; avoid large single-leg plays into binary events.',
    articles: [
      { title: 'Pfizer stock quote & news', url: 'https://finance.yahoo.com/quote/PFE' },
      { title: 'Pfizer Inc. — Reuters', url: 'https://www.reuters.com/markets/companies/PFE.N/' },
    ],
  },
  BAC: {
    summary:
      'Bank of America options are sensitive to rates and credit. Flow often reflects macro and earnings bets. IV rises into earnings; defined-risk structures preferred. Watch net interest income and loan growth.',
    articles: [
      { title: 'Bank of America stock quote & news', url: 'https://finance.yahoo.com/quote/BAC' },
      { title: 'Bank of America — Reuters', url: 'https://www.reuters.com/markets/companies/BAC.N/' },
    ],
  },
  V: {
    summary:
      'Visa’s payments narrative and volume growth support sentiment. Options IV is usually moderate; spikes occur around earnings and regulatory updates. Favor spreads; monitor cross-border and digital volume trends.',
    articles: [
      { title: 'Visa stock quote & news', url: 'https://finance.yahoo.com/quote/V' },
      { title: 'Visa Inc. — Reuters', url: 'https://www.reuters.com/markets/companies/V.N/' },
    ],
  },
  CVX: {
    summary:
      'Chevron options reflect oil and gas sentiment and dividend appeal. IV can rise with crude volatility. Put spreads for hedge or premium selling in elevated IV environments; watch capex and production updates.',
    articles: [
      { title: 'Chevron stock quote & news', url: 'https://finance.yahoo.com/quote/CVX' },
      { title: 'Chevron — Reuters', url: 'https://www.reuters.com/markets/companies/CVX.N/' },
    ],
  },
  HD: {
    summary:
      'Home Depot options track housing and consumer spending. IV often rises into earnings; same-store sales and guidance drive moves. Favor defined-risk structures; watch housing data and management commentary.',
    articles: [
      { title: 'Home Depot stock quote & news', url: 'https://finance.yahoo.com/quote/HD' },
      { title: 'Home Depot — Reuters', url: 'https://www.reuters.com/markets/companies/HD.N/' },
    ],
  },
  CAT: {
    summary:
      'Caterpillar options reflect cyclical and construction sentiment. Global growth and commodity demand drive flow. IV can spike around earnings and macro data. Consider spreads; monitor backlog and geographic mix.',
    articles: [
      { title: 'Caterpillar stock quote & news', url: 'https://finance.yahoo.com/quote/CAT' },
      { title: 'Caterpillar — Reuters', url: 'https://www.reuters.com/markets/companies/CAT.N/' },
    ],
  },
  BA: {
    summary:
      'Boeing options are event-driven; safety, delivery, and defense news move IV. Flow is often skewed. Avoid large naked positions; use spreads and size small. Watch delivery rates and regulatory updates.',
    articles: [
      { title: 'Boeing stock quote & news', url: 'https://finance.yahoo.com/quote/BA' },
      { title: 'Boeing — Reuters', url: 'https://www.reuters.com/markets/companies/BA.N/' },
    ],
  },
  NEE: {
    summary:
      'NextEra Energy options reflect utilities and clean-energy sentiment. IV is typically moderate; regulatory and rate updates can move the stock. Favor spreads; watch capex and renewable capacity guidance.',
    articles: [
      { title: 'NextEra Energy stock quote & news', url: 'https://finance.yahoo.com/quote/NEE' },
      { title: 'NextEra Energy — Reuters', url: 'https://www.reuters.com/markets/companies/NEE.N/' },
    ],
  },
  LIN: {
    summary:
      'Linde’s industrial-gas and ESG story supports steady options interest. IV is usually moderate. Defined-risk structures preferred; watch volume and pricing trends and capital allocation updates.',
    articles: [
      { title: 'Linde stock quote & news', url: 'https://finance.yahoo.com/quote/LIN' },
      { title: 'Linde plc — Reuters', url: 'https://www.reuters.com/markets/companies/LIN.N/' },
    ],
  },
};

export function getAiEvaluation(ticker: string): AiEvaluation {
  const key = ticker.toUpperCase();
  const eval_ = MOCK_AI_EVALUATIONS[key];
  if (eval_) return eval_;
  return {
    ...DEFAULT_EVALUATION,
    summary: DEFAULT_EVALUATION.summary.replace('this name', ticker),
    articles: [
      { title: `${ticker} quote & news`, url: `https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}` },
      { title: 'Market news', url: 'https://www.google.com/search?q=' + encodeURIComponent(ticker + ' stock news') },
    ],
  };
}
