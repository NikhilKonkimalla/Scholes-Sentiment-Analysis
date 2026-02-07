export interface Sector {
  id: string;
  name: string;
  icon: string;
  stockCount: number;
}

export const MOCK_SECTORS: Sector[] = [
  { id: 'technology', name: 'Technology', icon: '💻', stockCount: 12 },
  { id: 'health', name: 'Health', icon: '🏥', stockCount: 8 },
  { id: 'finance', name: 'Finance', icon: '🏦', stockCount: 10 },
  { id: 'energy', name: 'Energy', icon: '⚡', stockCount: 6 },
  { id: 'consumer', name: 'Consumer', icon: '🛒', stockCount: 9 },
  { id: 'industrials', name: 'Industrials', icon: '🏭', stockCount: 7 },
  { id: 'utilities', name: 'Utilities', icon: '💡', stockCount: 5 },
  { id: 'materials', name: 'Materials', icon: '🧪', stockCount: 4 },
];
