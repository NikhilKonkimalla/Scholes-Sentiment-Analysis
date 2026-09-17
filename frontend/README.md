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

Implemented in `src/services/api.ts`. Each of these falls back to mock data when the
backend is unreachable:

| Endpoint | Status |
|----------|--------|
| `GET /api/stocks/:ticker/options` | **Real** — from the backend options CSV |
| `GET /api/stocks/:ticker/quote` | **Real** — live Yahoo Finance |
| `GET /api/stocks/:ticker/history?period=1mo` | **Real** — live Yahoo Finance |
| `GET /api/stocks/:ticker/ai-summary` | **Real** — recent headlines scored by FinBERT/VADER |
| `GET /api/sectors` | Mock — sectors are a static list |
| `GET /api/sectors/:sectorId/stocks` | Mock — filtered by tickers the backend has data for |

Anything served from mock data is tagged and labelled in the UI (see the amber notices
on the options table and the News Sentiment panel) so placeholder content is never
mistaken for real analysis. The Home page's "Active Options" table is still entirely
mock and is not yet wired to the backend.

## Tech

- **Vite** + **React** + **TypeScript**
- **Tailwind CSS** (black/zinc, emerald/rose accents)
- **React Router** v6
- **Recharts** (line chart)
- **lucide-react** (icons)
