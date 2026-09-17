import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { IntroScreen } from '../components/IntroScreen';
import { TableRowSkeleton } from '../components/Skeleton';
import { fetchTopOptions } from '../services/api';
import type { StockOption } from '../mock/stocks';
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

type SortKey = 'score' | 'ticker' | 'strike' | 'expiration';

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

/**
 * Why a contract is risk-flagged. Mirrors the conditions in scoring.py: wide spread,
 * thin liquidity, or a theoretical price too near zero to derive a mispricing from.
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

export function Home() {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortKey>('score');
  const [hideRisky, setHideRisky] = useState(false);
  // undefined = loading, null = backend unavailable, array = real scored options
  const [options, setOptions] = useState<StockOption[] | null | undefined>(undefined);

  useEffect(() => {
    fetchTopOptions(50).then(setOptions);
  }, []);

  const flaggedCount = useMemo(
    () => (options ?? []).filter((o) => o.riskFlag === true).length,
    [options]
  );

  const filteredAndSorted = useMemo(() => {
    let list = [...(options ?? [])];
    if (hideRisky) list = list.filter((o) => o.riskFlag !== true);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((o) => o.ticker.toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      if (sortBy === 'ticker') return a.ticker.localeCompare(b.ticker);
      if (sortBy === 'strike') return a.strike - b.strike;
      if (sortBy === 'expiration') return String(a.expiration).localeCompare(String(b.expiration));
      return Math.abs(b.score) - Math.abs(a.score);
    });
    return list;
  }, [options, search, sortBy, hideRisky]);

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

        {/* Top opportunities, straight from the scored dataset */}
        <section id="opportunities" className="scroll-mt-24">
          <Card title="Top Opportunities">
            <div className="space-y-4">
              <p className="text-sm text-zinc-400">
                The highest-conviction contracts across every ticker in the dataset, ranked
                by absolute opportunity score. Not a portfolio and not a recommendation.
                Contracts marked <span className="text-amber-400">⚠ risk</span> are
                wide-spread or illiquid — a high score there may not be tradeable.
              </p>

              <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                  <input
                    type="text"
                    placeholder="Filter by ticker..."
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
                    <option value="score">Opportunity score</option>
                    <option value="ticker">Ticker</option>
                    <option value="strike">Strike price</option>
                    <option value="expiration">Expiration</option>
                  </select>
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-400">
                  <input
                    type="checkbox"
                    checked={hideRisky}
                    onChange={(e) => setHideRisky(e.target.checked)}
                    className="h-4 w-4 rounded border-zinc-600 bg-zinc-800 accent-emerald-500"
                  />
                  Hide flagged
                  {flaggedCount > 0 && <span className="text-zinc-500">({flaggedCount})</span>}
                </label>
              </div>

              {options === null ? (
                <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-6 text-center text-sm text-amber-200">
                  No options data could be loaded.
                  <div className="mt-1 text-xs text-amber-200/70">
                    Running locally? Start the backend with{' '}
                    <code className="rounded bg-zinc-800 px-1">python api_server.py</code>.
                  </div>
                </div>
              ) : (
                <div className="overflow-auto rounded-lg border border-zinc-800 max-h-[60vh] scrollable">
                  <table className="w-full min-w-[820px] text-left text-sm">
                    <thead className="sticky top-0 z-10 border-b border-zinc-800 bg-surface font-medium text-zinc-400">
                      <tr>
                        <th className="px-4 py-3">Ticker</th>
                        <th className="px-4 py-3">Type</th>
                        <th className="px-4 py-3">Expiration</th>
                        <th className="px-4 py-3">Strike</th>
                        <th className="px-4 py-3">Mid</th>
                        <th className="px-4 py-3">Liquidity</th>
                        <th className="px-4 py-3">Score</th>
                        <th className="px-4 py-3">Signal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800">
                      {options === undefined
                        ? Array.from({ length: 6 }).map((_, i) => <TableRowSkeleton key={i} cols={8} />)
                        : filteredAndSorted.map((row) => (
                            <OptionRow key={row.contractSymbol || `${row.ticker}-${row.strike}`} row={row} />
                          ))}
                    </tbody>
                  </table>
                  {options !== undefined && filteredAndSorted.length === 0 && (
                    <div className="px-4 py-6 text-center text-sm text-zinc-500">
                      No contracts match that filter.
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>
        </section>
      </div>
    </div>
  );
}

function OptionRow({ row }: { row: StockOption }) {
  const conf = row.confidence ?? 50;
  const signal = conf >= 60 ? 'Buy' : conf >= 40 ? 'Neutral' : 'Avoid';
  const liquidity =
    row.volume != null && row.openInterest != null ? row.volume + row.openInterest : null;

  return (
    <tr className={`transition-colors hover:bg-zinc-800/50 ${row.riskFlag === true ? 'bg-amber-500/[0.04]' : ''}`}>
      <td className="px-4 py-3">
        <Link to={`/stocks/${row.ticker}`} className="font-medium text-zinc-100 hover:text-gold">
          {row.ticker}
        </Link>
      </td>
      <td className="px-4 py-3">
        <Badge variant={row.type === 'call' ? 'call' : 'put'}>{row.type.toUpperCase()}</Badge>
      </td>
      <td className="px-4 py-3 text-xs text-zinc-400">
        {row.expiration ? String(row.expiration).slice(0, 10) : '—'}
      </td>
      <td className="px-4 py-3 text-zinc-300">${Number(row.strike).toFixed(2)}</td>
      <td className="px-4 py-3 text-zinc-300">${Number(row.midPrice ?? row.price ?? 0).toFixed(2)}</td>
      <td className="px-4 py-3 text-xs text-zinc-400">
        {liquidity == null ? (
          <span className="text-zinc-600" title="Liquidity data not in this snapshot">—</span>
        ) : (
          <span title={`volume ${row.volume}, open interest ${row.openInterest}`}>
            {liquidity.toLocaleString()}
          </span>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={`font-mono text-xs ${row.score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
          {row.score >= 0 ? '+' : ''}
          {Number(row.score).toFixed(1)}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={conf >= 60 ? 'green' : conf >= 40 ? 'yellow' : 'red'}>
            {signal} ({conf})
          </Badge>
          {row.riskFlag === true && (
            <span title={riskReason(row)}>
              <Badge variant="yellow">⚠ risk</Badge>
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}
