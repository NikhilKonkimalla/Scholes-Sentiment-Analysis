import { useMemo, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';

type OptionType = 'call' | 'put';

interface PayoffPoint {
  underlying: number;
  pnl: number;
  strike: number;
}

function computePayoff(
  type: OptionType,
  strike: number,
  premium: number,
  minS: number,
  maxS: number,
  step: number
): PayoffPoint[] {
  const points: PayoffPoint[] = [];
  for (let s = minS; s <= maxS; s += step) {
    let pnl: number;
    if (type === 'call') {
      pnl = Math.max(s - strike, 0) - premium;
    } else {
      pnl = Math.max(strike - s, 0) - premium;
    }
    points.push({ underlying: s, pnl, strike });
  }
  return points;
}

interface OptionsPayoffChartProps {
  className?: string;
  strike?: number;
  premium?: number;
  showStrikeToggle?: boolean;
}

export function OptionsPayoffChart({
  className = '',
  strike = 100,
  premium = 5,
  showStrikeToggle = true,
}: OptionsPayoffChartProps) {
  const [type, setType] = useState<OptionType>('call');
  const [selectedStrike, setSelectedStrike] = useState(strike);

  const data = useMemo(() => {
    const p = type === 'call' ? premium : premium * 0.8;
    return computePayoff(type, selectedStrike, p, 70, 130, 1);
  }, [type, selectedStrike, premium]);

  const gradientId = `payoff-gradient-${type}-${selectedStrike}`;
  const strokeColor = type === 'call' ? '#10b981' : '#f43f5e';

  return (
    <div className={`space-y-4 ${className}`}>
      {showStrikeToggle && (
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex rounded-lg border border-zinc-700 bg-zinc-800/50 p-0.5">
            <button
              onClick={() => setType('call')}
              className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                type === 'call'
                  ? 'bg-accent-green text-white'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Call
            </button>
            <button
              onClick={() => setType('put')}
              className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                type === 'put'
                  ? 'bg-accent-red text-white'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Put
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-500">Strike:</span>
            <select
              value={selectedStrike}
              onChange={(e) => setSelectedStrike(Number(e.target.value))}
              className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-200 focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold"
            >
              {[90, 95, 100, 105, 110].map((k) => (
                <option key={k} value={k}>
                  ${k}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="h-[280px] w-full rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={strokeColor} stopOpacity={0.3} />
                <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#27272a"
              vertical={false}
            />
            <XAxis
              dataKey="underlying"
              tick={{ fill: '#71717a', fontSize: 12 }}
              axisLine={{ stroke: '#3f3f46' }}
              tickLine={false}
              tickFormatter={(v) => `$${v}`}
              domain={['dataMin', 'dataMax']}
            />
            <YAxis
              tick={{ fill: '#71717a', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `$${v}`}
              domain={['auto', 'auto']}
              width={45}
            />
            <ReferenceLine
              x={selectedStrike}
              stroke="#CCA754"
              strokeDasharray="4 4"
              strokeWidth={1.5}
            />
            <ReferenceLine y={0} stroke="#52525b" strokeWidth={1} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#18181b',
                border: '1px solid #3f3f46',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#a1a1aa' }}
              formatter={(value: number) => [`$${value.toFixed(2)} P/L`, '']}
              labelFormatter={(label) => `Underlying: $${label}`}
              cursor={{ stroke: '#71717a', strokeWidth: 1 }}
            />
            <Area
              type="monotone"
              dataKey="pnl"
              stroke={strokeColor}
              strokeWidth={2.5}
              fill={`url(#${gradientId})`}
              isAnimationActive={true}
              animationDuration={600}
              animationEasing="ease-out"
            />
          </AreaChart>
        </ResponsiveContainer>
        <div className="mt-2 flex justify-center gap-6 text-xs text-zinc-500">
          <span>Underlying price →</span>
          <span className="text-gold">Strike: ${selectedStrike}</span>
        </div>
      </div>
    </div>
  );
}
