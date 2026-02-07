import { Outlet } from 'react-router-dom';
import { Link, useLocation } from 'react-router-dom';
import { LayoutGrid } from 'lucide-react';

export function Layout() {
  const location = useLocation();
  const path = location.pathname;
  const isHome = path === '/';
  const isSectors = path === '/sectors' || path.startsWith('/sectors/');

  return (
    <div className="min-h-screen bg-surface-dark">
      <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-surface-dark/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <Link to="/" className="text-xl font-bold text-zinc-100 hover:text-white transition-colors">
            Scholes <span className="text-gold">Options</span>
          </Link>

          <nav className="flex items-center gap-1">
            <Link
              to="/"
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isHome ? 'text-gold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Home
            </Link>
            <Link
              to="/sectors"
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isSectors ? 'text-gold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
              Sectors
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="rounded-full bg-accent-green px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
            >
              Explore
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6">
        <Outlet />
      </main>
    </div>
  );
}
