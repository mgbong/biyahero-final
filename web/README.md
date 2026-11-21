# BIYAHERO (web) — Naga City

Next.js + TypeScript + Tailwind + Supabase/PostGIS route planner for Philippine
commuters. Initial coverage: **Naga City, Camarines Sur**.

The existing Flask/Cebu app at the repo root is unchanged. This app lives in `web/`.

## Phase status

1. **Done** — App scaffold, PostGIS schema, Naga seed, types  
2. **Done** — Leaflet + OSM map (`/map`), polylines, stop markers, verification badges  
3. Next — Route graph + multi-criteria recommendation  

## Setup

```bash
cd web
cp .env.example .env.local   # optional for Phase 2 — seed works without it
npm install
npm run dev
```

- Home: [http://127.0.0.1:3000](http://127.0.0.1:3000)  
- Map: [http://127.0.0.1:3000/map](http://127.0.0.1:3000/map)  
- Geo API: [http://127.0.0.1:3000/api/geo/network](http://127.0.0.1:3000/api/geo/network)

Without Supabase keys, `/api/geo/network` returns the local Naga seed (`source: "seed"`).

### Database (optional for map)

1. Enable PostGIS  
2. Run `supabase/migrations/001_init.sql`  
3. Run `supabase/seed/001_naga_sample.sql`  
4. Run `supabase/migrations/002_geojson_views.sql`  

## Key decisions (Phase 2)

- **Leaflet only** (no `react-leaflet`) — fewer deps; map lives in a client component.  
- **OSM tiles** — no paid key.  
- **Seed fallback** — map works before Supabase is wired.  
- **Verification badges** — `verified` / `pending_verification` / `potentially_outdated`; never shown as verified unless status is `verified`.

## Build order

1. ~~Setup, schema, seed~~  
2. ~~Map view (Leaflet + OSM)~~  
3. Route graph + multi-criteria recommendation  
4. Itinerary view  
5. Fare + discounts from DB  
6. Disruption alerts  
7. Verification admin UI  
8. Admin analytics  
9. Saved routes / landmarks  
10. PWA offline saved itineraries  

## Ask before adding

Extra npm packages beyond Next, TypeScript, Tailwind, Leaflet, and Supabase need a quick OK first.
