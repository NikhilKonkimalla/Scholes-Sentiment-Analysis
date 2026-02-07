import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/Card';
import { Skeleton } from '../components/Skeleton';
import { fetchSectors } from '../services/api';
import type { Sector } from '../mock/sectors';

export function Sectors() {
  const [sectors, setSectors] = useState<Sector[] | null>(null);

  useEffect(() => {
    fetchSectors().then(setSectors);
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
