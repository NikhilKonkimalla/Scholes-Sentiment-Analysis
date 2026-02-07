import { useEffect, useState } from 'react';
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
import { ArrowLeft } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { Breadcrumb } from '../components/Breadcrumb';
import { Skeleton, TableRowSkeleton } from '../components/Skeleton';
import {
  fetchStock,
  fetchStockPrices,
  fetchStockAiSummary,
  fetchStockOptions,
} from '../services/api';
import { MOCK_SECTORS } from '../mock/sectors';
import type { Stock, PricePoint, StockOption } from '../mock/stocks';

export function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [stock, setStock] = useState<Stock | null | undefined>(undefined);
  const [prices, setPrices] = useState<PricePoint[] | null>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [options, setOptions] = useState<StockOption[] | null>(null);

  useEffect(() => {
    if (!ticker) return;
    Promise.all([
      fetchStock(ticker).then(setStock),
      fetchStockPrices(ticker).then(setPrices),
      fetchStockAiSummary(ticker).then(setAiSummary),
      fetchStockOptions(ticker).then(setOptions),
    ]);
  }, [ticker]);

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
            <div className="h-56">
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
