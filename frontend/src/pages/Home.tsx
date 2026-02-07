import { useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { MOCK_ACTIVE_OPTIONS, type ActiveOption } from '../mock/options';
import { Search, ArrowUpDown } from 'lucide-react';

type SortKey = 'ticker' | 'strikePrice' | 'boughtAtPrice';

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
    <div className="space-y-4">
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
              <thead className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 font-medium text-zinc-400">
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
