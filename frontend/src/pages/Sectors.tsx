import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/Card';
import { Skeleton } from '../components/Skeleton';
import { fetchSectors, fetchTickersWithData } from '../services/api';
import { MOCK_STOCKS_BY_SECTOR, getStockByTicker, EXTRA_TICKERS_CAP, EXTRA_TICKER_SECTORS, EXTRA_TICKERS_ORDER } from '../mock/stocks';
import type { Sector } from '../mock/sectors';

export function Sectors() {
  const [sectors, setSectors] = useState<Sector[] | null>(null);

  useEffect(() => {
    Promise.all([fetchSectors(), fetchTickersWithData()]).then(([allSectors, tickersWithData]) => {
      if (tickersWithData != null && tickersWithData.length > 0) {
        const set = new Set(tickersWithData.map((t) => t.toUpperCase()));
        const apiOnly = tickersWithData.filter((t) => !getStockByTicker(t));
        const inMap = apiOnly.filter((t) => EXTRA_TICKER_SECTORS[t.toUpperCase()]);
        const ordered = [...inMap].sort((a, b) => {
          const i = EXTRA_TICKERS_ORDER.indexOf(a.toUpperCase());
          const j = EXTRA_TICKERS_ORDER.indexOf(b.toUpperCase());
          if (i < 0 && j < 0) return 0;
          if (i < 0) return 1;
          if (j < 0) return -1;
          return i - j;
        });
        const cappedExtra = ordered.slice(0, EXTRA_TICKERS_CAP);
        const filtered: Sector[] = [];
        for (const sector of allSectors) {
          const mockStocks = MOCK_STOCKS_BY_SECTOR[sector.id] ?? [];
          const withData = mockStocks.filter((s) => set.has(s.ticker.toUpperCase()));
          const extraInSector = cappedExtra.filter((t) => (EXTRA_TICKER_SECTORS[t.toUpperCase()] ?? '') === sector.id);
          const total = withData.length + extraInSector.length;
          if (total > 0) {
            filtered.push({ ...sector, stockCount: total });
          }
        }
        setSectors(filtered);
      } else {
        setSectors(allSectors);
      }
    });
  }, []);

  if (sectors === null) {
    return (
      <div className="space-y-4">
        <Card>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-zinc-100">Sectors of Stocks</h1>
      <div className="overflow-auto max-h-[75vh] scrollable pr-1">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 pb-4">
          {sectors.map((sector) => (
            <Link
              key={sector.id}
              to={`/sectors/${sector.id}`}
              className="group rounded-lg border border-zinc-800 bg-zinc-900/80 p-4 transition-all hover:border-zinc-700 hover:bg-zinc-800/50"
            >
              <div className="text-2xl mb-2">{sector.icon}</div>
              <div className="font-medium text-zinc-100 group-hover:text-white transition-colors">
                {sector.name}
              </div>
              <div className="text-sm text-zinc-500">
                {sector.stockCount} stock{sector.stockCount !== 1 ? 's' : ''}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
