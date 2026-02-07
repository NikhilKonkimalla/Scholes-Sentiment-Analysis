# Scholes Options — Frontend

Finance-style React frontend: black theme, red/green accents, persistent Home | Sectors tabs, and drill-down to Sector → Stocks → Stock detail (price chart, AI evaluation, options table).

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the dev server:

   ```bash
   npm run dev
   ```

3. Open the URL shown in the terminal (e.g. `http://localhost:5173`).

## Build

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Structure

- **`src/components/`** — Layout, Card, Badge, Breadcrumb, Skeleton
- **`src/pages/`** — Home (Active Options), Sectors, SectorDetail, StockDetail
- **`src/mock/`** — options.ts, sectors.ts, stocks.ts (mock data)
- **`src/services/api.ts`** — API functions (mock promises; swap for real `fetch` later)

## Routes

| Route | Description |
|-------|-------------|
| `/` | Home — Active Options list (search, sort) |
| `/sectors` | Sectors grid (click tile → sector detail) |
| `/sectors/:sectorId` | Stocks in sector (click row → stock detail) |
| `/stocks/:ticker` | Stock detail: chart, AI summary, options table |

## API (mock → real)

The app is wired for these endpoints. Replace mock implementations in `src/services/api.ts` with real `fetch()` when the backend is ready:

- `GET /api/sectors`
- `GET /api/sectors/:sectorId/stocks`
- `GET /api/stocks/:ticker/prices?range=1m`
- `GET /api/stocks/:ticker/ai-summary`
- `GET /api/stocks/:ticker/options`

## Tech

- **Vite** + **React** + **TypeScript**
- **Tailwind CSS** (black/zinc, emerald/rose accents)
- **React Router** v6
- **Recharts** (line chart)
- **lucide-react** (icons)
