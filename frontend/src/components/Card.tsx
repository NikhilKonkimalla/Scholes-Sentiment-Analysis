import { type ReactNode } from 'react';

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Card({ title, children, className = '' }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-zinc-800 bg-zinc-900/80 shadow-lg ${className}`}
    >
      {title && (
        <div className="border-b border-zinc-800 px-4 py-3">
          <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
        </div>
      )}
      <div className={title ? 'p-4' : 'p-4'}>{children}</div>
    </div>
  );
}
