import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { ChevronLeft, ChevronRight, TrendingUp } from 'lucide-react';
import { fetchStock, fetchStockPrices } from '../services/api';
import { getTickerFullName } from '../mock/stocks';
import type { Stock } from '../mock/stocks';
import type { PricePoint } from '../mock/stocks';

const CAROUSEL_TICKERS = ['AAPL', 'SPY', 'NVDA', 'TSLA'];
const AUTO_ADVANCE_MS = 4500;
const SWIPE_THRESHOLD = 50;

type SlideData = {
  ticker: string;
  stock: Stock | null;
  prices: PricePoint[];
};

export function HeroChartCarousel() {
  const [slides, setSlides] = useState<SlideData[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [touchStartX, setTouchStartX] = useState<number | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const results: SlideData[] = await Promise.all(
        CAROUSEL_TICKERS.map(async (ticker) => {
          const [stock, prices] = await Promise.all([
            fetchStock(ticker),
            fetchStockPrices(ticker, '1mo'),
          ]);
          return {
            ticker,
            stock: stock ?? null,
            prices: prices ?? [],
          };
        })
      );
      if (!cancelled) setSlides(results);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const goTo = useCallback((index: number) => {
    const next = (index + CAROUSEL_TICKERS.length) % CAROUSEL_TICKERS.length;
    setIsTransitioning(true);
    setCurrentIndex(next);
    const t = setTimeout(() => setIsTransitioning(false), 350);
    return () => clearTimeout(t);
  }, []);

  const goNext = useCallback(() => goTo(currentIndex + 1), [currentIndex, goTo]);
  const goPrev = useCallback(() => goTo(currentIndex - 1), [currentIndex, goTo]);

  const goNextRef = useRef(goNext);
  goNextRef.current = goNext;
  useEffect(() => {
    if (slides.length === 0) return;
    intervalRef.current = setInterval(() => goNextRef.current(), AUTO_ADVANCE_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [slides.length]);

  const handleTouchStart = (e: React.TouchEvent) => setTouchStartX(e.touches[0].clientX);
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX == null) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (dx > SWIPE_THRESHOLD) goPrev();
    else if (dx < -SWIPE_THRESHOLD) goNext();
    setTouchStartX(null);
  };

  if (slides.length === 0) {
    return (
      <div className="flex h-[280px] w-full max-w-4xl items-center justify-center rounded-lg border border-zinc-700 bg-zinc-900">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
      </div>
    );
  }

  const slide = slides[currentIndex];

  return (
    <div
      className="relative w-full max-w-4xl overflow-hidden rounded-lg border border-zinc-700 bg-zinc-900 shadow-lg"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,260px)_1fr] min-h-[280px]">
        {/* Left: Ticker + details */}
        <div className="flex flex-col justify-center gap-4 px-6 py-6 lg:py-8 lg:pr-4 border-b border-zinc-700 lg:border-b-0 lg:border-r border-zinc-700">
          <div
            key={slide.ticker}
            className={`transition-all duration-300 ${isTransitioning ? 'opacity-0 scale-[0.98]' : 'opacity-100 scale-100'}`}
          >
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-zinc-100 antialiased tracking-tight">{slide.ticker}</span>
              {slide.stock && (
                <span
                  className={`text-sm font-medium ${(slide.stock.dayChangePercent ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                >
                  {(slide.stock.dayChangePercent ?? 0) >= 0 ? '+' : ''}
                  {(slide.stock.dayChangePercent ?? 0).toFixed(2)}%
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-zinc-400 font-medium">
              {slide.stock?.name && slide.stock.name !== slide.ticker ? slide.stock.name : getTickerFullName(slide.ticker)}
            </p>
            {slide.stock && (
              <p className="mt-2 text-lg font-semibold text-zinc-200 tracking-tight">
                ${Number(slide.stock.currentPrice ?? 0).toFixed(2)}
              </p>
            )}
            <Link
              to={`/stocks/${slide.ticker}`}
              className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              <TrendingUp className="h-4 w-4" />
              View details
            </Link>
          </div>
        </div>

        {/* Right: Chart */}
        <div className="relative h-56 lg:h-64 px-4 pb-4 pt-2">
          {CAROUSEL_TICKERS.map((_, i) => (
            <div
              key={i}
              className={`absolute inset-0 px-4 pb-4 pt-2 transition-all duration-300 ease-out ${
                i === currentIndex
                  ? 'opacity-100 pointer-events-auto translate-x-0'
                  : 'opacity-0 pointer-events-none translate-x-4'
              }`}
            >
              {slides[i]?.prices.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={slides[i].prices}
                    margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#71717a', fontSize: 10 }}
                      tickFormatter={(v) => (v && typeof v === 'string' ? v.slice(5) : '')}
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      tick={{ fill: '#71717a', fontSize: 10 }}
                      tickFormatter={(v) => `$${v}`}
                      width={42}
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
                <div className="flex h-full items-center justify-center text-zinc-500 text-sm">
                  No price data
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2 lg:gap-3">
        <button
          type="button"
          onClick={goPrev}
          className="rounded-md p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          aria-label="Previous"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div className="flex gap-1.5">
          {CAROUSEL_TICKERS.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => goTo(i)}
              className={`h-1.5 rounded-sm transition-all ${
                i === currentIndex ? 'w-5 bg-emerald-500' : 'w-1.5 bg-zinc-600 hover:bg-zinc-500'
              }`}
              aria-label={`Go to ${CAROUSEL_TICKERS[i]}`}
            />
          ))}
        </div>
        <button
          type="button"
          onClick={goNext}
          className="rounded-md p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          aria-label="Next"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
