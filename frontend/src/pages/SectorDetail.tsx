import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '../components/Card';
import { Breadcrumb } from '../components/Breadcrumb';
import { TableRowSkeleton } from '../components/Skeleton';
import { fetchSectorStocks, fetchTickersWithData, fetchStock } from '../services/api';
import { MOCK_SECTORS } from '../mock/sectors';
import { getTickerFullName } from '../mock/stocks';
import type { Stock } from '../mock/stocks';

export function SectorDetail() {
  const { sectorId } = useParams<{ sectorId: string }>();
  const navigate = useNavigate();
  const [stocks, setStocks] = useState<Stock[] | null>(null);

  const sector = sectorId ? MOCK_SECTORS.find((s) => s.id === sectorId) : null;

  useEffect(() => {
    if (!sectorId) return;
    fetchTickersWithData().then((tickers) => {
      fetchSectorStocks(sectorId, tickers).then((baseStocks) => {
        // Enrich with live quotes (Yahoo) so sector list shows accurate prices
        Promise.all(baseStocks.map((s) => fetchStock(s.ticker))).then((results) => {
          setStocks(results.filter((x): x is Stock => x != null));
        });
      });
    });
  }, [sectorId]);

  if (!sectorId || !sector) {
    return (
      <div className="space-y-4">
        <p className="text-zinc-400">Sector not found.</p>
        <Link to="/sectors" className="text-emerald-500 hover:underline">Back to Sectors</Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Breadcrumb
        items={[
          { label: 'Sectors', href: '/sectors' },
          { label: sector.name },
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
        <h1 className="text-2xl font-semibold text-zinc-100">{sector.name}</h1>
      </div>

      <Card title="Stocks">
        {stocks === null ? (
          <div className="overflow-auto max-h-[50vh]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 text-zinc-400">
                <tr>
                  <th className="px-4 py-3">Ticker / Name</th>
                  <th className="px-4 py-3">Current price</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <TableRowSkeleton key={i} cols={2} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-auto max-h-[60vh] scrollable rounded-lg border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 font-medium text-zinc-400">
                <tr>
                  <th className="px-4 py-3">Ticker / Name</th>
                  <th className="px-4 py-3">Current price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {stocks.map((s) => (
                  <tr
                    key={s.ticker}
                    className="cursor-pointer transition-colors hover:bg-zinc-800/50"
                    onClick={() => navigate(`/stocks/${s.ticker}`)}
                  >
                    <td className="px-4 py-3">
                      <div>
                        <span className="font-medium text-zinc-100">{s.ticker}</span>
                        <div className="text-xs text-zinc-500">{getTickerFullName(s.ticker)}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">${Number(s.currentPrice ?? 0).toFixed(2)}</td>
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
