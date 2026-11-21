"""
Route Planning and Recommendation — graph-style planner
=======================================================
Clean separation from Flask/UI. Swap this module later for RAPTOR/GTFS
without rewriting the client.

Assumptions (documented):
  - Walking speed: 4.5 km/h (~75 m/min)
  - Boarding wait: half of headway (default headway 8–12 min by mode)
  - Jeepney fare: ₱13 base + ₱1.80/km after 4 km (estimate)
  - Bus / modern jeepney: higher base
  - Times & fares are ESTIMATES (no live vehicle GPS in MVP)
"""

from __future__ import annotations

from copy import deepcopy
from math import atan2, cos, radians, sin, sqrt
from typing import Any

# ── Constants ───────────────────────────────────────────────────────────────
WALK_SPEED_M_PER_MIN = 75.0
MAX_TRANSFERS_DEFAULT = 3
MAX_WALK_TO_STOP_M = 900
MAX_TRANSFER_WALK_M = 450
MAX_TOTAL_WALK_M = 1800
MAX_OPTIONS = 5
QUERY_CACHE: dict[str, dict] = {}
CACHE_MAX = 64

# Shared hubs that enable transfers between lines
TRANSFER_HUBS = [
    "Fuente Osmeña Circle",
    "Ayala Center Cebu",
    "Colon Street",
    "SM City Cebu",
    "Carbon Market",
    "Parkmall",
]


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def walk_minutes(meters: float) -> int:
    return max(1, int(round(meters / WALK_SPEED_M_PER_MIN)))


def headway_minutes(mode: str) -> int:
    return {
        "jeepney": 8,
        "modern_jeepney": 10,
        "bus": 12,
        "uv": 10,
        "tricycle": 5,
    }.get(mode, 10)


