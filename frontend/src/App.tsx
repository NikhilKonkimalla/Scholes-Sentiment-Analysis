import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { Sectors } from './pages/Sectors';
import { SectorDetail } from './pages/SectorDetail';
import { StockDetail } from './pages/StockDetail';

// Deploys under a sub-path (e.g. GitHub Pages serves /<repo>/), so routes must be
// resolved against Vite's base URL rather than the domain root.
const basename = (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL ?? '/';

export default function App() {
  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="sectors" element={<Sectors />} />
          <Route path="sectors/:sectorId" element={<SectorDetail />} />
          <Route path="stocks/:ticker" element={<StockDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
