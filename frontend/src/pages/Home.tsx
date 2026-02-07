import { useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { IntroScreen } from '../components/IntroScreen';
import { MOCK_ACTIVE_OPTIONS, type ActiveOption } from '../mock/options';
import {
  Search,
  ArrowUpDown,
  TrendingUp,
  Zap,
  FileText,
  Brain,
  Percent,
  Shield,
} from 'lucide-react';

type SortKey = 'ticker' | 'strikePrice' | 'boughtAtPrice';

const features = [
  {
    icon: TrendingUp,
    title: 'Black–Scholes Scoring',
    description:
      'Rigorous options valuation using the Black–Scholes model. Compare theoretical fair value against market price to spot mispricings.',
  },
  {
    icon: Zap,
    title: 'News Sentiment',
    description:
      'Sentiment scoring from news headlines. Understand market mood around each ticker before you trade.',
  },
  {
    icon: Percent,
    title: 'Opportunity Score',
    description:
      'Combined score weighing volatility, sentiment, and value. Focus on the highest-conviction opportunities.',
  },
  {
    icon: Brain,
    title: 'Multi-Ticker Analysis',
    description:
      'Analyze dozens of tickers at once. Sector-level views help you compare opportunities across the market.',
  },
  {
    icon: FileText,
    title: 'Historical Data',
    description:
      'Backed by real news and options data. Filter and sort to find the setups that match your strategy.',
  },
  {
    icon: Shield,
    title: 'Transparent Methodology',
    description:
      'Clear scoring logic. No black boxes—understand exactly how each opportunity is ranked.',
  },
];

export function Home() {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortKey>('ticker');

  const filteredAndSorted = useMemo(() => {
    let list = [...MOCK_ACTIVE_OPTIONS];
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (o) =>
          o.ticker.toLowerCase().includes(q) ||
          o.name.toLowerCase().includes(q)
      );
    }
    list.sort((a, b) => {
      if (sortBy === 'ticker') return a.ticker.localeCompare(b.ticker);
      if (sortBy === 'strikePrice') return a.strikePrice - b.strikePrice;
      return a.boughtAtPrice - b.boughtAtPrice;
    });
    return list;
  }, [search, sortBy]);

  return (
    <div className="pb-16">
      {/* First screen: intro + interactive options graph */}
      <IntroScreen />

      {/* Main content */}
      <div id="content" className="mx-auto max-w-6xl space-y-24 px-6 pt-16">
      {/* Feature Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 lg:gap-10">
        {features.map(({ icon: Icon, title, description }) => (
          <div key={title} className="space-y-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-gold text-gold">
              <Icon className="h-6 w-6" strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-bold text-zinc-100">{title}</h3>
            <p className="text-zinc-400 leading-relaxed">{description}</p>
          </div>
        ))}
      </section>

      {/* Opportunities Table */}
      <section id="opportunities" className="scroll-mt-24">
        <Card title="Active Options">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Filter by ticker or name..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800/50 py-2 pl-9 pr-3 text-zinc-100 placeholder-zinc-500 focus:border-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-600"
                />
              </div>
              <div className="flex items-center gap-2">
                <ArrowUpDown className="h-4 w-4 text-zinc-500" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortKey)}
                  className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-200 focus:border-zinc-600 focus:outline-none"
                >
                  <option value="ticker">Ticker</option>
                  <option value="strikePrice">Strike price</option>
                  <option value="boughtAtPrice">Bought at</option>
                </select>
              </div>
            </div>

            <div className="overflow-auto rounded-lg border border-zinc-800 max-h-[60vh] scrollable">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="sticky top-0 z-10 border-b border-zinc-800 bg-surface font-medium text-zinc-400">
                  <tr>
                    <th className="px-4 py-3">Ticker / Name</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Bought at</th>
                    <th className="px-4 py-3">Can buy for</th>
                    <th className="px-4 py-3">Strike</th>
                    <th className="px-4 py-3">P/L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {filteredAndSorted.map((row) => (
                    <OptionRow key={row.id} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      </section>
      </div>
    </div>
  );
}

function OptionRow({ row }: { row: ActiveOption }) {
  return (
    <tr className="transition-colors hover:bg-zinc-800/50">
      <td className="px-4 py-3">
        <div>
          <span className="font-medium text-zinc-100">{row.ticker}</span>
          <div className="text-xs text-zinc-500">{row.name}</div>
        </div>
      </td>
      <td className="px-4 py-3">
        <Badge variant={row.optionType === 'call' ? 'call' : 'put'}>
          {row.optionType.toUpperCase()}
        </Badge>
      </td>
      <td className="px-4 py-3 text-zinc-300">${row.boughtAtPrice.toFixed(2)}</td>
      <td className="px-4 py-3 text-zinc-300">${row.canBuyFor.toFixed(2)}</td>
      <td className="px-4 py-3 text-zinc-300">${row.strikePrice.toFixed(2)}</td>
      <td className="px-4 py-3">
        <Badge variant={row.favorable ? 'green' : 'red'}>
          {row.favorable ? 'Favorable' : 'Unfavorable'}
        </Badge>
      </td>
    </tr>
  );
}
