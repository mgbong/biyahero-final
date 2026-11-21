# Route Planning and Recommendation — Biyahero

## Assumptions

| Item | Choice |
|------|--------|
| Client | **Web** (Plan Trip page) |
| Backend | **Python / Flask** |
| Map | **OpenStreetMap + Leaflet** |
| Transit data | **Custom stop/line catalog** (not live GTFS) |
| Algorithm | **Stop-and-line graph search** (direct + hub transfers); swappable for RAPTOR/A* later |

Guest-friendly: no login to plan. Saving a route redirects to login and keeps From/To in the URL/session.

---

## Data model

```
Route
  id, tags[], is_recommended, scores{}, disclaimer
  summary: mode_chain[], duration_min, transfers, fare_php, walk_meters, departure/arrival labels
  legs[]:
    walk   → from, to, distance_m, duration_min, steps[], geometry(dashed)
    transit→ line_code, boarding{}, dropoff{}, wait, ride, fare{}, geometry(solid), steps[]
  transfers[] → arriving_line, next_line, walk_meters, expected_wait_min, risky, risk_reasons
```

### Fare (estimate)

- Jeepney: ₱13 base + ₱1.80/km after 4 km  
- Modern jeepney / bus: higher base  
- Walk: ₱0  
- Student/senior/PWD: optional 20% flag with “verify with driver” note — not legal advice  
- Always labeled **estimate**

### Time (estimate)

- Walk: 75 m/min  
- Wait: half headway (jeepney ~8 min → ~4 min wait)  
- Ride: urban speed table (~16–22 km/h)  
- No realtime vehicle GPS in MVP

---

## Algorithm (flow)

```
1. Resolve origin/destination
2. Find nearby stops within walk budget
3. Direct: lines that contain both a near-origin stop and near-dest stop
4. One transfer: line A origin→hub + line B hub→dest (hubs: Fuente, Ayala, Colon, SM, …)
5. Two transfers: longer OD only (inflated alternative)
6. Walk-only if OD ≤ 1.5 km
7. Filter duplicates / excessive walk / time ≫ best
8. Score + mark Recommended
9. Return top 5
```

### Recommended score (lower is better)

```
0.45 * norm(time) + 0.25 * norm(fare) + 0.20 * norm(transfers) + 0.10 * norm(walk)
```

`norm(x) = x / max(x across options)`

### Sort tie-breakers (client)

- Cheapest → then time  
- Fewest transfers → then time  
- Fastest → then fare  
- Recommended → server score, then time  

Re-sort is **client-side** (no re-call).

---

## API

### `POST /api/routes/search`

**Request**

```json
{
  "from": { "name": "Colon Street", "lat": 10.2978, "lng": 123.8988 },
  "to": { "name": "SM City Cebu", "lat": 10.3116, "lng": 123.9184 },
  "max_transfers": 3,
  "max_walk_m": 1800,
  "passenger": "regular"
}
```

**Response (shape)**

```json
{
  "ok": true,
  "disclaimer": "Times and fares are estimates — not live arrivals.",
  "count": 3,
  "routes": [
    {
      "id": "direct-01K-Colon Street-SM City Cebu",
      "is_recommended": true,
      "summary": {
        "mode_chain_text": "Walk › 01K › Walk",
        "duration_min": 28,
        "transfers": 0,
        "fare_php": 15,
        "walk_meters": 240
      },
      "legs": [ { "type": "walk", "...": "..." }, { "type": "transit", "boarding": {}, "dropoff": {} } ],
      "transfers": [],
      "scores": { "recommended": 0.41 }
    }
  ],
  "suggestions": [],
  "assumptions": { "recommended_formula": "..." }
}
```

Multi-transfer example: look for `summary.transfers >= 1` and `transfers[].message` in the payload.

---

## Code map

| Layer | Path |
|-------|------|
| Planner | `routing/planner.py` |
| HTTP | `app.py` → `/api/routes/search` |
| UI + map | `js/plan-trip-map.js`, `html/plan-trip.html` |
| Styles | `css/route-search.css` |

---

## Map legend

- **Dashed gray** — walking  
- **Solid orange** — transit  
- **Green marker** — boarding  
- **Red marker** — drop-off  

---

## Test cases

| Case | Expect |
|------|--------|
| Direct (Colon → SM City) | ≥1 direct jeepney option, Recommended set |
| One transfer | Option with `transfers: 1` and transfer note |
| Multiple transfers | Prefer longer OD + max_transfers ≥ 2 |
| Walk-only | Short OD ≤ 1.5 km may return walk-only |
| No route | Empty `routes` + suggestions |
| Sort cheapest/fastest/fewest | Order changes without new API call |
| Missing fare | `fare_label` / estimate flags — never silent null in UI |
| Long walk edge | Routes with walk > max_walk_m filtered out |
| Guest | Plan Trip works logged out; Save → login with state kept |
| Offline | Falls back to last cached plan in `localStorage` when possible |

---

## Setup

Same as app: `python app.py` → http://127.0.0.1:5000/html/plan-trip.html  
No Google/Mapbox key required for MVP.
