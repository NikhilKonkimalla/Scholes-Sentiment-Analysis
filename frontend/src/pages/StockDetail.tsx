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
  fetchStockAiSummary,
  fetchStockOptions,
} from '../services/api';
import { MOCK_SECTORS } from '../mock/sectors';
import type { Stock, PricePoint, StockOption, OHLCPoint } from '../mock/stocks';

export function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [stock, setStock] = useState<Stock | null | undefined>(undefined);
  const [prices, setPrices] = useState<PricePoint[] | null>(null);
  const [ohlc, setOhlc] = useState<OHLCPoint[] | null>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [options, setOptions] = useState<StockOption[] | null>(null);
  const [chartFormat, setChartFormat] = useState<'line' | 'candlestick'>('line');
  const candleContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);

  useEffect(() => {
    if (!ticker) return;
    Promise.all([
      fetchStock(ticker).then(setStock),
      fetchStockPrices(ticker).then(setPrices),
      fetchStockOHLC(ticker).then(setOhlc),
      fetchStockAiSummary(ticker).then(setAiSummary),
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
  const loading = stock === undefined || prices === null || aiSummary === null || options === null;

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
              <span className="text-zinc-300">${stock.currentPrice.toFixed(2)}</span>
              <Badge variant={stock.dayChangePercent >= 0 ? 'green' : 'red'}>
                {stock.dayChangePercent >= 0 ? '+' : ''}{stock.dayChangePercent.toFixed(2)}%
              </Badge>
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
              {chartFormat === 'line' ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={prices ?? []} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#71717a', fontSize: 10 }}
                      tickFormatter={(v) => v.slice(5)}
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

          <Card title="AI Evaluation">
            <div className="flex items-start gap-2">
              <Badge variant="neutral" className="shrink-0">Generated</Badge>
              <p className="text-sm text-zinc-300 leading-relaxed">{aiSummary}</p>
            </div>
          </Card>
        </div>
      )}

      <Card title="Options">
        {options === null ? (
          <div className="overflow-auto max-h-64">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Strike $</th>
                  <th className="px-4 py-3">Option price</th>
                  <th className="px-4 py-3">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 4 }).map((_, i) => (
                  <TableRowSkeleton key={i} cols={4} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-auto max-h-64 scrollable rounded-lg border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 font-medium text-zinc-400">
                <tr>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Strike $</th>
                  <th className="px-4 py-3">Option price</th>
                  <th className="px-4 py-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {options.map((opt, i) => (
                  <tr key={i} className="transition-colors hover:bg-zinc-800/50">
                    <td className="px-4 py-3">
                      <Badge variant={opt.type === 'call' ? 'call' : 'put'}>
                        {opt.type.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">${opt.strike.toFixed(2)}</td>
                    <td className="px-4 py-3 text-zinc-300">${opt.optionPrice.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <Badge variant={opt.confidence >= 60 ? 'green' : opt.confidence >= 40 ? 'neutral' : 'red'}>
                        {opt.confidence}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
