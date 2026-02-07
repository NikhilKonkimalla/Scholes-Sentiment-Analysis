import { useState, useEffect } from 'react';
import { HeroChartCarousel } from './HeroChartCarousel';
import { ChevronDown } from 'lucide-react';

export function IntroScreen() {
  const [headlineVisible, setHeadlineVisible] = useState(false);
  const [carouselVisible, setCarouselVisible] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setHeadlineVisible(true), 200);
    const t2 = setTimeout(() => setCarouselVisible(true), 600);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  return (
    <section className="relative flex min-h-[100dvh] flex-col items-center justify-center px-4 py-12 sm:px-6 sm:py-16">
      {/* Headline - fades in first */}
      <div
        className={`mb-8 sm:mb-10 text-center transition-all duration-700 ${
          headlineVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <h1 className="text-4xl font-bold tracking-tight text-zinc-100 sm:text-5xl lg:text-6xl antialiased">
          Level Up Your{' '}
          <span className="text-gold">Options</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base sm:text-lg text-zinc-400 font-medium">
          Sentiment scoring and Black–Scholes valuation. Spot mispricings and
          trade with conviction.
        </p>
      </div>

      {/* Chart carousel: left = ticker/details, right = graph; auto-advance + swipe */}
      <div
        className={`w-full transition-all duration-700 ease-out ${
          carouselVisible
            ? 'translate-y-0 scale-100 opacity-100'
            : 'translate-y-8 scale-[0.98] opacity-0'
        }`}
      >
        <HeroChartCarousel />
      </div>

      {/* CTA - fades in after carousel */}
      <div
        className={`mt-10 sm:mt-12 flex flex-col items-center gap-4 transition-all duration-500 delay-200 ${
          carouselVisible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
        }`}
      >
        <button
          type="button"
          onClick={() => document.getElementById('content')?.scrollIntoView({ behavior: 'smooth' })}
          className="inline-flex items-center gap-2 rounded-lg bg-accent-green px-6 py-3 text-base font-semibold text-white shadow-md hover:opacity-90 transition-opacity"
        >
          Explore
        </button>
        <button
          type="button"
          onClick={() => document.getElementById('content')?.scrollIntoView({ behavior: 'smooth' })}
          className="flex flex-col items-center gap-1 text-zinc-500 hover:text-zinc-400 transition-colors"
        >
          <span className="text-xs">Scroll to explore</span>
          <ChevronDown className="h-5 w-5 animate-bounce" />
        </button>
      </div>
    </section>
  );
}
