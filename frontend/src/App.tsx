import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { Sectors } from './pages/Sectors';
import { SectorDetail } from './pages/SectorDetail';
import { StockDetail } from './pages/StockDetail';

export default function App() {
  return (
    <BrowserRouter>
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
