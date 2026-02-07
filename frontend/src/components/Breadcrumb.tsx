import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="flex items-center gap-1 text-sm text-zinc-400">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="h-4 w-4 text-zinc-600" />}
          {item.href ? (
            <Link to={item.href} className="hover:text-zinc-200 transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className="text-zinc-200">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