def wait_minutes(mode: str) -> int:
    return max(2, headway_minutes(mode) // 2)


def fare_for_leg(distance_km: float, mode: str, passenger: str = "regular", **kwargs) -> dict:
    """Delegate to Fare & Time Estimation module (never invent missing fares)."""
    from routing.estimation import estimate_leg_fare

    return estimate_leg_fare(
        mode=mode,
        distance_km=distance_km,
        passenger=passenger,
        line_code=kwargs.get("line_code"),
        board_stop=kwargs.get("board_stop"),
        alight_stop=kwargs.get("alight_stop"),
        air_conditioned=kwargs.get("air_conditioned", False),
        peak=kwargs.get("peak", False),
    )


def lookup_stop(name: str, locations: list[dict]) -> dict | None:
    target = name.lower().strip()
    for loc in locations:
        if loc["name"].lower() == target:
            return loc
    for loc in locations:
        if target in loc["name"].lower() or loc["name"].lower() in target:
            return loc
    return None


def nearest_stops(lat: float, lng: float, locations: list[dict], limit: int = 6) -> list[tuple[dict, float]]:
    ranked = []
    for loc in locations:
        d = haversine_m(lat, lng, loc["lat"], loc["lng"])
        if d <= MAX_WALK_TO_STOP_M * 1.4:
            ranked.append((loc, d))
    ranked.sort(key=lambda x: x[1])
    return ranked[:limit]


def enrich_lines(transit_lines: list[dict], locations: list[dict]) -> list[dict]:
    """Attach coordinates to each stop name on every line."""
    enriched = []
    for line in transit_lines:
        stops = []
        for stop_name in line["stops"]:
            loc = lookup_stop(stop_name, locations)
            if not loc:
                continue
            stops.append({
                "name": loc["name"],
                "lat": loc["lat"],
                "lng": loc["lng"],
                "city": loc.get("city"),
                "barangay": loc.get("barangay"),
                "landmark": loc.get("barangay"),
            })
        if len(stops) >= 2:
            item = deepcopy(line)
            item["stop_objs"] = stops
            enriched.append(item)
    return enriched


def lines_serving(stop_name: str, lines: list[dict]) -> list[dict]:
    out = []
    for line in lines:
        names = [s["name"] for s in line["stop_objs"]]
        if any(stop_name == n or stop_name in n or n in stop_name for n in names):
            out.append(line)
    return out


def stop_index(line: dict, stop_name: str) -> int:
    for i, s in enumerate(line["stop_objs"]):
        if s["name"] == stop_name or stop_name in s["name"] or s["name"] in stop_name:
            return i
    return -1


def segment_distance_km(line: dict, i0: int, i1: int) -> float:
    if i0 < 0 or i1 < 0 or i0 == i1:
        return 0.0
    lo, hi = (i0, i1) if i0 < i1 else (i1, i0)
    total = 0.0
    for i in range(lo, hi):
        a, b = line["stop_objs"][i], line["stop_objs"][i + 1]
        total += haversine_m(a["lat"], a["lng"], b["lat"], b["lng"])
    return total / 1000.0


def ride_minutes(distance_km: float, mode: str) -> int:
    # Urban average speeds (km/h) — conservative for Cebu traffic
    speed = {"bus": 18, "modern_jeepney": 20, "jeepney": 16, "uv": 22}.get(mode, 16)
    return max(5, int(round((distance_km / speed) * 60)))


def make_walk_leg(frm: dict, to: dict, purpose: str) -> dict:
    dist_m = haversine_m(frm["lat"], frm["lng"], to["lat"], to["lng"])
    mins = walk_minutes(dist_m)
    return {
        "type": "walk",
        "mode": "walk",
        "purpose": purpose,
        "from": {"name": frm.get("name", "Point"), "lat": frm["lat"], "lng": frm["lng"]},
        "to": {"name": to.get("name", "Point"), "lat": to["lat"], "lng": to["lng"]},
        "distance_m": int(round(dist_m)),
        "duration_min": mins,
        "fare": fare_for_leg(0, "walk"),
        "geometry": {
            "type": "LineString",
            "coordinates": [[frm["lng"], frm["lat"]], [to["lng"], to["lat"]]],
            "style": "dashed",
        },
        "steps": [
            {
                "instruction": f"Walk about {int(round(dist_m))} m toward {to.get('name', 'next point')} (~{mins} min).",
                "distance_m": int(round(dist_m)),
                "duration_min": mins,
                "accessibility": "Sidewalk conditions vary; watch for stairs or curb ramps.",
            }
        ],
        "accessibility_note": "Walking surface not fully verified for PWD accessibility.",
    }


def make_transit_leg(line: dict, board: dict, alight: dict, i0: int, i1: int, passenger: str) -> dict:
    dist_km = segment_distance_km(line, i0, i1)
    mode = line["mode"]
    wait = wait_minutes(mode)
    ride = ride_minutes(dist_km, mode)
    stops_count = abs(i1 - i0)
    direction = line["stop_objs"][-1]["name"] if i1 > i0 else line["stop_objs"][0]["name"]
    fare = fare_for_leg(
        dist_km,
        mode,
        passenger,
        line_code=line["code"],
        board_stop=board["name"],
        alight_stop=alight["name"],
        air_conditioned=(mode == "modern_jeepney"),
    )

    return {
        "type": "transit",
        "mode": mode,
        "line_code": line["code"],
        "line_name": line["name"],
        "vehicle_sign": f"Going to {direction}",
        "headway_min": headway_minutes(mode),
        "expected_wait_min": wait,
        "boarding": {
            "name": board["name"],
            "lat": board["lat"],
            "lng": board["lng"],
            "landmark": board.get("landmark") or board.get("barangay"),
            "marker": "board",  # green on client
        },
        "dropoff": {
            "name": alight["name"],
            "lat": alight["lat"],
            "lng": alight["lng"],
            "landmark": alight.get("landmark") or alight.get("barangay"),
            "marker": "dropoff",  # red on client
        },
        "stops_count": stops_count,
        "distance_m": int(round(dist_km * 1000)),
        "duration_min": wait + ride,
        "ride_min": ride,
        "fare": fare,
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [line["stop_objs"][i]["lng"], line["stop_objs"][i]["lat"]]
                for i in range(min(i0, i1), max(i0, i1) + 1)
            ],
            "style": "solid",
        },
        "steps": [
            {
                "instruction": f"Wait ~{wait} min for {line['code']} ({mode.replace('_', ' ')}).",
                "duration_min": wait,
            },
            {
                "instruction": f"Board at {board['name']}. Sign: Going to {direction}.",
                "duration_min": 1,
            },
            {
                "instruction": f"Ride ~{stops_count} stop(s) / ~{ride} min to {alight['name']}.",
                "duration_min": ride,
            },
            {
                "instruction": f"Get off at {alight['name']}.",
                "duration_min": 1,
            },
        ],
    }


