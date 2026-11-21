# Location and Route Search — Biyahero

## Confirmed assumptions

| Item | Choice |
|------|--------|
| Platform | **Web** (responsive HTML/CSS/JS) |
| Backend | **Flask** (`app.py`) |
| Map | **OpenStreetMap + Leaflet** (bundled under `api/leaflet/`) |
| Transit data | **Custom backend** (`/api/routes/search` + local place catalog) |
| Road polyline | **OSRM** public demo (optional; falls back to straight line) |
| Reverse geocode | Flask proxy to **Nominatim** (no API key in front-end) |
| Auth | **Guest-first** on Plan Trip (`user-soft.js` — no forced login) |

No Google Maps / Directions API keys are required for the MVP.

---

## Folder structure

```
biyahero-final/
├── app.py                      # /api/locations, /api/geocode/reverse, /api/routes/search
├── html/plan-trip.html         # UI: From/To, swap, GPS, map pick, results
├── js/
│   ├── location-search.js      # Autocomplete + recent places + reverse helper
│   ├── plan-trip-map.js        # Map, validation, route search orchestration
│   └── user-soft.js            # Guest-safe session chip
├── css/route-search.css        # Module styles (flex wrap; no @media/@keyframes)
└── docs/LOCATION_ROUTE_SEARCH.md
```

---

## Features delivered

1. **From / To** fields with swap and validation  
2. **Autocomplete** (350 ms debounce), empty/typo/network messages, recent places in `localStorage`  
3. **Use my location** (browser Geolocation + reverse geocode; friendly deny / GPS-off messages)  
4. **Choose on map** (tap pin → confirm → address)  
5. **Transit options** list with mode, transfers, time, fare guess, walk distance, steps; sort by fastest / fewest transfers / cheapest; tap to draw on map; empty state  

---

## Permissions / browser config

| Need | Where |
|------|--------|
| Location | Browser prompts on **Use my location** (HTTPS or `localhost`) |
| Network | OSM tiles, OSRM (optional), Nominatim via Flask |

There is no AndroidManifest / Info.plist for this web MVP.

---

## Setup

1. `pip install -r requirements.txt`
2. `python database/init_db.py` (first time)
3. `python app.py`
4. Open **http://127.0.0.1:5000/html/plan-trip.html**  
   Do **not** use Live Server / `file://`.

### Optional env (future paid APIs)

If you later add Google / Mapbox, put keys in environment variables only — never in JS source:

```
MAP_API_KEY=...
```

Current MVP needs **no** map API key.

### Privacy

- GPS is requested only when the user taps **Use my location**.  
- Recent places stay in the browser (`localStorage`), not on the server.  
- Times and fares are labeled as **estimates**.

---

## API sketch

### `GET /api/locations?q=&limit=10`
Place autocomplete from the Cebu catalog.

### `GET /api/geocode/reverse?lat=&lng=`
Returns a readable place (catalog match or Nominatim / fallback).

### `POST /api/routes/search`
Body: `{ "from": {name,lat,lng,...}, "to": {...} }`  
Returns `{ ok, disclaimer, options: [...] }`.

---

## Test checklist

- [ ] Type “Colon” → suggestions appear after ~350 ms  
- [ ] Empty / typo query → clear “no places” message  
- [ ] Offline search → network error message (no crash)  
- [ ] Swap From/To keeps selections  
- [ ] Find Routes blocked until both fields set  
- [ ] Same start/end → validation error  
- [ ] Use my location → allow → field fills; deny → friendly message  
- [ ] GPS off → friendly message + map/manual still work  
- [ ] Choose on map → pin → Confirm → field fills  
- [ ] Find Routes → 2–3 options; sort changes order  
- [ ] Tap option → orange path on map  
- [ ] Guest (logged out) can use Plan Trip without redirect to login  
- [ ] `?from=Colon&to=SM` query params prefill when possible  
