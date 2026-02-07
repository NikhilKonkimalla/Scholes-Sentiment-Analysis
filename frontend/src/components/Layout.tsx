import { Outlet } from 'react-router-dom';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, LayoutGrid } from 'lucide-react';

export function Layout() {
  const location = useLocation();
  const path = location.pathname;
  const isHome = path === '/';
  const isSectors = path === '/sectors' || path.startsWith('/sectors/');

  return (
    <div className="min-h-screen bg-black">
      <header className="sticky top-0 z-50 border-b border-zinc-800 bg-black/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="text-xl font-bold text-zinc-100 hover:text-white transition-colors">
            Scholes Options
          </Link>

          <nav className="flex items-center gap-1">
            <Link
              to="/"
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isHome ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              Home
            </Link>
            <Link
              to="/sectors"
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isSectors ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
              Sectors
            </Link>
          </nav>

          <div className="flex items-center gap-2">
            <span className="rounded border border-zinc-700 bg-zinc-800/50 px-2 py-1 text-xs text-zinc-400">
              Mock Data
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1200px] px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