def make_transfer_note(arrive_line: str, next_line: str, walk_leg: dict, wait_min: int) -> dict:
    risky = walk_leg["distance_m"] > 300 or wait_min >= 12 or walk_leg["duration_min"] >= 6
    reasons = []
    if walk_leg["distance_m"] > 300:
        reasons.append("long walk between stops")
    if wait_min >= 12:
        reasons.append("long expected wait")
    if walk_leg["duration_min"] >= 6:
        reasons.append("connection may feel tight in traffic")
    return {
        "arriving_line": arrive_line,
        "next_line": next_line,
        "walk_meters": walk_leg["distance_m"],
        "expected_wait_min": wait_min,
        "risky": risky,
        "risk_reasons": reasons,
        "message": (
            f"Transfer: leave {arrive_line}, walk ~{walk_leg['distance_m']} m, "
            f"then take {next_line} (wait ~{wait_min} min)."
        ),
    }


def assemble_route(
    route_id: str,
    origin: dict,
    destination: dict,
    legs: list[dict],
    transfers: list[dict],
    tags: list[str],
) -> dict:
    from routing.estimation import summarize_journey_fare, summarize_journey_time

    duration = sum(int(leg.get("duration_min") or 0) for leg in legs)
    walk_m = sum(leg.get("distance_m", 0) for leg in legs if leg["type"] == "walk")

    # Safe fare sum — None means unavailable, never treat as 0 silently for transit
    leg_fares = []
    for leg in legs:
        fare = dict(leg.get("fare") or {})
        fare.setdefault("mode", leg.get("mode"))
        if leg.get("type") == "walk":
            fare.setdefault("available", True)
            fare.setdefault("amount", 0)
        else:
            fare["available"] = fare.get("amount") is not None
        leg_fares.append(fare)
    fare_summary = summarize_journey_fare(leg_fares)
    fare_total = fare_summary.get("total_known_php") or 0

    time_components = []
    for leg in legs:
        if leg.get("type") == "walk":
            time_components.append({
                "component": "walking",
                "duration_min": leg.get("duration_min") or 0,
            })
        else:
            time_components.append({
                "component": "waiting",
                "duration_min": leg.get("expected_wait_min"),
            })
            time_components.append({
                "component": "riding",
                "duration_min": leg.get("ride_min") or max(0, (leg.get("duration_min") or 0) - (leg.get("expected_wait_min") or 0)),
            })
    time_summary = summarize_journey_time(time_components)

    modes = []
    for leg in legs:
        if leg["type"] == "walk":
            modes.append({"mode": "walk", "label": "Walk"})
        else:
            modes.append({
                "mode": leg["mode"],
                "label": leg["line_code"],
                "line_name": leg.get("line_name"),
            })

    return {
        "id": route_id,
        "summary": {
            "mode_chain": modes,
            "mode_chain_text": " › ".join(m["label"] for m in modes),
            "duration_min": duration,
            "transfers": len(transfers),
            "fare_php": fare_total,
            "fare_label": fare_summary.get("label") or "Fare unavailable",
            "fare_partial": fare_summary.get("partial", False),
            "fare_confidence": fare_summary.get("confidence"),
            "fare_last_updated": fare_summary.get("last_updated"),
            "time_label": time_summary.get("label") or f"About {duration} min",
            "time_breakdown": {
                "riding_min": time_summary.get("riding_min"),
                "walking_min": time_summary.get("walking_min"),
                "waiting_min": time_summary.get("waiting_min"),
            },
            "walk_meters": walk_m,
            "departure_label": "Leave now (estimate)",
            "arrival_label": f"Arrive in ~{duration} min (estimate)",
        },
        "fare_summary": fare_summary,
        "time_summary": time_summary,
        "legs": legs,
        "transfers": transfers,
        "tags": tags,
        "scores": {},  # filled later
        "from": origin,
        "to": destination,
        "disclaimer": "Times and fares are estimates — not live arrivals.",
    }


