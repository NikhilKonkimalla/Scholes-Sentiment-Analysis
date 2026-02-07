export interface Sector {
  id: string;
  name: string;
  icon: string;
  stockCount: number;
}

export const MOCK_SECTORS: Sector[] = [
  { id: 'technology', name: 'Technology', icon: '💻', stockCount: 6 },
  { id: 'health', name: 'Health', icon: '🏥', stockCount: 3 },
  { id: 'finance', name: 'Finance', icon: '🏦', stockCount: 3 },
  { id: 'energy', name: 'Energy', icon: '⚡', stockCount: 2 },
  { id: 'consumer', name: 'Consumer', icon: '🛒', stockCount: 2 },
  { id: 'industrials', name: 'Industrials', icon: '🏭', stockCount: 2 },
  { id: 'utilities', name: 'Utilities', icon: '💡', stockCount: 1 },
  { id: 'materials', name: 'Materials', icon: '🧪', stockCount: 1 },
];
