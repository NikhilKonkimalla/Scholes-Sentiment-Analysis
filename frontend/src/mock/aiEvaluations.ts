/**
 * Types for the per-ticker News Sentiment panel, plus the fallback used when the
 * backend is unreachable.
 *
 * This file previously held ~350 lines of hand-written per-ticker "evaluations" —
 * prose such as "we favor put-side and defined-risk strategies over naked calls" —
 * which the UI rendered next to a live price as though it were generated analysis.
 * No model and no analyst produced that text for those tickers, so it has been removed
 * outright rather than merely labelled.
 *
 * Real sentiment now comes from GET /api/stocks/:ticker/ai-summary, which scores
 * actual recent headlines with FinBERT (falling back to VADER) and reports only what
 * it measured.
 */

export interface AiArticle {
  title: string;
  url: string;
  /** Publisher, when the headline came from the live endpoint. */
  source?: string;
  /** Per-headline sentiment in [-1, 1], when live. */
  score?: number;
}

export interface AiEvaluation {
  summary: string;
  articles: AiArticle[];
  /** 'live' = computed from real scored headlines; 'mock' = offline fallback. */
  source?: 'live' | 'mock';
  /** False when there is no usable sentiment for this ticker. */
  available?: boolean;
  /** Why sentiment is unavailable, when it is. */
  reason?: string;
  sentimentMean?: number | null;
  sentimentStd?: number | null;
  headlineCount?: number;
  positive?: number;
  negative?: number;
  neutral?: number;
  /** Which model produced the scores: 'finbert' or 'vader'. */
  model?: string | null;
  generatedAt?: string;
}

/**
 * Offline fallback, used only when the API server cannot be reached.
 *
 * It deliberately carries no summary text. With no sentiment to report, the honest
 * thing to show is nothing at all plus a link the reader can follow themselves —
 * never invented commentary.
 */
export function getAiEvaluation(ticker: string): AiEvaluation {
  const symbol = ticker.toUpperCase();
  return {
    summary: '',
    source: 'mock',
    available: false,
    reason: 'Live sentiment unavailable — the API server is not reachable.',
    sentimentMean: null,
    sentimentStd: null,
    headlineCount: 0,
    positive: 0,
    negative: 0,
    neutral: 0,
    model: null,
    articles: [
      {
        title: `${symbol} news on Yahoo Finance`,
        url: `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/news`,
      },
    ],
  };
}