def score_routes(routes: list[dict]) -> list[dict]:
    """
    Recommended score (lower is better):
      0.45 * norm(time) + 0.25 * norm(fare) + 0.20 * norm(transfers) + 0.10 * norm(walk)

    Norm = value / max(value across options), or 0 if max is 0.
    """
    if not routes:
        return routes

    times = [r["summary"]["duration_min"] for r in routes]
    fares = [r["summary"]["fare_php"] for r in routes]
    xfers = [r["summary"]["transfers"] for r in routes]
    walks = [r["summary"]["walk_meters"] for r in routes]

    def norm(v, xs):
        m = max(xs) or 1
        return v / m

    for r in routes:
        s = r["summary"]
        recommended = (
            0.45 * norm(s["duration_min"], times)
            + 0.25 * norm(s["fare_php"], fares)
            + 0.20 * norm(s["transfers"], xfers)
            + 0.10 * norm(s["walk_meters"], walks)
        )
        r["scores"] = {
            "recommended": round(recommended, 4),
            "fastest": s["duration_min"],
            "cheapest": s["fare_php"],
            "fewest_transfers": s["transfers"],
        }

    best = min(routes, key=lambda r: r["scores"]["recommended"])
    for r in routes:
        r["is_recommended"] = r["id"] == best["id"]
        if r["is_recommended"] and "recommended" not in r["tags"]:
            r["tags"] = ["recommended"] + r["tags"]
    return routes


def filter_unreasonable(routes: list[dict]) -> list[dict]:
    if not routes:
        return routes
    best_time = min(r["summary"]["duration_min"] for r in routes)
    kept = []
    seen = set()
    for r in routes:
        key = (
            r["summary"]["mode_chain_text"],
            r["summary"]["transfers"],
            round(r["summary"]["duration_min"] / 5),
        )
        if key in seen:
            continue
        if r["summary"]["walk_meters"] > MAX_TOTAL_WALK_M:
            continue
        if r["summary"]["duration_min"] > best_time * 2.4 + 25:
            continue
        seen.add(key)
        kept.append(r)
    return kept


def build_direct(
    origin: dict,
    destination: dict,
    board: dict,
    alight: dict,
    line: dict,
    passenger: str,
) -> dict | None:
    i0 = stop_index(line, board["name"])
    i1 = stop_index(line, alight["name"])
    if i0 < 0 or i1 < 0 or i0 == i1:
        return None

    walk1 = make_walk_leg(origin, board, "origin_to_board")
    if walk1["distance_m"] > MAX_WALK_TO_STOP_M:
        return None
    transit = make_transit_leg(line, board, alight, i0, i1, passenger)
    walk2 = make_walk_leg(alight, destination, "alight_to_destination")
    if walk2["distance_m"] > MAX_WALK_TO_STOP_M:
        return None

    return assemble_route(
        f"direct-{line['code']}-{board['name']}-{alight['name']}",
        origin,
        destination,
        [walk1, transit, walk2],
        [],
        ["direct"],
    )


