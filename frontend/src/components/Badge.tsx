import { type ReactNode } from 'react';

type BadgeVariant = 'default' | 'call' | 'put' | 'green' | 'red' | 'neutral' | 'yellow';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-zinc-700 text-zinc-200 border-zinc-600',
  call: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
  put: 'bg-rose-500/20 text-rose-400 border-rose-500/40',
  green: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
  red: 'bg-rose-500/20 text-rose-400 border-rose-500/40',
  neutral: 'bg-zinc-600/50 text-zinc-300 border-zinc-500',
  yellow: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
};

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
