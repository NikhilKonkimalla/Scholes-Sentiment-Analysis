import { useEffect, useState, useRef } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { createChart } from 'lightweight-charts';
import { ArrowLeft } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { Breadcrumb } from '../components/Breadcrumb';
import { Skeleton, TableRowSkeleton } from '../components/Skeleton';
import {
  fetchStock,
  fetchStockPrices,
  fetchStockOHLC,
  fetchStockAiEvaluation,
  fetchStockOptions,
  checkBackendHealth,
} from '../services/api';
import { MOCK_SECTORS } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';
import type { AiEvaluation } from '../mock/aiEvaluations';

/**
 * Human-readable explanation for a risk-flagged contract, used as the badge tooltip.
 * Mirrors the conditions in scoring.py: wide spread, thin liquidity, or a theoretical
 * price too close to zero to derive a meaningful mispricing from.
 */
function riskReason(opt: StockOption): string {
  const reasons: string[] = [];
  if (opt.volume != null && opt.openInterest != null && opt.volume + opt.openInterest < 10) {
    reasons.push(`thin liquidity (volume ${opt.volume}, open interest ${opt.openInterest})`);
  }
  // A missing quote is not a wide quote. scoring.py charges both the maximum spread
  // penalty (5.0), so reporting "500% of mid" for a contract nobody is quoting would
  // be plainly false — distinguish the two.
  if (opt.ask != null && (opt.bid <= 0 || opt.ask <= 0)) {
    reasons.push('no bid/ask quote available');
  } else if (opt.spreadPenalty != null && opt.spreadPenalty > 1) {
    reasons.push(`wide bid/ask spread (${Math.round(opt.spreadPenalty * 100)}% of mid)`);
  }
  if (opt.theoPrice != null && opt.theoPrice < 0.05) {
    reasons.push('no usable theoretical price');
  }
  return reasons.length
    ? `Flagged: ${reasons.join('; ')}`
    : 'Flagged: wide spread, thin liquidity, or no usable theoretical price';
}