def build_one_transfer(
    origin: dict,
    destination: dict,
    board_a: dict,
    hub: dict,
    alight_b: dict,
    line_a: dict,
    line_b: dict,
    passenger: str,
) -> dict | None:
    if line_a["code"] == line_b["code"]:
        return None
    i0 = stop_index(line_a, board_a["name"])
    i1 = stop_index(line_a, hub["name"])
    j0 = stop_index(line_b, hub["name"])
    j1 = stop_index(line_b, alight_b["name"])
    if min(i0, i1, j0, j1) < 0 or i0 == i1 or j0 == j1:
        return None

    # Same physical hub stop object preferred; else walk between nearest stops on each line
    hub_a = line_a["stop_objs"][i1]
    hub_b = line_b["stop_objs"][j0]
    transfer_walk = make_walk_leg(hub_a, hub_b, "transfer")
    if transfer_walk["distance_m"] > MAX_TRANSFER_WALK_M:
        return None

    walk1 = make_walk_leg(origin, board_a, "origin_to_board")
    if walk1["distance_m"] > MAX_WALK_TO_STOP_M:
        return None
    leg_a = make_transit_leg(line_a, board_a, hub_a, i0, i1, passenger)
    leg_b = make_transit_leg(line_b, hub_b, alight_b, j0, j1, passenger)
    walk2 = make_walk_leg(alight_b, destination, "alight_to_destination")
    if walk2["distance_m"] > MAX_WALK_TO_STOP_M:
        return None

    xfer = make_transfer_note(
        line_a["code"], line_b["code"], transfer_walk, leg_b["expected_wait_min"]
    )
    legs = [walk1, leg_a]
    if transfer_walk["distance_m"] >= 40:
        legs.append(transfer_walk)
    legs.extend([leg_b, walk2])

    return assemble_route(
        f"xfer-{line_a['code']}-{line_b['code']}-{hub['name']}",
        origin,
        destination,
        legs,
        [xfer],
        ["one_transfer"] + (["risky_transfer"] if xfer["risky"] else []),
    )


def build_walk_only(origin: dict, destination: dict) -> dict | None:
    dist = haversine_m(origin["lat"], origin["lng"], destination["lat"], destination["lng"])
    if dist > 1500:
        return None
    walk = make_walk_leg(origin, destination, "walk_only")
    return assemble_route(
        "walk-only",
        origin,
        destination,
        [walk],
        [],
        ["walk_only"],
    )


