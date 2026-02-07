import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { OptionsPayoffChart } from './OptionsPayoffChart';
import { ChevronDown } from 'lucide-react';

export function IntroScreen() {
  const [graphVisible, setGraphVisible] = useState(false);
  const [headlineVisible, setHeadlineVisible] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setHeadlineVisible(true), 200);
    const t2 = setTimeout(() => setGraphVisible(true), 800);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  return (
    <section className="relative flex min-h-[100dvh] flex-col items-center justify-center px-6 py-16">
      {/* Headline - fades in first */}
      <div
        className={`mb-12 text-center transition-all duration-700 ${
          headlineVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <h1 className="text-4xl font-bold tracking-tight text-zinc-100 sm:text-5xl lg:text-6xl">
          Level Up Your{' '}
          <span className="text-gold">Options</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-zinc-400">
          Sentiment scoring and Black–Scholes valuation. Spot mispricings and
          trade with conviction.
        </p>
      </div>

      {/* Interactive graph - pops up with delay */}
      <div
        className={`w-full max-w-2xl transition-all duration-700 ease-out ${
          graphVisible
            ? 'translate-y-0 scale-100 opacity-100'
            : 'translate-y-8 scale-[0.97] opacity-0'
        }`}
      >
        <OptionsPayoffChart
          strike={100}
          premium={5}
          showStrikeToggle={true}
        />
      </div>

      {/* CTA - fades in after graph */}
      <div
        className={`mt-12 flex flex-col items-center gap-4 transition-all duration-500 delay-300 ${
          graphVisible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
        }`}
      >
        <Link
          to="#content"
          className="inline-flex items-center gap-2 rounded-full bg-accent-green px-6 py-3 text-base font-semibold text-white shadow-lg shadow-accent-green/20 hover:opacity-90 transition-opacity"
        >
          Explore opportunities
        </Link>
        <a
          href="#content"
          className="flex flex-col items-center gap-1 text-zinc-500 hover:text-zinc-400 transition-colors"
        >
          <span className="text-xs">Scroll to explore</span>
          <ChevronDown className="h-5 w-5 animate-bounce" />
        </a>
      </div>
    </section>
  );
}