export function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [stock, setStock] = useState<Stock | null | undefined>(undefined);
  const [prices, setPrices] = useState<PricePoint[] | null>(null);
  const [ohlc, setOhlc] = useState<OHLCPoint[] | null>(null);
  const [aiEvaluation, setAiEvaluation] = useState<AiEvaluation | null>(null);
  const [options, setOptions] = useState<StockOption[] | null>(null);
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);
  const [chartFormat, setChartFormat] = useState<'line' | 'candlestick'>('line');
  const candleContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);

  useEffect(() => {
    if (!ticker) return;
    checkBackendHealth().then(setBackendAvailable);
    Promise.all([
      fetchStock(ticker).then(setStock),
      fetchStockPrices(ticker).then(setPrices),
      fetchStockOHLC(ticker).then(setOhlc),
      fetchStockAiEvaluation(ticker).then(setAiEvaluation),
      fetchStockOptions(ticker).then(setOptions),
    ]);
  }, [ticker]);

  // Candlestick chart: create/update when format is candlestick and OHLC is loaded
  useEffect(() => {
    if (chartFormat !== 'candlestick' || !ohlc?.length || !candleContainerRef.current) {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
      return;
    }
    const container = candleContainerRef.current;
    const chart = createChart(container, {
      layout: { background: { color: '#18181b' }, textColor: '#71717a' },
      grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
      width: container.clientWidth,
      height: 224,
      rightPriceScale: { borderColor: '#27272a', scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: '#27272a', timeVisible: true, secondsVisible: false },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: true,
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
    });
    candleSeries.setData(
      ohlc.map((d) => ({
        time: d.date as string,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );
    chartRef.current = chart;
    const handleResize = () => {
      if (chartRef.current && candleContainerRef.current)
        chartRef.current.applyOptions({ width: candleContainerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [chartFormat, ohlc]);

  const sector = stock ? MOCK_SECTORS.find((s) => s.id === stock.sectorId) : null;
  const loading = stock === undefined || prices === null || aiEvaluation === null || options === null;

  if (!ticker) {
    return (
      <div className="space-y-4">
        <p className="text-zinc-400">No ticker specified.</p>
        <Link to="/sectors" className="text-emerald-500 hover:underline">Back to Sectors</Link>
      </div>
    );
  }

  if (stock === null) {
    return (
      <div className="space-y-4">
        <p className="text-zinc-400">Stock not found.</p>
        <Link to="/sectors" className="text-emerald-500 hover:underline">Back to Sectors</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { label: 'Sectors', href: '/sectors' },
          ...(sector ? [{ label: sector.name, href: `/sectors/${sector.id}` }] : []),
          { label: ticker },
        ]}
      />

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700/50 hover:text-zinc-100 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-zinc-100">{ticker}</h1>
          {stock && (
            <>
              {sector && <Badge variant="neutral">{sector.name}</Badge>}
              {Number(stock.currentPrice ?? 0) > 0 ? (
                <>
                  <span className="text-zinc-300">${Number(stock.currentPrice).toFixed(2)}</span>
                  <Badge variant={(stock.dayChangePercent ?? 0) >= 0 ? 'green' : 'red'}>
                    {(stock.dayChangePercent ?? 0) >= 0 ? '+' : ''}
                    {Number(stock.dayChangePercent ?? 0).toFixed(2)}%
                  </Badge>
                </>
              ) : (
                /* 0 means the quote endpoint was unreachable. Showing "$0.00" would
                   read as a real price, so say plainly that we do not have one. */
                <span className="text-sm text-zinc-500" title="Live quote unavailable">
                  price unavailable
                </span>
              )}
            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card title="Price (last 30 days)">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-zinc-400">Format:</span>
              <button
                type="button"
                onClick={() => setChartFormat('line')}
                className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                  chartFormat === 'line'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600 hover:text-zinc-200'
                }`}
              >
                Line
              </button>
              <button
                type="button"
                onClick={() => setChartFormat('candlestick')}
                className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                  chartFormat === 'candlestick'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600 hover:text-zinc-200'
                }`}
              >
                Candlestick
              </button>
            </div>
            <div className="h-56">
              {!prices?.length ? (
                <div className="flex h-full flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-zinc-700 text-center">
                  <p className="text-sm text-zinc-400">Price history unavailable</p>
                  <p className="text-xs text-zinc-500">
                    The API server is not reachable, so there is no market data to chart.
                  </p>
                </div>
              ) : chartFormat === 'line' ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={prices ?? []} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#71717a', fontSize: 10 }}
                      tickFormatter={(v) => (v && typeof v === 'string' ? v.slice(5) : '')}
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      tick={{ fill: '#71717a', fontSize: 10 }}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#18181b',
                        border: '1px solid #27272a',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: '#a1a1aa' }}
                      formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
                      labelFormatter={(label) => label}
                    />
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div ref={candleContainerRef} className="w-full h-full" />
              )}
            </div>
          </Card>

          <Card title="News Sentiment">
            <div className="space-y-3">
              {aiEvaluation?.source === 'mock' && (
                <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                  Live sentiment unavailable — the API server is not reachable. Nothing
                  shown here is an analysis of this stock.
                </div>
              )}
              {aiEvaluation?.source === 'live' && aiEvaluation.available === false && (
                <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-xs text-zinc-400">
                  {aiEvaluation.reason || 'No recent headlines found for this ticker.'}
                </div>
              )}

              {aiEvaluation?.summary ? (
                <p className="text-sm text-zinc-300 leading-relaxed">{aiEvaluation.summary}</p>
              ) : null}

              {aiEvaluation?.source === 'live' && aiEvaluation.available && (
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={(aiEvaluation.sentimentMean ?? 0) >= 0 ? 'green' : 'red'}>
                    mean {(aiEvaluation.sentimentMean ?? 0) >= 0 ? '+' : ''}
                    {Number(aiEvaluation.sentimentMean ?? 0).toFixed(2)}
                  </Badge>
                  <Badge variant="green">{aiEvaluation.positive ?? 0} positive</Badge>
                  <Badge variant="red">{aiEvaluation.negative ?? 0} negative</Badge>
                  <Badge variant="neutral">{aiEvaluation.neutral ?? 0} neutral</Badge>
                  {aiEvaluation.model && (
                    <span className="text-xs text-zinc-500">
                      scored by {aiEvaluation.model.toUpperCase()}
                    </span>
                  )}
                </div>
              )}

              {aiEvaluation?.articles?.length ? (
                <div className="border-t border-zinc-800 pt-3">
                  <p className="text-xs font-medium text-zinc-400 mb-2">
                    {aiEvaluation.source === 'live' ? 'Headlines scored' : 'Related articles'}
                  </p>
                  <ul className="space-y-1.5">
                    {aiEvaluation.articles.map((a, i) => (
                      <li key={i} className="flex items-start gap-2">
                        {typeof a.score === 'number' && (
                          <span
                            className={`mt-0.5 shrink-0 font-mono text-xs ${
                              a.score > 0.05
                                ? 'text-emerald-400'
                                : a.score < -0.05
                                ? 'text-rose-400'
                                : 'text-zinc-500'
                            }`}
                          >
                            {a.score >= 0 ? '+' : ''}
                            {a.score.toFixed(2)}
                          </span>
                        )}
                        {a.url ? (
                          <a
                            href={a.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-emerald-400 hover:text-emerald-300 hover:underline"
                          >
                            {a.title}
                          </a>
                        ) : (
                          <span className="text-sm text-zinc-300">{a.title}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </Card>
        </div>
      )}

      <Card title="Options">
        {backendAvailable === false && (
          <div className="mb-3 rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            Using mock data. Start the API server for real confidence scores from{' '}
            <code className="rounded bg-zinc-800 px-1">output_multi_ticker.csv</code>:{' '}
            <code className="rounded bg-zinc-800 px-1">python api_server.py</code>
          </div>
        )}
        {options === null ? (
          <div className="overflow-auto max-h-64">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead className="border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-3 py-3">Ticker</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Expiration</th>
                  <th className="px-3 py-3">Strike</th>
                  <th className="px-3 py-3">Price</th>
                  <th className="px-3 py-3">Bid</th>
                  <th className="px-3 py-3">Mid</th>
                  <th className="px-3 py-3">Recommendation</th>
                  <th className="px-3 py-3">Volatility</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 4 }).map((_, i) => (
                  <TableRowSkeleton key={i} cols={9} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-auto max-h-64 scrollable rounded-lg border border-zinc-800">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 font-medium text-zinc-400">
                <tr>
                  <th className="px-3 py-3">Ticker</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Expiration</th>
                  <th className="px-3 py-3">Strike</th>
                  <th className="px-3 py-3">Price</th>
                  <th className="px-3 py-3">Bid</th>
                  <th className="px-3 py-3">Mid</th>
                  <th className="px-3 py-3">Recommendation</th>
                  <th className="px-3 py-3">Volatility</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {options.map((opt, i) => {
                  const mid = opt.optionPrice ?? opt.midPrice ?? opt.price ?? 0;
                  const conf = opt.confidence ?? 50;
                  const iv = opt.impliedVolatility ?? 0;
                  const recommendation = conf >= 60 ? 'Buy' : conf >= 40 ? 'Neutral' : 'Avoid';
                  return (
                    <tr key={i} className="transition-colors hover:bg-zinc-800/50">
                      <td className="px-3 py-2 font-medium text-zinc-200">{opt.ticker}</td>
                      <td className="px-3 py-2">
                        <Badge variant={opt.type === 'call' ? 'call' : 'put'}>
                          {opt.type.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-zinc-400 text-xs">{opt.expiration ? String(opt.expiration).slice(0, 10) : '—'}</td>
                      <td className="px-3 py-2 text-zinc-300">${Number(opt.strike).toFixed(2)}</td>
                      <td className="px-3 py-2 text-zinc-300">${Number(opt.price ?? opt.midPrice ?? mid).toFixed(2)}</td>
                      <td className="px-3 py-2 text-zinc-300">${Number(opt.bid ?? 0).toFixed(2)}</td>
                      <td className="px-3 py-2 text-zinc-300">${Number(mid).toFixed(2)}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span title={conf >= 60 ? 'Recommended to buy' : conf >= 40 ? 'Neutral' : 'Not recommended'}>
                            <Badge variant={conf >= 60 ? 'green' : conf >= 40 ? 'yellow' : 'red'}>
                              {recommendation} ({conf})
                            </Badge>
                          </span>
                          {opt.riskFlag === true && (
                            <span title={riskReason(opt)}>
                              <Badge variant="yellow">⚠ risk</Badge>
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-zinc-400">{(iv * 100).toFixed(2)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