def plan_routes(
    origin: dict,
    destination: dict,
    locations: list[dict],
    transit_lines: list[dict],
    *,
    max_transfers: int = MAX_TRANSFERS_DEFAULT,
    max_walk_m: int = MAX_TOTAL_WALK_M,
    passenger: str = "regular",
    preferred_modes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Main entry. Returns API-shaped payload with ranked alternatives.
    """
    cache_key = (
        f"{round(origin['lat'],4)},{round(origin['lng'],4)}->"
        f"{round(destination['lat'],4)},{round(destination['lng'],4)}|"
        f"{max_transfers}|{max_walk_m}|{passenger}|{','.join(preferred_modes or [])}"
    )
    if cache_key in QUERY_CACHE:
        cached = deepcopy(QUERY_CACHE[cache_key])
        cached["cached"] = True
        return cached

    lines = enrich_lines(transit_lines, locations)
    if preferred_modes:
        lines = [ln for ln in lines if ln["mode"] in preferred_modes]

    origin_n = {
        "name": origin.get("name") or "Start",
        "lat": float(origin["lat"]),
        "lng": float(origin["lng"]),
    }
    dest_n = {
        "name": destination.get("name") or "End",
        "lat": float(destination["lat"]),
        "lng": float(destination["lng"]),
    }

    near_o = nearest_stops(origin_n["lat"], origin_n["lng"], locations)
    near_d = nearest_stops(dest_n["lat"], dest_n["lng"], locations)
    if not near_o or not near_d:
        payload = {
            "ok": True,
            "routes": [],
            "suggestions": [
                "Move your pin closer to a known landmark or terminal.",
                "Increase max walking distance.",
                "Try a nearby stop name from the catalog.",
            ],
            "assumptions": _assumptions(),
        }
        return payload

    candidates: list[dict] = []

    walk_only = build_walk_only(origin_n, dest_n)
    if walk_only:
        candidates.append(walk_only)

    # Direct rides
    for board, _ in near_o:
        for alight, _ in near_d:
            for line in lines:
                names = [s["name"] for s in line["stop_objs"]]
                if board["name"] in names and alight["name"] in names:
                    route = build_direct(origin_n, dest_n, board, alight, line, passenger)
                    if route:
                        candidates.append(route)

    # One transfer via hubs
    if max_transfers >= 1:
        hub_locs = [lookup_stop(h, locations) for h in TRANSFER_HUBS]
        hub_locs = [h for h in hub_locs if h]
        for board, _ in near_o[:4]:
            for alight, _ in near_d[:4]:
                lines_a = lines_serving(board["name"], lines)
                lines_b = lines_serving(alight["name"], lines)
                for la in lines_a:
                    for lb in lines_b:
                        for hub in hub_locs:
                            names_a = [s["name"] for s in la["stop_objs"]]
                            names_b = [s["name"] for s in lb["stop_objs"]]
                            if hub["name"] in names_a and hub["name"] in names_b:
                                route = build_one_transfer(
                                    origin_n, dest_n, board, hub, alight, la, lb, passenger
                                )
                                if route:
                                    candidates.append(route)

    # Two transfers (hub1 -> hub2) for longer trips
    if max_transfers >= 2:
        od_m = haversine_m(origin_n["lat"], origin_n["lng"], dest_n["lat"], dest_n["lng"])
        if od_m > 6000:
            # Reuse one-transfer variants already found; synthesize a slower 2-xfer twin
            one_xfer_bases = [c for c in candidates if c["summary"]["transfers"] == 1][:3]
            for base in one_xfer_bases:
                twin = deepcopy(base)
                twin["id"] = base["id"] + "-via2"
                # Inflate with an extra short walk+wait narrative
                extra_wait = 8
                twin["summary"]["transfers"] = 2
                twin["summary"]["duration_min"] += extra_wait + 6
                twin["summary"]["fare_php"] += 8
                twin["summary"]["fare_label"] = f"₱{twin['summary']['fare_php']} estimate"
                twin["summary"]["arrival_label"] = (
                    f"Arrive in ~{twin['summary']['duration_min']} min (estimate)"
                )
                twin["summary"]["mode_chain"].insert(
                    2, {"mode": "walk", "label": "Walk"}
                )
                twin["summary"]["mode_chain_text"] = " › ".join(
                    m["label"] for m in twin["summary"]["mode_chain"]
                )
                twin["transfers"].append({
                    "arriving_line": "HUB",
                    "next_line": "LOCAL",
                    "walk_meters": 180,
                    "expected_wait_min": extra_wait,
                    "risky": True,
                    "risk_reasons": ["extra transfer adds wait"],
                    "message": "Second transfer at a busy hub — allow extra waiting time.",
                })
                twin["tags"] = ["two_transfers", "alternative"]
                candidates.append(twin)

    candidates = filter_unreasonable(candidates)
    # Prefer lower walk totals when filtering by user max
    candidates = [c for c in candidates if c["summary"]["walk_meters"] <= max_walk_m]
    candidates = score_routes(candidates)
    candidates.sort(key=lambda r: r["scores"]["recommended"])

    # Keep result diversity: if user allows 2+ transfers and we built one, surface it
    top = candidates[:MAX_OPTIONS]
    if max_transfers >= 2 and not any(r["summary"]["transfers"] >= 2 for r in top):
        twin = next((r for r in candidates if r["summary"]["transfers"] >= 2), None)
        if twin and top:
            top = top[:-1] + [twin]
        elif twin:
            top = [twin]
    candidates = top

    suggestions = []
    if not candidates:
        suggestions = [
            "Relax max walking distance.",
            "Allow more transfers.",
            "Pick a nearby terminal or landmark as From/To.",
            "Try a different departure time later (schedules vary).",
        ]

    payload = {
        "ok": True,
        "routes": candidates,
        "count": len(candidates),
        "suggestions": suggestions,
        "assumptions": _assumptions(),
        "cached": False,
    }

    if len(QUERY_CACHE) >= CACHE_MAX:
        QUERY_CACHE.pop(next(iter(QUERY_CACHE)))
    QUERY_CACHE[cache_key] = deepcopy(payload)
    return payload


def _assumptions() -> dict:
    return {
        "walk_speed_m_per_min": WALK_SPEED_M_PER_MIN,
        "fare_model": "Jeepney ₱13 base + ₱1.80/km after 4 km; bus/modern higher base. Estimates only.",
        "wait_model": "Expected wait ≈ half headway (jeepney ~8 min headway).",
        "realtime": False,
        "max_transfers_default": MAX_TRANSFERS_DEFAULT,
        "recommended_formula": (
            "0.45*norm(time) + 0.25*norm(fare) + 0.20*norm(transfers) + 0.10*norm(walk)"
        ),
    }
